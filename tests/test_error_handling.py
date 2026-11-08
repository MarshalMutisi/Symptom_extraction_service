import json
from unittest.mock import MagicMock, patch

import groq
import httpx
import pytest
from fastapi.testclient import TestClient

from app.errors import InvalidLLMResponseError, LLMRateLimitError, LLMServiceError
from app.extract import extract_findings
from app.main import app

api = TestClient(app)

GROQ_CREATE = "app.extract.client.chat.completions.create"
MESSAGE = "My cow is not eating and foam is coming from her mouth."


def fake_groq_reply(content):
    response = MagicMock()
    response.choices[0].message.content = content
    return response


def fake_http_response(status_code, headers=None):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return httpx.Response(status_code, request=request, headers=headers)


# ---------- 1. Invalid JSON returned by Groq ----------

@pytest.mark.parametrize("content", ["not json at all", "{\"findings\": [", "", None])
def test_invalid_or_empty_json_raises(content):
    with patch(GROQ_CREATE, return_value=fake_groq_reply(content)):
        with pytest.raises(InvalidLLMResponseError):
            extract_findings(MESSAGE)


def test_invalid_json_returns_502():
    with patch(GROQ_CREATE, return_value=fake_groq_reply("oops")):
        response = api.post("/extract", json={"message": MESSAGE})

    assert response.status_code == 502


# ---------- 2. Missing findings in the AI response ----------

@pytest.mark.parametrize("payload", [{}, {"symptoms": []}, {"findings": "none"}, []])
def test_missing_or_malformed_findings_raises(payload):
    with patch(GROQ_CREATE, return_value=fake_groq_reply(json.dumps(payload))):
        with pytest.raises(InvalidLLMResponseError):
            extract_findings(MESSAGE)


def test_empty_findings_list_is_valid():
    with patch(GROQ_CREATE, return_value=fake_groq_reply('{"findings": []}')):
        assert extract_findings(MESSAGE) == []


# ---------- 3. Invalid symptom IDs or values ----------

def test_invalid_items_are_skipped_and_valid_ones_kept():
    payload = {
        "findings": [
            {"sign_id": "headache", "value": "yes", "quote": "not eating"},
            {"sign_id": "reduced_appetite", "value": "definitely", "quote": "not eating"},
            {"sign_id": "reduced_appetite", "value": "yes"},
            "froth_nose_mouth",
            {"sign_id": "froth_nose_mouth", "value": "yes",
             "quote": "foam is coming from her mouth"},
        ]
    }

    with patch(GROQ_CREATE, return_value=fake_groq_reply(json.dumps(payload))):
        result = extract_findings(MESSAGE)

    assert len(result) == 1
    assert result[0].sign_id.value == "froth_nose_mouth"


def test_urgent_sign_still_escalates_when_other_items_invalid():
    payload = {
        "findings": [
            {"sign_id": "made_up_sign", "value": "yes", "quote": "not eating"},
            {"sign_id": "froth_nose_mouth", "value": "yes",
             "quote": "foam is coming from her mouth"},
        ]
    }

    with patch(GROQ_CREATE, return_value=fake_groq_reply(json.dumps(payload))):
        response = api.post("/extract", json={"message": MESSAGE})

    assert response.status_code == 200
    assert response.json()["escalate"] is True


# ---------- 4. Groq API failures or rate limits ----------

def test_rate_limit_returns_429_with_retry_after():
    error = groq.RateLimitError(
        "rate limited",
        response=fake_http_response(429, headers={"retry-after": "12"}),
        body=None,
    )

    with patch(GROQ_CREATE, side_effect=error):
        with pytest.raises(LLMRateLimitError):
            extract_findings(MESSAGE)

        response = api.post("/extract", json={"message": MESSAGE})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "12"


@pytest.mark.parametrize("error", [
    groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com")),
    groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.com")),
    groq.InternalServerError("boom", response=fake_http_response(500), body=None),
    groq.AuthenticationError("bad key", response=fake_http_response(401), body=None),
])
def test_groq_failures_return_503(error):
    with patch(GROQ_CREATE, side_effect=error):
        with pytest.raises(LLMServiceError):
            extract_findings(MESSAGE)

        response = api.post("/extract", json={"message": MESSAGE})

    assert response.status_code == 503
