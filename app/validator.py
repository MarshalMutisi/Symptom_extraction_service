
from app.models import Finding


def validate_findings(
    findings: list[Finding],
    message: str
) -> list[Finding]:

    validated = []
    seen_signs = set()

    for finding in findings:

        # Reject duplicate symptoms
        if finding.sign_id in seen_signs:
            continue

        # Reject quotes that do not appear in the farmer's message
        if finding.quote.lower() not in message.lower():
            continue

        seen_signs.add(finding.sign_id)
        validated.append(finding)

    return validated
