# System Failure Modes, Bias Analysis & Mitigations (FAILURE_MODES.md)

As required by problem statement AO-01 and Section 8 of the project brief, this document identifies known operational failure modes, modeling biases, detection methods, and the automated safety mitigations implemented in the AO-01 system.

---

### 1. Bias Toward Past Patterns (Novel Failure Types Mistaken for Noise)
- **Risk:** If the system aggressively suppresses alerts that have never been seen during past incidents, an entirely novel failure mode (e.g. split-brain in a new cache cluster) could be silenced.
- **Detection Method:** Novelty detection check in `RecallGuard`: any `rule_key` absent from the historical baseline registry is flagged `is_novel=True`.
- **Implemented Mitigation:**
  - The **Novelty Rule** mandates that any alert with an unseen `rule_key` is immediately surfaced and **cannot be suppressed**.
  - Rare alerts ($n_{fires} < 30$) are placed in `Keep - insufficient evidence` and never recommended for suppression.

---

### 2. Stale or Incomplete Service Dependency Map
- **Risk:** Microservice topologies evolve rapidly. If a newly deployed service $A$ calls $B$ but the edge is missing from the dependency graph, graph distance $d(A, B)$ defaults to unreachable ($d=999$), preventing correlation.
- **Detection Method:** Dynamic topology discrepancy monitoring: detects clusters of temporally correlated alerts whose graph distance exceeds $H$ hops.
- **Implemented Mitigation:**
  - The pairwise affinity score balances topology ($w_g$) with temporal decay ($w_t$) and text similarity ($w_s$).
  - An audit warning is issued when alerts with high temporal affinity are disconnected in the graph, prompting the operator to review the dependency map.

---

### 3. Over-Merging of Concurrent Unrelated Incidents (Chaining)
- **Risk:** Two unrelated outages occurring at the same time (e.g., a payment gateway outage and an Elasticsearch connection exhaustion) could be mistakenly chained together if an intermediate service (such as `checkout-orchestrator`) alerts for both.
- **Detection Method:** Graph diameter and duration monitoring across open incident cards.
- **Implemented Mitigation:**
  - **Anti-Chaining Guard:** Rejects joining an incident if the temporal span exceeds $W_{max}$ (default 60 minutes) or if the graph diameter of the combined alerting services exceeds `max_diameter` (4 hops).
  - When anti-chaining triggers, a new incident card is opened, keeping concurrent incidents isolated.

---

### 4. Under-Merging Due to Discrepant Service Naming Across Tools
- **Risk:** Prometheus may label a service `order_service`, Datadog may report `order-service`, and Sentry may report `orders-api`.
- **Detection Method:** Canonical entity resolver check in `schema_detect.py`.
- **Implemented Mitigation:**
  - Canonical normalization strips punctuation, replaces underscores with hyphens, and maintains an alias map.
  - Multi-source correlation rules match on normalized `service_alias`.

---

### 5. Timestamp Skew and Clock Drift Across Monitoring Tools
- **Risk:** Agents on different virtual machines or third-party webhooks may deliver timestamps skewed by tens of seconds or minutes.
- **Detection Method:** Ingestion timestamp discrepancy tracking: comparing alert `timestamp` with payload ingestion time.
- **Implemented Mitigation:**
  - Configurable exponential time decay ($\tau = 5$ minutes) and sliding window ($W = 15$ minutes) tolerate clock drifts of up to several minutes without breaking correlation.

---

### 6. Small-Sample Suppression Risk
- **Risk:** A rule that fired only twice might appear to have a $0\%$ incident link rate, leading a naive model to suggest suppression.
- **Detection Method:** Bayesian / Wilson score interval lower bound.
- **Implemented Mitigation:**
  - Hard minimum volume constraint: rules must have $\ge 30$ historical firings before being categorized as a `Suppress candidate`.
  - Rare rules are explicitly labeled `Keep - insufficient evidence`.

---

### 7. Redaction Gaps (Adversarial or Nested Strings)
- **Risk:** An alert message containing nested URLs with IP addresses (`https://10.0.1.25:8080/checkout`) or port suffixes could leak private infrastructure details.
- **Detection Method:** Adversarial test suite (`test_redactor_and_schema.py`) validating regex coverage against IPs with ports, internal FQDNs, and customer IDs.
- **Implemented Mitigation:**
  - Pre-serialization regex redaction captures host/IP and isolates port numbers, replacing them with stable SHA-256 derived pseudonyms (`ip-xxxx:8080`, `host-xxxx:5432`).
  - Redaction is strictly **default ON** across all API responses.

---

### 8. Origin Prior Bias
- **Risk:** Over-weighting historical priors could cause the ranker to perpetually blame the primary database, ignoring a real upstream root cause.
- **Detection Method:** Comparing upstream blast radius vs prior weight influence.
- **Implemented Mitigation:**
  - Downstream reachability (blast radius) is given the highest weight ($w_{upstream} = 0.50$), temporal earliness is given $w_{earliness} = 0.30$, and historical prior is limited to a small tie-breaker ($w_{prior} = 0.20$).
