#!/usr/bin/env python3
"""
Run Log Processor Script

Script to run the actual LogProcessor within a Qt application context.
This properly tests the real LogProcessor with Qt timers and signals.
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

class LogProcessorApp:
    """Qt application wrapper for LogProcessor"""
    
    def __init__(self, db_directory: Path, batch_interval: float):
        self.db_directory = db_directory
        self.batch_interval = batch_interval
        self.processor = None
        self.app = None
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal, shutting down...")
            if self.processor:
                self.processor.stop()
            if self.app:
                QTimer.singleShot(100, self.app.quit)  # Give a moment for cleanup
        
        signal.signal(signal.SIGINT, signal_handler)
        # On Windows, also handle SIGBREAK (Ctrl+Break)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def run(self):
        """Run the LogProcessor in Qt application context"""
        print(f"Starting LogProcessor in Qt application context...")
        print(f"Database directory: {self.db_directory.absolute()}")
        print(f"Batch interval: {self.batch_interval} seconds")
        print("Press Ctrl+C to stop")
        print()
        
        # Create Qt application
        self.app = QCoreApplication(sys.argv)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Create and configure LogProcessor
        self.processor = LogProcessor(
            db_directory=self.db_directory, 
            batch_interval=self.batch_interval
        )
        
        # Connect signals for monitoring (optional)
        self.processor.new_logs_processed.connect(
            lambda count: print(f"Processed {count} new log entries.")
        )
        self.processor.no_logs_found.connect(
            lambda: print("No new logs found in this batch.")
        )
        self.processor.error_occurred.connect(
            lambda error: print(f"Error occurred: {error}")
        )
        
        # Start the processor
        try:
            self.processor.start()
            print("LogProcessor started successfully")
            print("Monitoring for log entries...")
            print()
            
            # Run the Qt event loop
            return self.app.exec()
            
        except Exception as e:
            print(f"Error starting LogProcessor: {e}")
            return 1
        finally:
            # Cleanup
            if self.processor:
                self.processor.stop()
            print("LogProcessor stopped.")

def main():
    parser = argparse.ArgumentParser(description='Run the LogProcessor in Qt application context')
    parser.add_argument('--db-directory', type=str, default='data',
                       help='Directory containing the log database files (default: data)')
    parser.add_argument('--batch-interval', type=float, default=3.0,
                       help='Interval between batch processing in seconds (default: 3.0)')
    
    args = parser.parse_args()
    
    # Enable debug logging for manual testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Set specific loggers to debug level
    logging.getLogger('monitor.core.log_processor').setLevel(logging.DEBUG)
    logging.getLogger('monitor.core.log_reader').setLevel(logging.DEBUG)
    logging.getLogger('monitor.services.devices_db').setLevel(logging.DEBUG)
    
    # Create database directory path
    db_dir = Path(args.db_directory)
    db_dir.mkdir(exist_ok=True)  # Ensure directory exists
    
    print("🔍 DEBUG MODE ENABLED - Verbose logging active")
    print("=" * 50)
    
    # Create and run the application
    app = LogProcessorApp(db_dir, args.batch_interval)
    sys.exit(app.run())

if __name__ == "__main__":
    main()
