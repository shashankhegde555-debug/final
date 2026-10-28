import json
import urllib.request
from typing import Dict, Any, Optional
from backend.app.config import config
from backend.app.models import Incident

# Catalogue of server problem archetypes with Brief Descriptions and What It Implies in Simple English
SERVER_ROOT_CAUSES_CATALOGUE = {
    "leader_election_timeout": {
        "title": "Quorum Leader Election Timeout",
        "brief": "The leader election process on '{service}' timed out while waiting for quorum votes from peer servers.",
        "implies": "What this implies: The cluster cannot elect a primary coordinator, blocking all write requests and causing connected applications to stall until consensus is restored."
    },
    "socket_connection_drop": {
        "title": "Client Socket Disconnection Storm",
        "brief": "The network interface on '{service}' suffered rapid TCP socket resets and dropped client connections.",
        "implies": "What this implies: Downstream applications and microservices are suddenly disconnected, causing request dropouts and requiring immediate reconnect handshakes."
    },
    "session_expiration_storm": {
        "title": "Client Session Expiration & Purge",
        "brief": "Session heartbeats timed out on '{service}', triggering mass revocation of active client sessions.",
        "implies": "What this implies: Applications have lost their session authentication and ephemeral locks, forcing them to re-authenticate and re-acquire cluster locks."
    },
    "replication_sync_failure": {
        "title": "Quorum Follower Replication Interruption",
        "brief": "Replication worker on '{service}' lost sync with peer nodes and closed the synchronization channel.",
        "implies": "What this implies: Standby nodes have fallen behind on cluster state, risking outdated read responses if queries hit replica nodes."
    },
    "channel_connection_refused": {
        "title": "Quorum Peer Channel Refusal",
        "brief": "Inter-node communication listener on '{service}' was unable to open TCP channels to peer cluster addresses.",
        "implies": "What this implies: Node-to-node consensus traffic is blocked, isolating this server from the active cluster quorum."
    },
    "server_runtime_halt": {
        "title": "Unexpected Server Runtime Exception",
        "brief": "Internal server worker on '{service}' encountered an unhandled exception and entered a degraded recovery state.",
        "implies": "What this implies: Primary server operations are halted or rejecting traffic, requiring process restart or failover."
    },
    "disk_snapshot_stall": {
        "title": "Disk Snapshot / Storage I/O Delay",
        "brief": "Storage persistence on '{service}' experienced high disk write latency while saving state snapshots.",
        "implies": "What this implies: In-memory buffers are backing up waiting for disk flushing, which increases memory consumption and slows down the server."
    },
    "datadir_purge_failure": {
        "title": "Automatic Data Purge / Cleanup Stall",
        "brief": "Background log purger on '{service}' halted or failed to clean historical transaction files.",
        "implies": "What this implies: Old transaction logs will accumulate on the file system, eventually causing disk space exhaustion if not cleaned."
    },
    "network_buffer_overflow": {
        "title": "Network Socket Buffer Contention",
        "brief": "Send and receive worker queues on '{service}' experienced queue backpressure under heavy network packet load.",
        "implies": "What this implies: Inter-node message delivery is delayed, introducing communication lag across dependent microservices."
    },
    "environment_misconfiguration": {
        "title": "Environment & Classpath Misconfiguration",
        "brief": "Service '{service}' detected conflicting system paths or invalid configuration flags during execution.",
        "implies": "What this implies: Essential dependencies and libraries cannot be loaded, preventing the service from operating normally."
    },
    "hadoop_block_replication_delay": {
        "title": "HDFS Block Replication Delay",
        "brief": "DataNode '{service}' experienced transmission stalls while replicating distributed storage blocks.",
        "implies": "What this implies: Distributed file blocks have fallen below the required replication factor, risking temporary read latency."
    },
    "hadoop_task_tracker_failure": {
        "title": "TaskTracker Node Heartbeat Loss",
        "brief": "Compute worker '{service}' failed to report heartbeats to the cluster coordinator within the deadline.",
        "implies": "What this implies: In-progress MapReduce batch tasks on this node are considered lost and must be rescheduled on other hosts."
    },
    "bgl_kernel_memory_error": {
        "title": "Supercomputer Node Kernel Memory Fault",
        "brief": "Compute node '{service}' experienced hardware-corrected memory parity alerts in the OS kernel.",
        "implies": "What this implies: The compute node must be isolated from batch calculation queues to prevent calculation errors."
    },
    "openstack_nova_hypervisor_drop": {
        "title": "Hypervisor Compute Provisioning Disruption",
        "brief": "Nova compute agent on '{service}' lost RPC communication with the central message broker.",
        "implies": "What this implies: New virtual machine instances cannot be scheduled, booted, or resized on this hypervisor host."
    },
    "database_slowdown": {
        "title": "Database Lock Contention & Bottleneck",
        "brief": "Query engine on '{service}' is experiencing table lock contention and thread pool saturation.",
        "implies": "What this implies: Client transactions are queueing up, causing application latency to spike and triggering timeout errors."
    },
    "memory_leak_oom": {
        "title": "Process Memory Leak & Out of Memory",
        "brief": "Application memory usage on '{service}' approached physical limits, triggering high garbage collection pauses.",
        "implies": "What this implies: Server response times spike and the operating system may terminate the process abruptly."
    }
}

