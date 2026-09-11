"""HTTP entry point for tracking and service endpoints."""

from fastapi import FastAPI

app = FastAPI(
    title="Postupashki Marketing Measurement MVP",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Confirm that the application skeleton starts correctly."""
    return {"status": "ok"}
