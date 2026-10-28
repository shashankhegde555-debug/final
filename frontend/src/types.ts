export interface Alert {
  alert_id: string;
  timestamp: string;
  timestamp_epoch: number;
  source: string;
  service: string;
  severity: string;
  name: string;
  message: string;
  host?: string;
  customer_ref?: string;
  incident_id?: string;
  rule_key?: string;
  dedup_count: number;
  first_seen?: string;
  last_seen?: string;
}

export interface EdgeReason {
  a: string;
  b: string;
  score: number;
  time_gap_sec: number;
  graph_distance: number;
  text_similarity: number;
  is_directed_path: boolean;
  reason: string;
}

export interface OriginRankingItem {
  service: string;
  score: number;
  upstream_score: number;
  earliness: number;
  prior: number;
  first_alert_time?: string;
}

export interface DependencyPath {
  to_service: string;
  path: string[];
}

export interface OriginInfo {
  service: string;
  confidence: number;
  ranking: OriginRankingItem[];
  paths: DependencyPath[];
}

export interface PriorityBreakdown {
  score: number;
  factors: Record<string, number>;
}

export interface Incident {
  incident_id: string;
  summary: string;
  origin: OriginInfo;
  alerts: Alert[];
  services: string[];
  start_time: string;
  end_time: string;
  severity: string;
  priority: PriorityBreakdown;
  edges: EdgeReason[];
  protected_alerts: string[];
  has_real_signal: boolean;
  ai_summary?: string;
  water_pipe_analogy?: string;
  params: Record<string, any>;
  is_closed: boolean;
}

export interface RuleNoiseStats {
  rule_key: string;
  source: string;
  service: string;
  normalized_name: string;
  n_fires: number;
  n_linked: number;
  link_rate: number;
  recommendation: string;
  evidence: string;
  risk_note: string;
  decision?: string;
  decision_timestamp?: string;
}

export interface TimeToSurfaceStats {
  median_sec: number;
  p90_sec: number;
  max_sec: number;
  late_count: number;
}

export interface EvaluationReport {
  method: string;
  raw_alerts: number;
  incident_cards: number;
  notification_reduction: number;
  cards_per_true_incident: number;
  alerts_per_card: number;
  incident_recall: number;
  missed_incidents: string[];
  pairwise_precision: number;
  pairwise_recall: number;
  pairwise_f1: number;
  adjusted_rand_index: number;
  v_measure: number;
  origin_accuracy_top1: number;
  origin_accuracy_top3: number;
  explainability_coverage: number;
  time_to_surface: TimeToSurfaceStats;
}

export interface TopologyNode {
  id: string;
  label: string;
  tier: string;
  application: string;
  is_highlighted?: boolean;
  is_origin?: boolean;
}

export interface TopologyEdge {
  source: string;
  target: string;
  is_active_path?: boolean;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  highlighted_services?: string[];
  origin_service?: string;
}
