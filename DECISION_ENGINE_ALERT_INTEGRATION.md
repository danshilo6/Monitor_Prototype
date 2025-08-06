# DecisionEngine Alert Integration

## Overview
The DecisionEngine uses a signal-based architecture to integrate with the AlertDatabase, following the same pattern as the AlertsPage. This ensures loose coupling and real-time updates. The system has been simplified to remove the "resolved" status - alerts are either active (in database) or resolved (deleted from database).

## Signal Architecture

### DecisionEngine Signals (Emits)
- `alert_creation_requested(Alert)` - Emitted when a device fails and needs an alert
- `alert_resolution_requested(str)` - Emitted when a device recovers (device_id)

### AlertDatabase Signals (Emits) 
- `alert_added(Alert)` - Emitted when an alert is successfully added
- `alert_resolved(str)` - Emitted when an alert is deleted (alert_id)

## Integration Example

```python
# In main application setup (e.g., main_window.py or app.py)

from monitor.core.decision_engine import DecisionEngine
from monitor.services.alert_db import AlertDatabase

# Create instances
decision_engine = DecisionEngine(db_directory)
alert_db = AlertDatabase()

# Connect DecisionEngine signals TO AlertDatabase methods
decision_engine.alert_creation_requested.connect(alert_db.add_alert)
decision_engine.alert_resolution_requested.connect(alert_db.resolve_alerts_for_device)

# Optional: Connect AlertDatabase signals FROM DecisionEngine for logging
alert_db.alert_added.connect(lambda alert: logger.info(f"Alert created by decision engine: {alert.id}"))
alert_db.alert_resolved.connect(lambda alert_id: logger.info(f"Alert deleted by decision engine: {alert_id}"))

# If running in separate thread
decision_thread = QThread()
decision_engine.moveToThread(decision_thread)
decision_thread.started.connect(decision_engine.start)
decision_thread.start()
```

## How It Works

1. **Device Failure Detection**: DecisionEngine detects device failure in `_process_device_evaluation()`
2. **Signal Emission**: DecisionEngine emits `alert_creation_requested` signal with Alert object
3. **Alert Creation**: AlertDatabase receives signal and calls `add_alert()` method
4. **Real-time Update**: AlertDatabase emits `alert_added` signal to update UI

5. **Device Recovery Detection**: DecisionEngine detects device recovery in `_process_device_evaluation()`
6. **Signal Emission**: DecisionEngine emits `alert_resolution_requested` signal with device_id
7. **Alert Deletion**: AlertDatabase receives signal and calls `resolve_alerts_for_device()` method (which deletes the alert)
8. **Real-time Update**: AlertDatabase emits `alert_resolved` signal to update UI

## Benefits

- **Loose Coupling**: DecisionEngine doesn't directly depend on AlertDatabase
- **Testability**: Easy to mock/test individual components
- **Real-time Updates**: Qt signals provide immediate UI updates
- **Consistency**: Same pattern used throughout the application (AlertsPage)
- **Thread Safety**: Qt signals handle cross-thread communication safely
- **Simplified Logic**: No resolved status tracking - alerts are either active or deleted
- **No UNIQUE Constraints**: Deleted alerts can't conflict with new ones

## Alert ID Format

Alerts created by DecisionEngine use the device_id directly as the alert ID. For thread devices, the device_id now matches the device_type for consistency:

**Thread devices:**
- `device_mode_thread` (device_id = device_type)
- `system_health` (device_id = device_type)  
- `thread` (device_id = device_type)

**Physical devices:**
- `192.168.1.205` (device_id = IP address)
- `COM3` (device_id = port name)

## Alert Types

All device types now have corresponding alert types:
- `camera` -> `AlertType.CAMERA`
- `sprinkler` -> `AlertType.SPRINKLER` 
- `fan` -> `AlertType.FAN`
- `group` -> `AlertType.GROUP`
- `thread` -> `AlertType.THREAD`
- `device_mode_thread` -> `AlertType.DEVICE_MODE_THREAD`
- `system_health` -> `AlertType.SYSTEM_HEALTH`
- `comport` -> `AlertType.COMPORT`
- `THI` -> `AlertType.THI`
- `unknown` -> `AlertType.UNKNOWN`

## Resolution Strategy

When a device recovers, the AlertDatabase deletes the alert by matching the exact device_id (since alert_id = device_id):
```sql
DELETE FROM alerts WHERE id = device_id
```

This ensures the specific device alert is removed when the device comes back online. The resolved functionality has been removed for simplicity - alerts are either active (in database) or resolved (deleted from database).
