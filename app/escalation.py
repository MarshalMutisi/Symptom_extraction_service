
from app.models import Finding, FindingValue, SignID

URGENT_SIGNS = {
    SignID.FROTH_NOSE_MOUTH,
    SignID.UNABLE_TO_STAND,
    SignID.CLOUDY_EYE,
}


def check_escalation(findings: list[Finding]) -> tuple[bool, str]:

    for finding in findings:

        if (
            finding.sign_id in URGENT_SIGNS
            and finding.value in {
                FindingValue.YES,
                FindingValue.NOT_SURE,
            }
        ):
            return True, f"Urgent sign detected: {finding.sign_id.value}"

    return False, "No urgent signs detected."
