
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.models import ExtractRequest, ExtractResponse
from app.extract import extract_findings
from app.escalation import check_escalation
from app.errors import InvalidLLMResponseError, LLMRateLimitError, LLMServiceError

app = FastAPI(title="V-Vet Symptom Extraction API")


@app.exception_handler(LLMRateLimitError)
def rate_limit_handler(request: Request, exc: LLMRateLimitError):
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return JSONResponse(
        status_code=429,
        content={"detail": "The AI service is busy. Please try again shortly."},
        headers=headers,
    )


@app.exception_handler(LLMServiceError)
def service_error_handler(request: Request, exc: LLMServiceError):
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI service is unavailable. Please try again later."},
    )


@app.exception_handler(InvalidLLMResponseError)
def invalid_response_handler(request: Request, exc: InvalidLLMResponseError):
    return JSONResponse(
        status_code=502,
        content={"detail": "The AI service returned an unusable response. Please try again."},
    )


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest):

    findings = extract_findings(request.message)

    escalate, reason = check_escalation(findings)

    return ExtractResponse(
        findings=findings,
        escalate=escalate,
        reason=reason
    )
