import json
import urllib.request
from typing import Dict, Any, Optional
from backend.app.config import config
from backend.app.models import Incident

# Catalogue of 18 server problem archetypes and concise engineering descriptions
SERVER_ROOT_CAUSES_CATALOGUE = {
    "database_slowdown": {
        "title": "Database Query Bottleneck / Slowdown",
        "description": "The database query engine or storage layer is experiencing excessive lock contention or table scan delays, causing connection pool starvation and high latency across all client services."
    },
    "memory_leak_oom": {
        "title": "Out of Memory (Memory Leak)",
        "description": "Application memory usage progressively grew until hitting the container memory limit, triggering an OS OOM kill and restarting the service repeatedly."
    },
    "disk_full": {
        "title": "Disk Volume Exhaustion",
        "description": "The local volume reached 100% disk capacity, causing the database to reject write operations, abort transaction logs, and cascade write errors downstream."
    },
    "traffic_spike": {
        "title": "External Traffic Spike / Overload",
        "description": "A sudden burst in incoming client request volume saturated the edge ingress layer, causing thread pool contention and queue backlogs across downstream microservices."
    },
    "bad_deployment": {
        "title": "Faulty Release / Deployment Bug",
        "description": "A newly deployed software release introduced a breaking schema incompatibility or unhandled runtime exception, immediately triggering a high 5xx error rate."
    },
    "network_partition": {
        "title": "Network Partition / Connectivity Loss",
        "description": "Intermittent routing loss, packet drops, or firewall drops disrupted TCP handshakes between services, resulting in cascading connection timeouts."
    },
    "dns_failure": {
        "title": "DNS Name Resolution Failure",
        "description": "The internal DNS resolver cluster is dropping address queries, resulting in 'Host Not Found' exceptions across services attempting to resolve internal endpoints."
    },
    "expired_certificate": {
        "title": "Expired SSL/TLS Certificate",
        "description": "The server TLS certificate expired, causing client TLS handshakes and mutual TLS (mTLS) inter-service communication to be rejected immediately."
    },
    "third_party_outage": {
        "title": "Third-Party API Dependency Outage",
        "description": "An external provider API is returning HTTP 503 or timing out, blocking internal billing or dispatch pipelines that synchronously depend on it."
    },
    "connection_pool_exhaustion": {
        "title": "Connection Pool Exhaustion",
        "description": "All available connection slots in the shared pool are occupied, forcing incoming requests into an overflow backlog until timeout thresholds are breached."
    },
    "queue_backlog": {
        "title": "Message Queue Backlog",
        "description": "Incoming message ingestion rate exceeds worker consumer processing throughput, driving up queue latency, message age, and worker memory consumption."
    },
    "cache_failure": {
        "title": "In-Memory Cache Cluster Failure",
        "description": "The caching cluster suffered shard eviction or an outage, forcing 100% of read queries directly onto the underlying primary database and overloading it."
    },
    "crash_loop": {
        "title": "Crash Loop Backoff",
        "description": "The containerized process repeatedly crashes immediately following startup health checks, causing transient availability drops and request retries."
    },
    "cpu_overload": {
        "title": "CPU Overload / Runaway Process",
        "description": "A runaway thread or intensive computation consumed 100% CPU capacity on the host, starving co-located services of compute resources."
    },
    "configuration_mistake": {
        "title": "Configuration / Flag Misconfiguration",
        "description": "An erroneous parameter, bad environment variable, or strict rate limit was applied by operators, causing immediate operational failure on this component."
    },
    "hardware_failure": {
        "title": "Hardware / Node Eviction",
        "description": "The underlying virtual machine or physical node suffered a hardware failure, forcing pod rescheduling and temporary connectivity disruption."
    },
    "retry_storm": {
        "title": "Retry Storm Contention",
        "description": "Downstream clients synchronously retried failed requests without exponential backoff or jitter, multiplying total request load onto degraded backends."
    },
    "scheduled_job_collision": {
        "title": "Scheduled Heavy Job Collision",
        "description": "A heavy scheduled batch report or database backup ran during peak production traffic hours, producing temporary resource contention and I/O saturation."
    }
}

