"""Alert data models and dummy data for the Monitor Prototype"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List
import random

class AlertType(Enum):
    SPRINKLER = "sprinkler"
    FAN = "fan"
    CAMERA = "camera"
    SOFTWARE = "software"

@dataclass
class Alert:
    id: str
    alert_type: AlertType
    description: str
    timestamp: datetime

def generate_dummy_alerts() -> List[Alert]:
    """Generate dummy alerts for testing"""
    alerts = []
    
    # Sprinkler alerts (A-Z + group number - single sprinkler number)
    for i in range(3):
        letter = chr(65 + random.randint(0, 25))  # A-Z
        group = random.randint(1, 5)
        sprinkler_number = random.randint(1, 4)  # Single number
        alerts.append(Alert(
            id=f"sprinkler_{i}",
            alert_type=AlertType.SPRINKLER,
            description=f"{letter}{group} - {sprinkler_number}",
            timestamp=datetime.now()
        ))
    
    # Fan alerts (AY + group number - always 4 fan numbers)
    for i in range(2):
        group = random.randint(1, 5)
        # Always show all 4 fan numbers for dummy data
        fan_numbers = "1, 2, 3, 4"
        alerts.append(Alert(
            id=f"fan_{i}",
            alert_type=AlertType.FAN,
            description=f"AY{group} - {fan_numbers}",
            timestamp=datetime.now()
        ))
    
    # Camera alerts (IP addresses starting from 192.168.1.202)
    for i in range(3):
        ip = f"192.168.1.{202 + i}"
        alerts.append(Alert(
            id=f"camera_{i}",
            alert_type=AlertType.CAMERA,
            description=ip,
            timestamp=datetime.now()
        ))
    
    # Software alerts
    alerts.append(Alert(
        id="software_1",
        alert_type=AlertType.SOFTWARE,
        description="error",
        timestamp=datetime.now()
    ))
    
    return alerts
