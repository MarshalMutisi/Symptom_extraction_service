class ExtractionError(Exception):
    """Base class for all symptom extraction failures."""


class InvalidLLMResponseError(ExtractionError):
    """Groq replied, but the content was not usable (bad JSON, missing findings)."""


class LLMServiceError(ExtractionError):
    """Groq could not be reached or returned an API error."""


class LLMRateLimitError(LLMServiceError):
    """Groq rejected the request because of rate limits."""

    def __init__(self, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.retry_after = retry_after
