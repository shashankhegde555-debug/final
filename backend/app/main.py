import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.config import config, AppConfig
from backend.app.models import Alert, Incident, RuleNoiseStats, EvaluationReport
from backend.app.ingest.schema_detect import loader
from backend.app.redact.redactor import redactor
from backend.app.correlate.engine import CorrelatorEngine
from backend.app.origin.ranker import OriginRanker
from backend.app.noise.analyzer import noise_analyzer
from backend.app.guard.recall_guard import RecallGuard
from backend.app.eval.metrics import EvaluationHarness
from backend.app.eval.baselines import (
    run_raw_baseline,
    run_service_window_baseline,
    run_keep_topology_processor_baseline
)
from backend.app.explain.llm_summarizer import llm_summarizer

from contextlib import asynccontextmanager

# In-memory application state
class AppState:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.incidents: List[Incident] = []
        self.gt_incidents: List[Dict[str, Any]] = []
        self.replay_idx: int = 0
        self.replay_speed: float = 1.0
        self.is_replaying: bool = False
        self.guard: Optional[RecallGuard] = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load dataset & topology
    loader.load_topology()
    state.alerts = loader.load_alerts()
    state.gt_incidents = loader.load_incidents()
    state.guard = RecallGuard(state.alerts)
    run_full_correlation()
    yield

app = FastAPI(
    title="AO-01 Alert Correlation & Root Cause Intelligence API",
    description="Deterministic alert grouping, graph-aware origin ranking, noise recommendation, and 2B LLM advisory explanations.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_full_correlation():
    service_to_app = {s: node.application for s, node in loader.services_dict.items()}
    engine = CorrelatorEngine(loader.graph, service_to_app, custom_config=config)
    raw_incidents = engine.correlate_stream(state.alerts)
    if state.guard:
        state.incidents = state.guard.protect_and_prioritize(raw_incidents, [])
    else:
        state.incidents = raw_incidents

    # Instant assignment of curated root cause brief descriptions
    for inc in state.incidents:
        archetype_key = llm_summarizer.infer_root_cause_type(inc)
        from backend.app.explain.llm_summarizer import SERVER_ROOT_CAUSES_CATALOGUE
        archetype = SERVER_ROOT_CAUSES_CATALOGUE.get(archetype_key, SERVER_ROOT_CAUSES_CATALOGUE["database_slowdown"])
        desc = (
            f"Root Cause: {archetype['title']} on '{inc.origin.service}'. "
            f"{archetype['description']} "
            f"Cascaded to {len(inc.services)} dependent services: {', '.join(inc.services[:5])}."
        )
        inc.ai_summary = desc
        inc.water_pipe_analogy = desc

@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "service": "ao01-alert-correlation",
        "total_alerts": len(state.alerts),
        "total_incidents": len(state.incidents),
        "graph_nodes": loader.graph.number_of_nodes(),
        "graph_edges": loader.graph.number_of_edges(),
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

# 1. Config management
@app.get("/api/config")
def get_config():
    return config.model_dump()

@app.put("/api/config")
def update_config(updated: AppConfig):
    global config
    config = updated
    run_full_correlation()
    return {"status": "updated", "config": config.model_dump()}

# 2. Redaction toggle
@app.get("/api/redaction")
def get_redaction_status():
    return {"redaction_enabled": config.redaction_enabled}

@app.put("/api/redaction")
def set_redaction_status(payload: Dict[str, bool]):
    val = payload.get("redaction_enabled", True)
    config.redaction_enabled = val
    return {"status": "success", "redaction_enabled": config.redaction_enabled}

# 3. Incidents feed & detail
@app.get("/api/incidents")
def list_incidents(
    limit: int = 50,
    offset: int = 0,
    severity: Optional[str] = None,
    protected_only: bool = False
):
    filtered = state.incidents
    if severity:
        filtered = [inc for inc in filtered if inc.severity.lower() == severity.lower()]
    if protected_only:
        filtered = [inc for inc in filtered if inc.has_real_signal]

    sliced = filtered[offset : offset + limit]

    # Apply redaction if enabled
    results = []
    for inc in sliced:
        inc_dict = inc.model_dump()
        if config.redaction_enabled:
            for a in inc_dict.get("alerts", []):
                a["message"] = redactor.redact_text(a.get("message", ""), True)
                if a.get("host"):
                    a["host"] = redactor._pseudonymize(a["host"], "host", redactor._host_cache)
                if a.get("customer_ref"):
                    a["customer_ref"] = redactor._pseudonymize(a["customer_ref"], "cust", redactor._cust_cache)
        results.append(inc_dict)

    return {
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "incidents": results
    }

@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: str):
    inc = next((i for i in state.incidents if i.incident_id == incident_id), None)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    # If explanation not yet generated, generate now
    if not inc.ai_summary:
        exp = llm_summarizer.generate_explanation(inc)
        inc.water_pipe_analogy = exp.get("brief_description", "")
        inc.ai_summary = exp.get("diagnostic_summary", "")

    inc_dict = inc.model_dump()
    if config.redaction_enabled:
        for a in inc_dict.get("alerts", []):
            a["message"] = redactor.redact_text(a.get("message", ""), True)
            if a.get("host"):
                a["host"] = redactor._pseudonymize(a["host"], "host", redactor._host_cache)
            if a.get("customer_ref"):
                a["customer_ref"] = redactor._pseudonymize(a["customer_ref"], "cust", redactor._cust_cache)

    return inc_dict

