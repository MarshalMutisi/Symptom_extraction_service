
from app.models import Finding
from app.escalation import check_escalation


def test_froth_triggers_escalation():
    findings = [
        Finding(
            sign_id="froth_nose_mouth",
            value="yes",
            quote="foam is coming from her mouth"
        )
    ]

    escalate, reason = check_escalation(findings)

    assert escalate is True
    assert "froth_nose_mouth" in reason


def test_reduced_appetite_does_not_trigger_escalation():
    findings = [
        Finding(
            sign_id="reduced_appetite",
            value="yes",
            quote="not eating"
        )
    ]

    escalate, reason = check_escalation(findings)

    assert escalate is False


def test_uncertain_urgent_sign_triggers_escalation():
    findings = [
        Finding(
            sign_id="unable_to_stand",
            value="not_sure",
            quote="might not be able to stand"
        )
    ]

    escalate, reason = check_escalation(findings)

    assert escalate is True
