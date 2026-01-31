from pydantic import BaseModel


class AddTransactionIntentResult(BaseModel):
    success: bool
    message: str | None = None
