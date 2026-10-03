import pytest
from ai_supervisor.models import (
    SupervisorVerdict, SupervisorAlignment, RecommendedAction, SupervisorAssessment
)


def test_supervisor_assessment_serialization():
    assessment = SupervisorAssessment(
        verdict=SupervisorVerdict.ALIGNED,
        confidence="HIGH",
        alignment=SupervisorAlignment.ALIGNED,
        explanation="The test execution directly aligns with active debugging task.",
        concerns=[],
        recommended_action=RecommendedAction.NO_CONCERN,
        model="mock-supervisor",
        command="python -m pytest -v",
        safety_classification="SAFE",
        safety_score=0
    )

    data = assessment.to_dict()
    assert data["verdict"] == "ALIGNED"
    assert data["confidence"] == "HIGH"
    assert data["alignment"] == "ALIGNED"
    assert data["recommended_action"] == "NO_CONCERN"
    assert data["model"] == "mock-supervisor"
    assert data["command"] == "python -m pytest -v"