class LLMSummarizer:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.2:latest"):
        self.ollama_url = ollama_url
        self.model = model

    def infer_root_cause_type(self, incident: Incident) -> str:
        text_corpus = " ".join([a.name + " " + a.message for a in incident.alerts]).lower()
        origin_svc = incident.origin.service.lower()

        # Zookeeper / Distributed consensus
        if any(k in origin_svc for k in ["fastleaderelection", "leaderelection"]) or any(k in text_corpus for k in ["election", "notification time out", "e31", "e34", "e35"]):
            return "leader_election_timeout"
        if "nioservercnxn" in origin_svc or any(k in text_corpus for k in ["closed socket", "socket connection", "caught end of stream", "e6", "e10"]):
            return "socket_connection_drop"
        if "preprequestprocessor" in origin_svc or any(k in text_corpus for k in ["session termination", "sessionid", "e38", "e21"]):
            return "session_expiration_storm"
        if "learnerhandler" in origin_svc or any(k in text_corpus for k in ["goodbye", "learner", "e1", "e49"]):
            return "replication_sync_failure"
        if "listener" in origin_svc or any(k in text_corpus for k in ["cannot open channel", "e5", "e40"]):
            return "channel_connection_refused"
        if "zookeeperserver" in origin_svc or any(k in text_corpus for k in ["unexpected exception", "renew session", "e7", "e8", "e12", "e15"]):
            return "server_runtime_halt"
        if "snap" in origin_svc or any(k in text_corpus for k in ["snapshot", "reading snapshot"]):
            return "disk_snapshot_stall"
        if "cleanup" in origin_svc or "purge" in text_corpus:
            return "datadir_purge_failure"
        if any(k in origin_svc for k in ["sendworker", "recvworker"]) or any(k in text_corpus for k in ["waiting for message on queue", "connection broken for id", "e24", "e25"]):
            return "network_buffer_overflow"
        if "environment" in origin_svc or "classpath" in text_corpus:
            return "environment_misconfiguration"

        # Hadoop
        if any(k in origin_svc for k in ["datanode", "leaserenewer", "dfsclient", "commit"]):
            return "hadoop_block_replication_delay"
        if any(k in origin_svc for k in ["tasktracker", "taskattempt", "yarnuncaught"]):
            return "hadoop_task_tracker_failure"

        # BGL
        if any(k in origin_svc for k in ["kernel", "hardware", "discovery", "mmcs"]):
            return "bgl_kernel_memory_error"

        # OpenStack
        if any(k in origin_svc for k in ["nova", "libvirt", "imagecache", "wsgi"]):
            return "openstack_nova_hypervisor_drop"

        # Generic Web / DB / Memory
        if "wal" in text_corpus or "disk" in text_corpus or "enospc" in text_corpus:
            return "disk_snapshot_stall"
        if "oom" in text_corpus or "heap" in text_corpus or "leak" in text_corpus:
            return "memory_leak_oom"
        if "lock" in text_corpus or "timeout" in text_corpus or "db" in origin_svc:
            return "database_slowdown"

        return "server_runtime_halt"

    def generate_explanation(self, incident: Incident, use_llm: bool = False) -> Dict[str, str]:
        archetype_key = self.infer_root_cause_type(incident)
        archetype = SERVER_ROOT_CAUSES_CATALOGUE.get(archetype_key, SERVER_ROOT_CAUSES_CATALOGUE["server_runtime_halt"])

        brief_text = archetype["brief"].format(service=incident.origin.service)
        implication_text = archetype["implies"]

        # Attempt fast refinement with local Ollama 2B only when requested (e.g. for top incident or detail explain)
        if use_llm and config.enable_llm_explanations and incident.alerts:
            try:
                sample_log = incident.alerts[0].message[:100]
                prompt = (
                    f"Explain this server failure in simple English in two sentences.\n"
                    f"Component: {incident.origin.service}\n"
                    f"Failure: {archetype['title']}\n"
                    f"Log: {sample_log}\n\n"
                    f"Reply strictly in this format:\n"
                    f"Brief: <one sentence describing what happened>\n"
                    f"Implies: <one sentence explaining what this implies for the system>"
                )
                payload = json.dumps({
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 70}
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    ai_text = res_data.get("response", "").strip()
                    if "Brief:" in ai_text and "Implies:" in ai_text:
                        parts = ai_text.split("Implies:")
                        b = parts[0].replace("Brief:", "").strip()
                        i = parts[1].strip()
                        if len(b) > 10:
                            brief_text = b
                        if len(i) > 10:
                            implication_text = f"What this implies: {i}"
            except Exception:
                pass  # Use calibrated expert sentences on timeout or error

        title = f"{archetype['title']} on '{incident.origin.service}'"
        return {
            "root_cause_type": archetype_key,
            "root_cause_title": archetype["title"],
            "title": title,
            "brief_description": brief_text,
            "what_it_implies": implication_text,
            "water_pipe_analogy": f"{brief_text} {implication_text}",
            "diagnostic_summary": f"{brief_text} {implication_text}"
        }

llm_summarizer = LLMSummarizer()
