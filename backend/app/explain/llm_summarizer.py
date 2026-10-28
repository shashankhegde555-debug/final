import json
import urllib.request
from typing import Dict, Any, Optional
from backend.app.config import config
from backend.app.models import Incident

# Catalogue of 18 server problem archetypes and their curated water-pipe analogies
SERVER_ROOT_CAUSES_CATALOGUE = {
    "database_slowdown": {
        "title": "Database Slowdown",
        "analogy": "The main water tank is clogged, so every tap in the building runs slowly.",
        "description": "The database storage or query engine is blocked, causing CPU spikes on dependent services waiting on connections, slow API responses, and cascading gateway timeouts."
    },
    "memory_leak_oom": {
        "title": "Out of Memory (Memory Leak)",
        "analogy": "A slow leak that gradually fills the basement over days until the equipment floods.",
        "description": "A service steadily consumes RAM without releasing it, eventually getting killed by the OS OOM killer and triggering restart loops."
    },
    "disk_full": {
        "title": "Disk Full",
        "analogy": "The drain pipe is blocked and the tub overflows.",
        "description": "Volume storage reached 100% capacity, preventing database WAL writes, log output, and transaction commits."
    },
    "traffic_spike": {
        "title": "Traffic Spike (Overload)",
        "analogy": "Everyone in the building flushes the toilet at the exact same second.",
        "description": "A sudden surge in external requests saturates edge ingress, causing thread pool contention and queue backlogs across downstream microservices."
    },
    "bad_deployment": {
        "title": "Bad Deployment / Release",
        "analogy": "A plumber replaced a pipe but installed the wrong diameter fitting.",
        "description": "A freshly released software version introduced a breaking API schema mismatch or unhandled exception immediately after rollout."
    },
    "network_partition": {
        "title": "Network Partition / Connectivity Failure",
        "analogy": "A pipe joint cracked, preventing water from reaching the upper floors.",
        "description": "Network packet loss, routing drops, or firewall drops prevent services from communicating, triggering connection timeouts."
    },
    "dns_failure": {
        "title": "DNS Name Resolution Failure",
        "analogy": "The building directory is erased, so nobody knows which room to deliver mail to.",
        "description": "Core DNS cluster is dropping lookups, resulting in 'Host Not Found' errors across dependent client services."
    },
    "expired_certificate": {
        "title": "Expired SSL/TLS Certificate",
        "analogy": "The electronic master keycard expired, instantly locking every security door.",
        "description": "The TLS certificate expired, causing client handshakes and mTLS connections between services to be rejected."
    },
    "third_party_outage": {
        "title": "Third-Party Dependency Outage",
        "analogy": "The municipal city water supply is shut off at the street main.",
        "description": "An external API provider (e.g. Stripe, Twilio) is returning HTTP 5xx errors or timing out, halting internal flows."
    },
    "connection_pool_exhaustion": {
        "title": "Connection Pool Exhaustion",
        "analogy": "All the taps are open simultaneously, dropping water pressure to an unusable trickle.",
        "description": "All available database/cache connection slots are exhausted, queuing incoming queries until clients timeout."
    },
    "queue_backlog": {
        "title": "Queue Backlog",
        "analogy": "The factory conveyor belt jams and packages pile up on the floor.",
        "description": "Worker throughput is lower than ingestion rate, causing message age and worker memory usage to climb."
    },
    "cache_failure": {
        "title": "Cache Cluster Failure",
        "analogy": "The express highway is blocked, forcing all city traffic onto narrow residential streets.",
        "description": "The in-memory Redis/Memcached tier failed or experienced high eviction, routing 100% of read traffic to the slow underlying database."
    },
    "crash_loop": {
        "title": "Crash Loop Backoff",
        "analogy": "A faulty water pump kicks on, sputters, and shuts down every thirty seconds.",
        "description": "Application container fails health checks upon boot and repeatedly restarts."
    },
    "cpu_overload": {
        "title": "CPU Overload (Runaway Process)",
        "analogy": "One industrial tap monopolizes the entire building's water pressure.",
        "description": "A single unoptimized compute thread consumes 100% CPU, starving neighboring services on the same host."
    },
    "configuration_mistake": {
        "title": "Configuration Mistake",
        "analogy": "Someone turned the wrong valve by hand and shut off the cold line.",
        "description": "An operator modified an environment variable or rate limit, causing sudden errors on one specific service."
    },
    "hardware_failure": {
        "title": "Hardware / Node Failure",
        "analogy": "A main pump motor burns out completely.",
        "description": "A physical server or hypervisor crashed, triggering pod rescheduling and temporary connection blips."
    },
    "retry_storm": {
        "title": "Retry Storm",
        "analogy": "People yank on a stuck door harder and harder until the handle snaps.",
        "description": "Clients aggressively retry failed requests without exponential backoff, multiplying traffic on already struggling services."
    },
    "scheduled_job_collision": {
        "title": "Scheduled Job Collision",
        "analogy": "The washing machine, dishwasher, and sprinkler system all start at 2:00 AM sharp.",
        "description": "A heavy maintenance job coincides with operational load, causing transient CPU/IO spikes (often benign background noise)."
    }
}

class LLMSummarizer:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.2"):
        self.ollama_url = ollama_url
        self.model = model

    def infer_root_cause_type(self, incident: Incident) -> str:
        """Determines the closest archetype among the 18 root causes based on incident alerts."""
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

        # Curated deterministic fallback
        water_pipe = archetype["analogy"]
        diagnostic = (
            f"Likely Root Cause: {archetype['title']} on {incident.origin.service}. "
            f"{archetype['description']} "
            f"Cascaded to {len(incident.services)} dependent services: {', '.join(incident.services[:5])}."
        )

        # Try querying local 2B model if enabled
        if config.enable_llm_explanations:
            prompt = (
                f"You are an on-call site reliability engineering assistant. "
                f"We detected an alert storm involving {len(incident.alerts)} alerts across {len(incident.services)} services. "
                f"Our deterministic graph-aware algorithm identified '{incident.origin.service}' as the probable root cause "
                f"with {int(incident.origin.confidence*100)}% confidence. "
                f"Problem archetype: {archetype['title']}. "
                f"Alert samples: {[a.name for a in incident.alerts[:3]]}. "
                f"Provide a 2-sentence plain-English executive summary for the on-call engineer, "
                f"including this water pipe analogy: '{water_pipe}'."
            )
            try:
                payload = json.dumps({
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 120}
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
                        diagnostic = f"[AI Summary (Advisory via 2B model)] {ai_text}"
            except Exception:
                # Deterministic fallback preserved
                diagnostic = f"[Deterministic Summary] {diagnostic}"

        return {
            "root_cause_type": archetype_key,
            "root_cause_title": archetype["title"],
            "water_pipe_analogy": water_pipe,
            "diagnostic_summary": diagnostic
        }

llm_summarizer = LLMSummarizer()
