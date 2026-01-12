from fastapi import FastAPI

from advisor.api.v1.api import router

app = FastAPI(title="Job Advisor - Personal Finance Engine")

app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "System Operational"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
