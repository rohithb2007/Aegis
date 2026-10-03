"""
Aegis Protected Workspace & Command Proxy Package (V0.8)
"""

from .models import GatewayStatus, WorkspaceBoundary, ProtectedContext, ProtectedResponse
from .session import ProtectedSession
from .gateway import ProtectedGateway
from .proxy import CommandProxy
from .daemon import AegisGatewayDaemon
from .profile_installer import ProfileInstaller
from .protection import ProtectionManager

__all__ = [
    "GatewayStatus",
    "WorkspaceBoundary",
    "ProtectedContext",
    "ProtectedResponse",
    "ProtectedSession",
    "ProtectedGateway",
    "CommandProxy",
    "AegisGatewayDaemon",
    "ProfileInstaller",
    "ProtectionManager",
]


