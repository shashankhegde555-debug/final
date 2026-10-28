import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import config

app = FastAPI(
    title="AO-01 Alert Correlation & Root Cause Intelligence API",
    description="Deterministic alert grouping, graph-aware origin ranking, noise recommendation, and 2B LLM advisory explanations.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "service": "ao01-alert-correlation",
        "version": "1.0.0",
        "redaction_default": config.redaction_enabled,
        "keep_integration": {
            "url": config.keep_url,
            "dry_run": config.keep_dry_run
        },
        "llm_advisory": {
            "model": config.ollama_model,
            "url": config.ollama_url,
            "enabled": config.enable_llm_explanations
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
