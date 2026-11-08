# V-Vet Symptom Extractor

A FastAPI service that reads a farmer's free-text message about a sick cow, extracts the livestock warning signs that are mentioned, and flags whether the case needs urgent escalation to a vet.

```
"My cow is not eating and foam is coming from her mouth."
        │
        ▼
{
  "findings": [
    {"sign_id": "reduced_appetite", "value": "yes", "quote": "not eating"},
    {"sign_id": "froth_nose_mouth", "value": "yes", "quote": "foam is coming from her mouth"}
  ],
  "escalate": true,
  "reason": "Urgent sign detected: froth_nose_mouth"
}
```

The LLM (via Groq) is only used to **extract** signs. It does not diagnose diseases or decide on escalation. Escalation is a fixed, rule-based check in Python so it is predictable and testable.

## Recognised signs

| `sign_id` | Meaning | Urgent |
|---|---|---|
| `reduced_appetite` | Eating less, stopped eating or grazing | |
| `weakness` | Dull, weak, lying down more than usual | |
| `swelling` | Lump below the ear, under the jaw or in front of the shoulder (*mbandabvu*) | |
| `rapid_breathing` | Breathing fast while resting | |
| `cloudy_eye` | Eye looks white, grey or milky | ✅ |
| `froth_nose_mouth` | Foam or froth from the nose or mouth | ✅ |
| `red_urine` | Urine red, brown or the colour of strong tea | |
| `unable_to_stand` | Cannot get up or stay standing | ✅ |
| `ticks` | Ticks visible on the animal | |

Each finding has a `value` of `yes`, `no` or `not_sure`. A case is escalated when an urgent sign is `yes` **or** `not_sure`, so an uncertain report of a dangerous sign is still escalated.

## How it works

1. **Request validation** (`app/models.py`): the message is trimmed and must be 1–2000 characters.
2. **Extraction** (`app/extract.py`): the message is sent to Groq with a system prompt listing the nine signs and the exact JSON shape to return (JSON mode, temperature 0).
3. **Parsing**: the JSON is converted to `Finding` objects. A field validator normalises values such as `"Not Sure"`, `"maybe"` or `"uncertain"` to `not_sure`.
4. **Post-validation** (`app/validator.py`): duplicate signs are dropped, and so is any finding whose quote does not appear in the farmer's message. This guards against the model inventing symptoms.
5. **Escalation** (`app/escalation.py`): rule-based check against the urgent signs.

## Project structure

```
app/
  main.py         FastAPI app, /extract endpoint, HTTP error handlers
  extract.py      Groq call, prompt, response parsing
  llm.py          Groq client and model configuration
  models.py       Pydantic models and sign definitions
  validator.py    Duplicate and quote checks on extracted findings
  escalation.py   Urgent-sign escalation rules
  errors.py       Custom exception types
tests/
  test_api.py             Endpoint test (Groq mocked)
  test_extract.py         Extraction test (Groq mocked)
  test_escalation.py      Escalation rules
  test_error_handling.py  Failure cases (bad JSON, missing findings, invalid signs, API errors)
```

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key
# Optional, defaults to openai/gpt-oss-120b
GROQ_MODEL=openai/gpt-oss-120b
```

`.env` is in `.gitignore`. Never commit your API key.

## Running

```bash
uv run uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

Example request:

```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"message": "My cow is not eating and foam is coming from her mouth."}'
```

## Error handling

| Situation | Response |
|---|---|
| Message empty or longer than 2000 characters | `422` |
| Groq returns invalid or empty JSON | `502` |
| Groq response has no `findings` list | `502` |
| A single finding has an unknown sign, bad value or missing quote | That finding is skipped and logged; valid findings are still returned |
| Groq rate limit | `429`, with Groq's `Retry-After` header passed through |
| Groq unreachable, timed out, or other API error | `503` |

Invalid findings are skipped rather than failing the whole request so that one bad item from the model cannot hide a real urgent sign. The Groq client retries connection errors, rate limits and server errors twice before an error is returned.

## Tests

```bash
uv run pytest -v
```

All tests mock the Groq API, so they run offline and use no API credits. `GROQ_API_KEY` must still be set, because `app/llm.py` reads it when it is imported, but any value works.

## Limitations

- The quote check is an exact (case-insensitive) substring match. If the model paraphrases instead of quoting, a correct finding is dropped.
- Extraction quality depends on the LLM. The service has only been tried with English messages.
- This tool supports triage. It is not a diagnosis and does not replace a vet.

## Use of AI assistance

I used [Claude Code](https://claude.com/claude-code) for help in some parts of this project:

- Tests
- Error handling (`app/errors.py`, the error handling in `app/extract.py`, and the exception handlers in `app/main.py`)
- Model and validator customisation
- Setup and debugging: Groq client configuration in `app/llm.py`, pytest configuration, and fixing import errors

I reviewed all AI-assisted code before keeping it. The rest of the code, mainly the parts without comments, I wrote myself.