@app.post("/api/incidents/{incident_id}/explain")
def generate_incident_explanation(incident_id: str):
    inc = next((i for i in state.incidents if i.incident_id == incident_id), None)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    exp = llm_summarizer.generate_explanation(inc)
    inc.water_pipe_analogy = exp.get("brief_description", "")
    inc.ai_summary = exp.get("diagnostic_summary", "")
    return exp

# 4. Raw Alerts & Streaming
@app.get("/api/alerts")
def list_alerts(
    limit: int = 100,
    offset: int = 0,
    service: Optional[str] = None,
    source: Optional[str] = None
):
    filtered = state.alerts
    if service:
        filtered = [a for a in filtered if a.service == service]
    if source:
        filtered = [a for a in filtered if a.source == source]

    sliced = filtered[offset : offset + limit]
    results = []
    for a in sliced:
        d = a.model_dump()
        if config.redaction_enabled:
            d = redactor.redact_alert_dict(d, True)
        results.append(d)

    return {
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "alerts": results
    }

# 5. Service Topology
@app.get("/api/topology")
def get_topology(incident_id: Optional[str] = None):
    highlighted_services = []
    origin_service = None
    paths = []

    if incident_id:
        inc = next((i for i in state.incidents if i.incident_id == incident_id), None)
        if inc:
            highlighted_services = inc.services
            origin_service = inc.origin.service
            paths = [p.model_dump() for p in inc.origin.paths]

    nodes = []
    for s_name, data in loader.graph.nodes(data=True):
        nodes.append({
            "id": s_name,
            "label": s_name,
            "tier": data.get("tier", "service"),
            "application": data.get("application", "default"),
            "is_highlighted": s_name in highlighted_services,
            "is_origin": s_name == origin_service
        })

    edges = []
    for u, v in loader.graph.edges():
        edges.append({
            "source": u,
            "target": v,
            "is_active_path": any(
                u in p.get("path", []) and v in p.get("path", []) for p in paths
            )
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "highlighted_services": highlighted_services,
        "origin_service": origin_service
    }

# 6. Noise Studio & Recommendations
@app.get("/api/noise/rules")
def get_noise_rules():
    stats = noise_analyzer.analyze_rules(state.alerts)
    return {
        "total_rules": len(stats),
        "rules": [s.model_dump() for s in stats]
    }

class DecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"

@app.post("/api/noise/rules/{rule_key:path}/decision")
def set_rule_decision(rule_key: str, req: DecisionRequest):
    res = noise_analyzer.record_decision(rule_key, req.decision)
    return res

@app.get("/api/noise/what-if")
def get_what_if_impact():
    impact = noise_analyzer.compute_what_if_impact(state.alerts)
    return impact

# 7. Metrics & Benchmark Scoreboard
@app.get("/api/metrics")
def get_metrics():
    harness = EvaluationHarness(state.gt_incidents)
    service_to_app = {s: node.application for s, node in loader.services_dict.items()}

    # Evaluate all 4 methods
    report_raw = harness.evaluate("1. Raw (No Correlation)", state.alerts, run_raw_baseline(state.alerts))
    report_svc = harness.evaluate("2. Service-Window (10m)", state.alerts, run_service_window_baseline(state.alerts, 600.0))
    report_keep = harness.evaluate("3. Keep Topology (App 15m)", state.alerts, run_keep_topology_processor_baseline(state.alerts, service_to_app, 900.0))
    report_our = harness.evaluate("4. AO-01 Origin Engine (Ours)", state.alerts, state.incidents)

    return {
        "benchmarks": [
            report_raw.model_dump(),
            report_svc.model_dump(),
            report_keep.model_dump(),
            report_our.model_dump()
        ],
        "summary": {
            "notification_reduction": report_our.notification_reduction,
            "incident_recall": report_our.incident_recall,
            "pairwise_f1": report_our.pairwise_f1,
            "median_time_to_surface_sec": report_our.time_to_surface.median_sec,
            "origin_accuracy_top1": report_our.origin_accuracy_top1
        }
    }

@app.post("/api/evaluate")
def rerun_evaluation():
    run_full_correlation()
    return get_metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
