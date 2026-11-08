
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_endpoint_without_groq():

    fake_response = MagicMock()

    fake_response.choices[0].message.content = """
    {
        "findings": [
            {
                "sign_id": "reduced_appetite",
                "value": "yes",
                "quote": "not eating"
            },
            {
                "sign_id": "froth_nose_mouth",
                "value": "yes",
                "quote": "foam is coming from her mouth"
            }
        ]
    }
    """

    with patch(
        "app.extract.client.chat.completions.create",
        return_value=fake_response
    ) as mock_groq:

        response = client.post(
            "/extract",
            json={
                "message": "My cow is not eating and foam is coming from her mouth."
            }
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data["findings"]) == 2
    assert data["escalate"] is True
    assert "froth_nose_mouth" in data["reason"]

    mock_groq.assert_called_once()
