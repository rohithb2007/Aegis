import os
import pytest
from protected.models import GatewayStatus, WorkspaceBoundary, ProtectedContext, ProtectedResponse


def test_workspace_boundary_inside():
    boundary = WorkspaceBoundary(workspace_root=os.getcwd())
    # Inside path
    sub_file = os.path.join(os.getcwd(), "main.py")
    assert boundary.is_path_inside(sub_file) is True


def test_workspace_boundary_outside_traversal():
    boundary = WorkspaceBoundary(workspace_root=os.getcwd())
    # Traversal escaping root
    outside_path = os.path.abspath(os.path.join(os.getcwd(), "..", "..", "outside.txt"))
    assert boundary.is_path_inside(outside_path) is False


def test_protected_context_serialization():
    ctx = ProtectedContext(
        workspace_root="/app",
        cwd="/app/src",
        session_id="sess-123",
        task_id="task-456",
        user_goal="Build app",
        workflow_phase="IMPLEMENTATION"
    )
    d = ctx.to_dict()
    assert d["workspace_root"] == "/app"
    assert d["session_id"] == "sess-123"
    assert d["task_id"] == "task-456"


def test_protected_response_console_rendering():
    res = ProtectedResponse(
        gateway_status=GatewayStatus.PERMITTED,
        command="git status",
        policy_decision="ALLOW",
        enforcement_status="SIMULATED",
        explanation="Command permitted automatically."
    )
    d = res.to_dict()
    assert d["gateway_status"] == "PERMITTED"
    assert d["command"] == "git status"

    console = res.render_console()
    assert "AEGIS PROTECTED WORKSPACE PROXY" in console
    assert "PERMITTED" in console
    assert "git status" in console
