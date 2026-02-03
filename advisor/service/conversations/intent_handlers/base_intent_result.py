from pydantic import BaseModel


class BaseIntentResult(BaseModel):
    success: bool
    message: str | None = None
