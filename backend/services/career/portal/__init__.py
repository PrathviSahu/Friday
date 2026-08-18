"""backend/services/career/portal/__init__.py — Career Portal Automation Safety Package.
"""

from backend.services.career.portal.base import (
    BaseApplicationPortal,
    FieldSensitivity,
    classify_field_sensitivity,
)
from backend.services.career.portal.mock_portal import MockApplicationPortal
from backend.services.career.portal.engine import (
    PortalAutomationEngine,
    PortalSecurityError,
    PortalSession,
)

__all__ = [
    "BaseApplicationPortal",
    "FieldSensitivity",
    "classify_field_sensitivity",
    "MockApplicationPortal",
    "PortalAutomationEngine",
    "PortalSecurityError",
    "PortalSession",
]
