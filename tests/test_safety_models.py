import pytest
from safety.models import (
    SafetyClassification, SafetyAction, CapabilityType, Reversibility, Scope, SafetyAssessment
)


def test_safety_assessment_to_dict():
    assessment = SafetyAssessment(
        command="npm install axios",
        classification=SafetyClassification.MEDIUM_RISK,
        action=SafetyAction.REVIEW_REQUIRED,
        score=38,
        reasons=["Downloads external package", "Modifies dependency state"],
        capabilities=[CapabilityType.NETWORK_ACCESS, CapabilityType.PACKAGE_INSTALLATION],
        reversibility=Reversibility.PARTIALLY_REVERSIBLE,
        scope=Scope.INSIDE_PROJECT,
        confidence="HIGH"
    )

    data = assessment.to_dict()
    assert data["command"] == "npm install axios"
    assert data["classification"] == "MEDIUM_RISK"
    assert data["action"] == "REVIEW_REQUIRED"
    assert data["score"] == 38
    assert "NETWORK_ACCESS" in data["capabilities"]
    assert "PACKAGE_INSTALLATION" in data["capabilities"]
    assert data["reversibility"] == "PARTIALLY_REVERSIBLE"
