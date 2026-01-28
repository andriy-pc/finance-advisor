import logging
import sys

from fastapi import FastAPI

from advisor.api.v1.api import router
from advisor.lifespan import lifespan

log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=log_format)

app = FastAPI(title="Finance Advisor - Personal Finance Engine", lifespan=lifespan)

app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "System Operational"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
