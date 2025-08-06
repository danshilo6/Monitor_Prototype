#!/usr/bin/env python3
"""
Quick test to verify that DecisionEngine and LogProcessor can share the same database
"""

import tempfile
import os
from pathlib import Path
from monitor.core.decision_engine import DecisionEngine

def test_shared_database():
    """Test that DecisionEngine and LogProcessor share the same database instance"""
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logs_dir = temp_path / "logs"
        data_dir = temp_path / "data"
        
        # Create directories
        logs_dir.mkdir()
        data_dir.mkdir()
        
        try:
            print("Creating DecisionEngine with shared database...")
            decision_engine = DecisionEngine(logs_dir, data_dir)
            
            # Check that both have database instances
            print(f"DecisionEngine database: {decision_engine.devices_db}")
            print(f"LogProcessor database: {decision_engine.log_processor.devices_db}")
            
            # Verify they are the same instance
            if decision_engine.devices_db is decision_engine.log_processor.devices_db:
                print("✓ SUCCESS: DecisionEngine and LogProcessor share the same database instance!")
            else:
                print("✗ FAIL: DecisionEngine and LogProcessor have different database instances")
                return False
            
            print("✓ Database sharing test passed!")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_shared_database()
