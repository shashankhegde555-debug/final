from pydantic import BaseModel, Field
from typing import Optional

class AppConfig(BaseModel):
    # Correlation hard gates & decay
    W: float = Field(default=15.0, description="Time window in minutes for hard gate")
    H: int = Field(default=2, description="Max graph distance hops for hard gate")
    tau: float = Field(default=5.0, description="Exponential time decay in minutes")
    
    # Pairwise weights & threshold
    w_t: float = Field(default=0.45, description="Weight for temporal affinity")
    w_g: float = Field(default=0.45, description="Weight for graph topology affinity")
    w_s: float = Field(default=0.10, description="Weight for text similarity")
    beta: float = Field(default=0.15, description="Bonus for direct upstream/downstream dependency path")
    theta: float = Field(default=0.50, description="Affinity threshold to join incident")
    
    # Anti-chaining & clustering lifecycle
    Q: float = Field(default=20.0, description="Quiet period in minutes before closing an incident")
    W_max: float = Field(default=60.0, description="Maximum incident duration in minutes (anti-chaining)")
    max_diameter: int = Field(default=4, description="Maximum dependency graph diameter for incident")
    
    # Origin ranking weights
    origin_w_upstream: float = Field(default=0.50, description="Weight for downstream reachability (upstream score)")
    origin_w_earliness: float = Field(default=0.30, description="Weight for alert earliness")
    origin_w_prior: float = Field(default=0.20, description="Weight for historical root-cause prior")
    
    # Safety & Redaction
    redaction_enabled: bool = Field(default=True, description="Enable automatic IP/host/customer redaction")
    
    # Keep Integration
    keep_url: str = Field(default="http://localhost:8080", description="Keep API base URL")
    keep_api_key: Optional[str] = Field(default=None, description="Keep X-API-KEY header")
    keep_dry_run: bool = Field(default=True, description="Dry run mode for Keep mutations")
    
    # 2B Model LLM Integration
    ollama_url: str = Field(default="http://127.0.0.1:11434", description="Ollama local endpoint")
    ollama_model: str = Field(default="llama3.2", description="2B/3B parameter model name")
    enable_llm_explanations: bool = Field(default=True, description="Generate advisory plain-English summaries")

config = AppConfig()
