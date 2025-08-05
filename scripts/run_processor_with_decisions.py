#!/usr/bin/env python3
"""
Test Decision Engine with LogProcessor

Demo script showing how to run LogProcessor and DecisionEngine together
with proper threading and signal connections.
"""

import sys
import argparse
import signal
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QCoreApplication, QTimer
from monitor.core.log_processor import LogProcessor
from monitor.core.decision_engine import create_decision_engine_thread

class LogProcessorWithDecisionEngine:
    """Application wrapper that manages LogProcessor and DecisionEngine together"""
    
    def __init__(self, db_directory: Path, batch_interval: float):
        self.db_directory = db_directory
        self.batch_interval = batch_interval
        self.processor = None
        self.decision_engine = None
        self.decision_thread = None
        self.app = None
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal, shutting down...")
            self.stop()
            if self.app:
                QTimer.singleShot(100, self.app.quit)
        
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def setup_logging(self):
        """Setup debug logging"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Set specific loggers to debug level
        logging.getLogger('monitor.core.log_processor').setLevel(logging.DEBUG)
        logging.getLogger('monitor.services.decision_engine').setLevel(logging.DEBUG)
        logging.getLogger('monitor.services.devices_db').setLevel(logging.DEBUG)
    
    def start(self):
        """Start both LogProcessor and DecisionEngine"""
        print("🔍 DEBUG MODE ENABLED - Verbose logging active")
        print("🤖 Starting LogProcessor + DecisionEngine")
        print("=" * 60)
        
        # Create Qt application
        self.app = QCoreApplication(sys.argv)
        
        # Setup logging and signal handlers
        self.setup_logging()
        self.setup_signal_handlers()
        
        # Create DecisionEngine in separate thread
        self.decision_thread, self.decision_engine = create_decision_engine_thread(self.db_directory)
        
        # Create LogProcessor
        self.processor = LogProcessor(
            db_directory=self.db_directory,
            batch_interval=self.batch_interval
        )
        
        # Connect LogProcessor signals to DecisionEngine
        self.processor.new_logs_processed.connect(self.decision_engine.on_new_logs_processed)
        self.processor.no_logs_found.connect(self.decision_engine.on_no_logs_found)
        self.processor.error_occurred.connect(
            lambda error: print(f"LogProcessor Error: {error}")
        )
        
        # Connect DecisionEngine signals for monitoring
        self.decision_engine.decision_made.connect(self.on_decision_made)
        self.decision_engine.alert_triggered.connect(self.on_alert_triggered)
        self.decision_engine.evaluation_finished.connect(self.on_evaluation_finished)
        self.decision_engine.error_occurred.connect(
            lambda error: print(f"DecisionEngine Error: {error}")
        )
        
        # Start the decision engine thread
        self.decision_thread.start()
        print("✅ DecisionEngine thread started")
        
        # Start the log processor
        self.processor.start()
        print("✅ LogProcessor started")
        
        print(f"📊 Database directory: {self.db_directory.absolute()}")
        print(f"⏱️  Batch interval: {self.batch_interval} seconds")
        print("🔄 Monitoring for log entries and making decisions...")
        print("Press Ctrl+C to stop")
        print()
        
        # Run the Qt event loop
        return self.app.exec()
    
    def stop(self):
        """Stop both services"""
        print("\n🛑 Stopping services...")
        
        if self.processor:
            self.processor.stop()
            print("✅ LogProcessor stopped")
        
        if self.decision_thread:
            self.decision_thread.quit()
            self.decision_thread.wait(3000)  # Wait up to 3 seconds
            print("✅ DecisionEngine thread stopped")
    
    def on_decision_made(self, device_id: str, decision_type: str, decision_data: dict):
        """Handle decision made signal"""
        print(f"🧠 DECISION: {device_id} -> {decision_type}")
        if decision_type == "FAILURE_ALERT":
            consecutive = decision_data.get('consecutive_failures', 0)
            alert_level = decision_data.get('alert_level', 'UNKNOWN')
            print(f"   📈 {consecutive} consecutive failures ({alert_level} alert)")
        elif decision_type == "RECOVERY":
            consecutive = decision_data.get('consecutive_successes', 0)
            print(f"   💚 Recovery: {consecutive} consecutive successes")
        elif decision_type == "PATTERN_ALERT":
            pattern = decision_data.get('pattern', '')
            print(f"   🔄 Pattern alert: {pattern}")
    
    def on_alert_triggered(self, device_id: str, alert_level: str, message: str):
        """Handle alert triggered signal"""
        emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡", "LOW": "ℹ️", "INFO": "✅"}.get(alert_level, "📢")
        print(f"{emoji} ALERT [{alert_level}]: {message}")
    
    def on_evaluation_finished(self, device_count: int):
        """Handle evaluation finished signal"""
        if device_count > 0:
            print(f"🔍 Evaluated {device_count} devices")

def main():
    parser = argparse.ArgumentParser(description='Run LogProcessor with DecisionEngine')
    parser.add_argument('--db-directory', type=str, default='data',
                       help='Directory containing the log database files (default: data)')
    parser.add_argument('--batch-interval', type=float, default=3.0,
                       help='Interval between batch processing in seconds (default: 3.0)')
    
    args = parser.parse_args()
    
    # Create database directory path
    db_dir = Path(args.db_directory)
    db_dir.mkdir(exist_ok=True)
    
    # Create and run the application
    app = LogProcessorWithDecisionEngine(db_dir, args.batch_interval)
    try:
        sys.exit(app.start())
    except Exception as e:
        print(f"💥 Error: {e}")
        app.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