class LLMSummarizer:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.2"):
        self.ollama_url = ollama_url
        self.model = model

    def infer_root_cause_type(self, incident: Incident) -> str:
        text_corpus = " ".join([a.name + " " + a.message for a in incident.alerts]).lower()
        origin_svc = incident.origin.service.lower()

        if "wal" in text_corpus or "disk" in text_corpus or "enospc" in text_corpus:
            return "disk_full"
        if "lock" in text_corpus or ("db" in origin_svc and "timeout" in text_corpus):
            return "database_slowdown"
        if "oom" in text_corpus or "heap" in text_corpus or "leak" in text_corpus:
            return "memory_leak_oom"
        if "connectionpool" in text_corpus or "pool" in text_corpus or "too many connections" in text_corpus:
            return "connection_pool_exhaustion"
        if "rate" in text_corpus and "surge" in text_corpus or "flood" in text_corpus:
            return "traffic_spike"
        if "deploy" in text_corpus or "migration" in text_corpus or "syntax" in text_corpus:
            return "bad_deployment"
        if "dns" in text_corpus or "host not found" in text_corpus:
            return "dns_failure"
        if "ssl" in text_corpus or "tls" in text_corpus or "certificate" in text_corpus:
            return "expired_certificate"
        if "stripe" in text_corpus or "sendgrid" in text_corpus or "twilio" in text_corpus or "external" in text_corpus:
            return "third_party_outage"
        if "cache" in text_corpus or "redis" in text_corpus or "eviction" in text_corpus or "miss" in text_corpus:
            return "cache_failure"
        if "partition" in text_corpus or "timeout" in text_corpus:
            return "network_partition"
        return "database_slowdown"

    def generate_explanation(self, incident: Incident) -> Dict[str, str]:
        archetype_key = self.infer_root_cause_type(incident)
        archetype = SERVER_ROOT_CAUSES_CATALOGUE.get(archetype_key, SERVER_ROOT_CAUSES_CATALOGUE["database_slowdown"])

        # Curated deterministic root cause brief
        diagnostic = (
            f"Root Cause: {archetype['title']} on '{incident.origin.service}'. "
            f"{archetype['description']} "
            f"This impacted {len(incident.services)} dependent services: {', '.join(incident.services[:5])}."
        )

        # Query local 2B model for brief technical root-cause description
        if config.enable_llm_explanations:
            prompt = (
                f"You are a senior site reliability engineer. "
                f"We detected an alert storm of {len(incident.alerts)} alerts across {len(incident.services)} services. "
                f"Our deterministic graph analysis identified '{incident.origin.service}' as the root cause origin "
                f"(confidence: {int(incident.origin.confidence*100)}%). "
                f"Failure category: {archetype['title']}. "
                f"Alert names: {[a.name for a in incident.alerts[:3]]}. "
                f"Write a concise, 2-sentence technical root-cause brief description. "
                f"Directly explain: 1) What failed on '{incident.origin.service}', and "
                f"2) Why it is overloading downstream services. "
                f"Do NOT use metaphors or analogies; be direct, technical, and concise."
            )
            try:
                payload = json.dumps({
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 100}
                }).encode("utf-8")

                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    ai_text = res_data.get("response", "").strip()
                    if ai_text:
                        diagnostic = f"[2B Model Brief] {ai_text}"
            except Exception:
                diagnostic = f"[Deterministic Brief] {diagnostic}"

        return {
            "root_cause_type": archetype_key,
            "root_cause_title": archetype["title"],
            "brief_description": diagnostic,
            "water_pipe_analogy": diagnostic,
            "diagnostic_summary": diagnostic
        }

llm_summarizer = LLMSummarizer()
