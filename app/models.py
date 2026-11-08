
from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SignID(StrEnum):
    REDUCED_APPETITE = "reduced_appetite"
    WEAKNESS = "weakness"
    SWELLING = "swelling"
    RAPID_BREATHING = "rapid_breathing"
    CLOUDY_EYE = "cloudy_eye"
    FROTH_NOSE_MOUTH = "froth_nose_mouth"
    RED_URINE = "red_urine"
    UNABLE_TO_STAND = "unable_to_stand"
    TICKS = "ticks"


SIGN_DESCRIPTIONS: dict[SignID, str] = {
    SignID.REDUCED_APPETITE: "eating less, or has stopped eating or grazing",
    SignID.WEAKNESS: "dull, weak, lying down more than usual",
    SignID.SWELLING: "a lump below the ear, under the jaw, or in front of the shoulder (farmers may call it mbandabvu)",
    SignID.RAPID_BREATHING: "breathing fast while resting",
    SignID.CLOUDY_EYE: "the eye looks white, grey or milky",
    SignID.FROTH_NOSE_MOUTH: "foam or froth from the nose or mouth",
    SignID.RED_URINE: "urine that is red, brown, or the colour of strong tea",
    SignID.UNABLE_TO_STAND: "cannot get up or stay standing",
    SignID.TICKS: "ticks can be seen on the animal",
}


class FindingValue(StrEnum):
    YES = "yes"
    NO = "no"
    NOT_SURE = "not_sure"


class Finding(BaseModel):
    sign_id: SignID
    value: FindingValue
    quote: str = Field(min_length=1)

    @field_validator("value", mode="before")
    @classmethod
    def normalise_value(cls, v):
        if isinstance(v, str):
            v = v.strip().lower().replace(" ", "_").replace("-", "_")
            if v in {"unsure", "maybe", "uncertain"}:
                return "not_sure"
        return v


class ExtractRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)


class ExtractResponse(BaseModel):
    findings: list[Finding]
    escalate: bool
    reason: str
