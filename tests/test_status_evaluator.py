"""Tests for StatusEvaluator class"""

import unittest
from datetime import datetime
from monitor.services.status_evaluator import StatusEvaluator
from monitor.services.device_status_models import DeviceStatusInfo


class TestStatusEvaluator(unittest.TestCase):
    """Test cases for StatusEvaluator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.evaluator = StatusEvaluator(fail_threshold=3)  # Lower threshold for testing
        self.test_time = datetime.now()
    
    def test_new_device_gets_initial_status_from_first_log(self):
        """Test that new devices get their initial status from the first log"""
        # New device with empty status
        new_device = DeviceStatusInfo(
            device_id='device1',
            current_status='',
            last_log_status='',
            count=0,
            last_updated=self.test_time
        )
        
        # Process a success log
        result = self.evaluator.evaluate_status_after_log(new_device, 'success')
        
        self.assertEqual(result.current_status, 'success')
        self.assertEqual(result.last_log_status, 'success')
        self.assertEqual(result.count, 1)
    
    def test_immediate_recovery_on_success(self):
        """Test that device immediately recovers to success on any success log"""
        # Device currently failed
        failed_device = DeviceStatusInfo(
            device_id='device1',
            current_status='fail',
            last_log_status='fail',
            count=5,
            last_updated=self.test_time
        )
        
        # Process a success log
        result = self.evaluator.evaluate_status_after_log(failed_device, 'success')
        
        self.assertEqual(result.current_status, 'success')
        self.assertEqual(result.last_log_status, 'success')
        self.assertEqual(result.count, 1)  # Reset count
    
    def test_failure_after_threshold(self):
        """Test that device fails after threshold consecutive failures"""
        # Device with 2 consecutive failures (below threshold)
        device = DeviceStatusInfo(
            device_id='device1',
            current_status='success',
            last_log_status='fail',
            count=2,
            last_updated=self.test_time
        )
        
        # Process another failure (should reach threshold of 3)
        result = self.evaluator.evaluate_status_after_log(device, 'fail')
        
        self.assertEqual(result.current_status, 'fail')
        self.assertEqual(result.last_log_status, 'fail')
        self.assertEqual(result.count, 3)
    
    def test_no_status_change_below_threshold(self):
        """Test that status doesn't change when below failure threshold"""
        # Device with 1 failure (below threshold)
        device = DeviceStatusInfo(
            device_id='device1',
            current_status='success',
            last_log_status='fail',
            count=1,
            last_updated=self.test_time
        )
        
        # Process another failure (still below threshold of 3)
        result = self.evaluator.evaluate_status_after_log(device, 'fail')
        
        self.assertEqual(result.current_status, 'success')  # Should remain success
        self.assertEqual(result.last_log_status, 'fail')
        self.assertEqual(result.count, 2)
    
    def test_count_reset_on_status_change(self):
        """Test that count resets when log status changes"""
        # Device with consecutive successes
        device = DeviceStatusInfo(
            device_id='device1',
            current_status='success',
            last_log_status='success',
            count=5,
            last_updated=self.test_time
        )
        
        # Process a failure log
        result = self.evaluator.evaluate_status_after_log(device, 'fail')
        
        self.assertEqual(result.current_status, 'success')  # Should remain success
        self.assertEqual(result.last_log_status, 'fail')
        self.assertEqual(result.count, 1)  # Count should reset
    
    def test_consecutive_same_status_increments_count(self):
        """Test that consecutive same status logs increment the count"""
        # Device with 3 consecutive successes
        device = DeviceStatusInfo(
            device_id='device1',
            current_status='success',
            last_log_status='success',
            count=3,
            last_updated=self.test_time
        )
        
        # Process another success log
        result = self.evaluator.evaluate_status_after_log(device, 'success')
        
        self.assertEqual(result.current_status, 'success')
        self.assertEqual(result.last_log_status, 'success')
        self.assertEqual(result.count, 4)  # Count should increment
    
    def test_should_status_change_method(self):
        """Test the should_status_change helper method"""
        # Device at threshold for failure
        device = DeviceStatusInfo(
            device_id='device1',
            current_status='success',
            last_log_status='fail',
            count=3,
            last_updated=self.test_time
        )
        
        self.assertTrue(self.evaluator.should_status_change(device))
        
        # Device below threshold
        device.count = 2
        self.assertFalse(self.evaluator.should_status_change(device))


if __name__ == '__main__':
    unittest.main()
