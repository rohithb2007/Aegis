import os
import pytest
from protected.models import WorkspaceBoundary
from protected.gateway import ProtectedGateway


def test_protected_gateway_valid_scope():
    gw = ProtectedGateway(workspace_boundary=WorkspaceBoundary(workspace_root=os.getcwd()))
    ok, reasons = gw.validate_command_scope("git status")
    assert ok is True
    assert len(reasons) == 0


def test_protected_gateway_root_delete_scope_rejection():
    gw = ProtectedGateway(workspace_boundary=WorkspaceBoundary(workspace_root=os.getcwd()))
    ok, reasons = gw.validate_command_scope("rm -rf /")
    assert ok is False
    assert len(reasons) > 0
    assert "root or system" in reasons[0].lower()


def test_protected_gateway_system_dir_scope_rejection():
    gw = ProtectedGateway(workspace_boundary=WorkspaceBoundary(workspace_root=os.getcwd()))
    ok, reasons = gw.validate_command_scope("cat /etc/passwd")
    assert ok is False
    assert len(reasons) > 0


def test_protected_gateway_traversal_escape_rejection():
    gw = ProtectedGateway(workspace_boundary=WorkspaceBoundary(workspace_root=os.getcwd()))
    # Command attempting traversal far outside workspace
    ok, reasons = gw.validate_command_scope("ls ../../../../../../")
    assert ok is False
    assert len(reasons) > 0
