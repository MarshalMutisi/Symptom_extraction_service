
import json
import logging

import groq
from pydantic import ValidationError

from app.errors import InvalidLLMResponseError, LLMRateLimitError, LLMServiceError
from app.llm import client, MODEL
from app.models import Finding
from app.validator import validate_findings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a veterinary symptom extraction assistant.

Your task is to extract symptoms explicitly mentioned
in a farmer's message.

You must recognize only these nine signs:

1. reduced_appetite:
   Eating less, stopped eating or stopped grazing.

2. weakness:
   Dull, weak or lying down more than usual.

3. swelling:
   A lump below the ear, under the jaw or in front
   of the shoulder. Farmers may call this mbandabvu.

4. rapid_breathing:
   Breathing fast while resting.

5. cloudy_eye:
   An eye that looks white, grey or milky.

6. froth_nose_mouth:
   Foam or froth coming from the nose or mouth.

7. red_urine:
   Urine that is red, brown or the colour of strong tea.

8. unable_to_stand:
   Cannot get up or stay standing.

9. ticks:
   Ticks visible on the animal.

Rules:

- Only return signs mentioned in the message.
- Do not invent symptoms.
- Use "yes" when the farmer clearly confirms a sign.
- Use "no" when the farmer explicitly denies a sign.
- Use "not_sure" when the farmer expresses uncertainty.
- Preserve a short supporting quote from the original message.
- Do not diagnose diseases.
- Do not make escalation decisions.

LANGUAGE SUPPORT:

- Understand English, Shona, and mixed
  English-Shona messages.
- Recognise symptoms even when farmers
  describe them using informal Shona.
- Do not require the farmer to translate
  their message into English.
- Return symptom IDs and values using
  the required English identifiers.
- Keep the quote exactly as it appears
  in the farmer's original message.
- Never invent a translation and present
  it as an original quote.


Return JSON in exactly this shape:

{
  "findings": [
    {"sign_id": "<one of the nine sign ids above>",
     "value": "yes" | "no" | "not_sure",
     "quote": "<short quote from the message>"}
  ]
}

If no signs are mentioned, return {"findings": []}.
"""

def _call_groq(message: str):
    """Call Groq and convert SDK errors into our own error types.

    The Groq client already retries connection errors, 429s and 5xx
    responses (2 retries by default) before any of these are raised.
    """
    try:
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
    except groq.RateLimitError as e:
        logger.warning("Groq rate limit hit: %s", e)
        raise LLMRateLimitError(
            "Groq rate limit reached.",
            retry_after=e.response.headers.get("retry-after"),
        ) from e
    except groq.APITimeoutError as e:
        logger.error("Groq request timed out: %s", e)
        raise LLMServiceError("Groq request timed out.") from e
    except groq.APIConnectionError as e:
        logger.error("Could not connect to Groq: %s", e)
        raise LLMServiceError("Could not connect to Groq.") from e
    except groq.APIStatusError as e:
        logger.error("Groq API error %s: %s", e.status_code, e)
        raise LLMServiceError(f"Groq API error (status {e.status_code}).") from e


def _parse_findings(content: str | None) -> list[Finding]:
    """Turn Groq's raw text into Finding objects, rejecting unusable output."""
    if not content or not content.strip():
        raise InvalidLLMResponseError("Groq returned an empty response.")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Groq returned invalid JSON: %r", content[:500])
        raise InvalidLLMResponseError("Groq returned invalid JSON.") from e

    if not isinstance(data, dict) or "findings" not in data:
        logger.error("Groq response missing 'findings': %r", content[:500])
        raise InvalidLLMResponseError("Groq response is missing 'findings'.")

    raw_findings = data["findings"]
    if not isinstance(raw_findings, list):
        raise InvalidLLMResponseError("'findings' in Groq response is not a list.")

    # Skip individual bad items (unknown sign_id, bad value, missing quote)
    # instead of failing the whole request, so valid urgent signs are kept.
    findings = []
    for item in raw_findings:
        if not isinstance(item, dict):
            logger.warning("Skipping non-object finding: %r", item)
            continue
        try:
            findings.append(Finding(**item))
        except ValidationError as e:
            logger.warning(
                "Skipping invalid finding %r: %s",
                item, e.errors(include_url=False),
            )

    return findings


def extract_findings(message: str) -> list[Finding]:

    response = _call_groq(message)

    if not response.choices:
        raise InvalidLLMResponseError("Groq returned no choices.")

    content = response.choices[0].message.content

    findings = _parse_findings(content)

    validated_findings = validate_findings(findings, message)

    return  validated_findings
    
