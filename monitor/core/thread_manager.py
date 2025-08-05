"""
Thread Manager

Manages worker threads for the monitoring application, including:
- LogProcessor thread for reading and processing log entries
- DecisionEngine thread for making automated decisions
- Proper thread lifecycle management with graceful shutdown
"""

import sys
import signal
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtCore import QThread, QObject, QTimer, Signal, Slot, QMetaObject, Qt
from PySide6.QtWidgets import QApplication
from monitor.core.log_processor import LogProcessor
from monitor.core.decision_engine import DecisionEngine
from monitor.services.alert_db import AlertDatabase
from monitor.services.contact_db import ContactDatabase
from monitor.services.email_service import EmailService
from monitor.log_setup import get_logger


class ThreadManager(QObject):
    """
    Manages worker threads for the monitoring application.
    
    Handles:
    - Creating and starting LogProcessor and DecisionEngine threads
    - Proper signal connections between components
    - Graceful shutdown of all threads
    - Error handling and recovery
    """
    
    # Signals
    all_threads_started = Signal()
    all_threads_stopped = Signal()
    thread_error = Signal(str)  # Emits error message
    
    def __init__(self, logs_directory: Path, data_directory: Path, alert_db: AlertDatabase, contact_db: ContactDatabase):
        """
        Initialize the thread manager.
        
        Args:
            logs_directory: Directory containing the logs database files
            data_directory: Directory containing the data databases (devices, alerts, etc.)
            alert_db: Alert database instance for signal connections
            contact_db: Contact database instance for email notifications
        """
        super().__init__()
        self.logger = get_logger("monitor.core.thread_manager")
        self.logs_directory = logs_directory
        self.data_directory = data_directory
        self.alert_db = alert_db
        self.contact_db = contact_db
        
        # Create email service
        self.email_service = EmailService(self.contact_db)
        
        # Thread objects
        self.log_processor_thread: Optional[QThread] = None
        self.decision_engine_thread: Optional[QThread] = None
        
        # Worker objects
        self.log_processor: Optional[LogProcessor] = None
        self.decision_engine: Optional[DecisionEngine] = None
        
        # State tracking
        self.is_running = False
        self.shutdown_requested = False
        self.threads_finished_count = 0
        
        # Shutdown timeout timer
        self.shutdown_timer: Optional[QTimer] = None
        self.shutdown_timeout_seconds = 10
        
        self.logger.info("ThreadManager initialized")
    
    def start_threads(self) -> bool:
        """
        Start all worker threads.
        
        Returns:
            bool: True if all threads started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Threads are already running")
            return True
        
        try:
            self.logger.info("Starting worker threads...")
            
            # Create and start LogProcessor thread
            if not self._start_log_processor_thread():
                return False
            
            # Create and start DecisionEngine thread
            if not self._start_decision_engine_thread():
                self._cleanup_log_processor_thread()
                return False
            
            # Connect signals between components
            self._connect_component_signals()
            
            self.is_running = True
            self.logger.info("All worker threads started successfully")
            self.all_threads_started.emit()
            return True
            
        except Exception as e:
            self.logger.error("Failed to start worker threads", exc_info=True)
            self.thread_error.emit(f"Failed to start threads: {str(e)}")
            self.stop_threads()
            return False
    
    def stop_threads(self, timeout_seconds: Optional[float] = None) -> bool:
        """
        Stop all worker threads gracefully.
        
        Args:
            timeout_seconds: Maximum time to wait for threads to stop
            
        Returns:
            bool: True if all threads stopped gracefully, False if timeout occurred
        """
        if not self.is_running:
            self.logger.debug("Threads are not running, nothing to stop")
            return True
        
        if self.shutdown_requested:
            self.logger.warning("Shutdown already in progress")
            return False
        
        self.shutdown_requested = True
        self.threads_finished_count = 0
        
        if timeout_seconds is None:
            timeout_seconds = self.shutdown_timeout_seconds
        
        self.logger.info(f"Stopping worker threads (timeout: {timeout_seconds}s)...")
        
        try:
            # Start shutdown timeout timer
            self._start_shutdown_timer(timeout_seconds)
            
            # Stop workers using queued connections to ensure they run on correct threads
            if self.log_processor and self.log_processor_thread:
                QMetaObject.invokeMethod(self.log_processor, "stop", 
                                       Qt.ConnectionType.QueuedConnection)
            
            if self.decision_engine and self.decision_engine_thread:
                QMetaObject.invokeMethod(self.decision_engine, "stop", 
                                       Qt.ConnectionType.QueuedConnection)
            
            # If no threads were running, complete immediately
            if not self.log_processor_thread and not self.decision_engine_thread:
                self._on_all_threads_finished()
                return True
            
            return True  # Will complete asynchronously
            
        except Exception as e:
            self.logger.error("Error during thread shutdown", exc_info=True)
            self.thread_error.emit(f"Error during shutdown: {str(e)}")
            self._force_cleanup()
            return False
    
    def _start_log_processor_thread(self) -> bool:
        """Start the LogProcessor thread."""
        try:
            self.logger.debug("Creating LogProcessor thread...")
            
            # Create thread and worker
            self.log_processor_thread = QThread()
            self.log_processor = LogProcessor(
                logs_directory=self.logs_directory,
                data_directory=self.data_directory,
                batch_interval=2.0
            )
            
            # Move worker to thread
            self.log_processor.moveToThread(self.log_processor_thread)
            
            # Connect thread lifecycle signals
            self.log_processor_thread.started.connect(self.log_processor.start)
            self.log_processor.finished.connect(self.log_processor_thread.quit)
            self.log_processor.finished.connect(self._on_log_processor_finished)
            # Note: Don't use deleteLater() here to avoid shutdown issues
            
            # Connect error handling
            self.log_processor.error_occurred.connect(
                lambda msg: self.thread_error.emit(f"LogProcessor error: {msg}")
            )
            
            # Start thread
            self.log_processor_thread.start()
            self.logger.info("LogProcessor thread started")
            return True
            
        except Exception as e:
            self.logger.error("Failed to start LogProcessor thread", exc_info=True)
            self._cleanup_log_processor_thread()
            return False
    
    def _start_decision_engine_thread(self) -> bool:
        """Start the DecisionEngine thread."""
        try:
            self.logger.debug("Creating DecisionEngine thread...")
            
            # Create thread and worker
            self.decision_engine_thread = QThread()
            self.decision_engine = DecisionEngine(
                data_directory=self.data_directory,
                evaluation_interval=3.0
            )
            
            # Move worker to thread
            self.decision_engine.moveToThread(self.decision_engine_thread)
            
            # Connect thread lifecycle signals
            self.decision_engine_thread.started.connect(self.decision_engine.start)
            self.decision_engine.finished.connect(self.decision_engine_thread.quit)
            self.decision_engine.finished.connect(self._on_decision_engine_finished)
            # Note: Don't use deleteLater() here to avoid shutdown issues
            
            # Start thread
            self.decision_engine_thread.start()
            self.logger.info("DecisionEngine thread started")
            return True
            
        except Exception as e:
            self.logger.error("Failed to start DecisionEngine thread", exc_info=True)
            self._cleanup_decision_engine_thread()
            return False
    
    def _connect_component_signals(self) -> None:
        """Connect signals between components."""
        try:
            # Connect DecisionEngine alert signals to AlertDatabase
            if self.decision_engine and self.alert_db:
                self.decision_engine.alert_creation_requested.connect(
                    self.alert_db.add_alert
                )
                self.decision_engine.alert_resolution_requested.connect(
                    self.alert_db.resolve_alerts_for_device
                )
                self.logger.debug("Connected DecisionEngine -> AlertDatabase signals")
            
            # Connect DecisionEngine email notification signals to EmailService
            if self.decision_engine and self.email_service:
                self.decision_engine.device_failure_notification_requested.connect(
                    self.email_service.send_device_failure_notification
                )
                self.decision_engine.device_recovery_notification_requested.connect(
                    self.email_service.send_device_recovery_notification
                )
                self.logger.debug("Connected DecisionEngine -> EmailService signals")
            
            self.logger.info("Component signals connected successfully")
            
        except Exception as e:
            self.logger.error("Failed to connect component signals", exc_info=True)
            raise
    
    def _start_shutdown_timer(self, timeout_seconds: float) -> None:
        """Start the shutdown timeout timer."""
        self.shutdown_timer = QTimer()
        self.shutdown_timer.setSingleShot(True)
        self.shutdown_timer.timeout.connect(self._on_shutdown_timeout)
        self.shutdown_timer.start(int(timeout_seconds * 1000))
    
    @Slot()
    def _on_log_processor_finished(self) -> None:
        """Handle LogProcessor finished signal."""
        self.logger.debug("LogProcessor finished")
        self.threads_finished_count += 1
        self._check_all_threads_finished()
    
    @Slot()
    def _on_decision_engine_finished(self) -> None:
        """Handle DecisionEngine finished signal."""
        self.logger.debug("DecisionEngine finished")
        self.threads_finished_count += 1
        self._check_all_threads_finished()
    
    def _check_all_threads_finished(self) -> None:
        """Check if all threads have finished and complete shutdown if so."""
        expected_threads = 0
        if self.log_processor_thread:
            expected_threads += 1
        if self.decision_engine_thread:
            expected_threads += 1
        
        if self.threads_finished_count >= expected_threads:
            self._on_all_threads_finished()
    
    @Slot()
    def _on_shutdown_timeout(self) -> None:
        """Handle shutdown timeout."""
        self.logger.warning(f"Thread shutdown timeout after {self.shutdown_timeout_seconds}s, forcing cleanup")
        self._force_cleanup()
    
    def _on_all_threads_finished(self) -> None:
        """Handle completion of thread shutdown."""
        if self.shutdown_timer:
            self.shutdown_timer.stop()
            self.shutdown_timer = None
        
        # Wait for QThread.finished signals and cleanup
        if self.log_processor_thread:
            self.log_processor_thread.wait(2000)  # Wait up to 2 seconds
        if self.decision_engine_thread:
            self.decision_engine_thread.wait(2000)  # Wait up to 2 seconds
        
        self._cleanup_all()
        self.logger.info("All worker threads stopped successfully")
        self.all_threads_stopped.emit()
    
    def _force_cleanup(self) -> None:
        """Force cleanup of threads that didn't stop gracefully."""
        self.logger.warning("Forcing thread cleanup...")
        
        if self.shutdown_timer:
            self.shutdown_timer.stop()
            self.shutdown_timer = None
        
        # Terminate threads if they're still running
        if self.log_processor_thread and self.log_processor_thread.isRunning():
            self.log_processor_thread.terminate()
            self.log_processor_thread.wait(1000)
        
        if self.decision_engine_thread and self.decision_engine_thread.isRunning():
            self.decision_engine_thread.terminate()
            self.decision_engine_thread.wait(1000)
        
        self._cleanup_all()
        self.logger.warning("Forced thread cleanup completed")
        self.all_threads_stopped.emit()
    
    def _cleanup_all(self) -> None:
        """Cleanup all thread resources."""
        self._cleanup_log_processor_thread()
        self._cleanup_decision_engine_thread()
        self.is_running = False
        self.shutdown_requested = False
        self.threads_finished_count = 0
    
    def _cleanup_log_processor_thread(self) -> None:
        """Cleanup LogProcessor thread resources."""
        if self.log_processor_thread:
            if self.log_processor_thread.isRunning():
                self.log_processor_thread.quit()
                if not self.log_processor_thread.wait(3000):  # Wait up to 3 seconds
                    self.logger.warning("LogProcessor thread did not quit gracefully, terminating")
                    self.log_processor_thread.terminate()
                    self.log_processor_thread.wait(1000)
            self.log_processor_thread = None
        self.log_processor = None
    
    def _cleanup_decision_engine_thread(self) -> None:
        """Cleanup DecisionEngine thread resources."""
        if self.decision_engine_thread:
            if self.decision_engine_thread.isRunning():
                self.decision_engine_thread.quit()
                if not self.decision_engine_thread.wait(3000):  # Wait up to 3 seconds
                    self.logger.warning("DecisionEngine thread did not quit gracefully, terminating")
                    self.decision_engine_thread.terminate()
                    self.decision_engine_thread.wait(1000)
            self.decision_engine_thread = None
        self.decision_engine = None


def setup_signal_handlers(thread_manager: ThreadManager) -> None:
    """
    Setup system signal handlers for graceful shutdown.
    
    Args:
        thread_manager: ThreadManager instance to shutdown on signals
    """
    logger = get_logger("monitor.core.thread_manager")
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        thread_manager.stop_threads()
        
        # Give threads time to shutdown gracefully
        QTimer.singleShot(thread_manager.shutdown_timeout_seconds * 1000 + 1000, 
                         lambda: QApplication.instance().quit())
    
    # Setup signal handlers for graceful shutdown
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    logger.debug("Signal handlers setup for graceful shutdown")
