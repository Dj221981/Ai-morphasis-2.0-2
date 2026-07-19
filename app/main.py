from fastapi import FastAPI

app = FastAPI(title="Ai-morphasis-2.0-2")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Ai-morphasis 2.0-2 API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
