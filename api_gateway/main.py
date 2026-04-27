from fastapi import FastAPI
from api_gateway.routers import webhook

app = FastAPI(title="Sieve API Gateway", version="1.0.0")

# Include webhook router
app.include_router(webhook.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Sieve API Gateway",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
