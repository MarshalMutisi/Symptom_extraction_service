
import json
from unittest.mock import patch, MagicMock

from app.extract import extract_findings


def test_extract_findings_without_groq():

    fake_response = MagicMock()

    fake_response.choices[0].message.content = json.dumps({
        "findings": [
            {
                "sign_id": "reduced_appetite",
                "value": "yes",
                "quote": "not eating"
            }
        ]
    })

    with patch(
        "app.extract.client.chat.completions.create",
        return_value=fake_response
    ) as mock_groq:

        result = extract_findings("My cow is not eating.")

    assert len(result) == 1
    assert result[0].sign_id.value == "reduced_appetite"
    assert result[0].value.value == "yes"

    mock_groq.assert_called_once()
