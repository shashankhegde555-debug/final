from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Alert(BaseModel):
    alert_id: str
    timestamp: str  # ISO-8601 string
    timestamp_epoch: float
    source: str
    service: str
    severity: str  # critical, high, warning, info
    name: str
    message: str
    host: Optional[str] = None
    customer_ref: Optional[str] = None
    incident_id: Optional[str] = None  # Ground truth label if present
    rule_key: Optional[str] = None  # (source, service, normalized_name)
    dedup_count: int = 1
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

class ServiceNode(BaseModel):
    service: str
    tier: str  # edge, gateway, service, datastore, thirdparty
    application: str
    dependencies: List[str] = []

class EdgeReason(BaseModel):
    a: str
    b: str
    score: float
    time_gap_sec: float
    graph_distance: int
    text_similarity: float
    is_directed_path: bool = False
    reason: str

class OriginRankingItem(BaseModel):
    service: str
    score: float
    upstream_score: float
    earliness: float
    prior: float
    first_alert_time: Optional[str] = None

class DependencyPath(BaseModel):
    to_service: str
    path: List[str]

class OriginInfo(BaseModel):
    service: str
    confidence: float
    ranking: List[OriginRankingItem] = []
    paths: List[DependencyPath] = []

class PriorityBreakdown(BaseModel):
    score: float
    factors: Dict[str, float] = {}

class Incident(BaseModel):
    incident_id: str
    summary: str
    origin: OriginInfo
    alerts: List[Alert] = []
    services: List[str] = []
    start_time: str
    end_time: str
    severity: str
    priority: PriorityBreakdown
    edges: List[EdgeReason] = []
    protected_alerts: List[str] = []
    has_real_signal: bool = False
    ai_summary: Optional[str] = None
    ai_implication: Optional[str] = None
    water_pipe_analogy: Optional[str] = None
    params: Dict[str, Any] = {}
    is_closed: bool = False

class RuleNoiseStats(BaseModel):
    rule_key: str
    source: str
    service: str
    normalized_name: str
    n_fires: int
    n_linked: int
    link_rate: float
    median_lead_time_sec: Optional[float] = None
    recommendation: str  # "Suppress candidate", "Keep - insufficient evidence", "Raise threshold / add duration", "Keep and page", "Surface by default (novel)"
    evidence: str
    risk_note: str
    decision: Optional[str] = None  # "approved", "rejected", or None
    decision_timestamp: Optional[str] = None

class TimeToSurfaceStats(BaseModel):
    median_sec: float
    p90_sec: float
    max_sec: float
    late_count: int

class EvaluationReport(BaseModel):
    method: str
    raw_alerts: int
    incident_cards: int
    notification_reduction: float
    cards_per_true_incident: float
    alerts_per_card: float
    incident_recall: float
    missed_incidents: List[str] = []
    pairwise_precision: float
    pairwise_recall: float
    pairwise_f1: float
    adjusted_rand_index: float
    v_measure: float
    origin_accuracy_top1: float
    origin_accuracy_top3: float
    explainability_coverage: float
    time_to_surface: TimeToSurfaceStats
