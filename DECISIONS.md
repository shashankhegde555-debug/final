# Architecture & Design Decisions Log (DECISIONS.md)

This log documents all non-obvious choices, dataset assumptions, performance tradeoffs, and architectural shifts made during the development of AO-01.

---

## Decision 001: Architecture Option Selection & Decoupled Keep Adapter
- **Date:** 2026-10-29
- **Context:** Docker is not installed on the Windows runtime (`docker: command not found`). Timeboxed trial under Phase 0 confirms Keep cannot be booted via local Docker Compose within 60 minutes.
- **Decision:** As specified in Section 4 and Section 12 (Fallback Rules), we proceed with **Option C / Decoupled Option B**:
  - The core correlation, root-cause origin ranking, noise recommendation, recall guard, and 2B LLM explanation engine runs in a standalone high-performance FastAPI service.
  - A comprehensive `KeepClient` and `KeepSink` integration layer is implemented (`backend/app/integrations/keep_client.py`) with configurable API key, URL, and dry-run safety gates.
  - The evaluation harness re-implements the Keep Topology Processor (application-membership clustering) and Keep Rule-Only baselines for rigorous head-to-head benchmarking.
- **Safety Impact:** Zero risk of unintended live modifications; complete independence from local Docker daemon.

---

## Decision 002: Dependency Graph Directionality
- **Date:** 2026-10-29
- **Context:** In microservices architecture, directionality of dependency graphs dictates root-cause flow.
- **Decision:** In our `networkx.DiGraph`, a directed edge `(A, B)` represents **`A depends on B`** (i.e., service `A` sends calls downstream to service `B`).
  - Therefore, if database `B` degrades, request failures cascade back to upstream services (`A`).
  - Downstream blast radius is computed by walking the reverse edges: `s` explains any service that can reach `s` through dependency paths.
  - Distance metrics $d(A, B)$ used in the topology affinity score use undirected shortest path length, with an additional directed path bonus $\beta = 0.15$ when an active dependency relationship exists.

---

## Decision 003: Ground Truth Unlabeled Alerts as Noise Singletons
- **Date:** 2026-10-29
- **Context:** Pairwise evaluation requires ground-truth pairing for all alerts, but real-world operational datasets contain thousands of alerts that do not belong to any confirmed incident.
- **Decision:** Any alert without an assigned ground-truth `incident_id` is treated as a unique singleton class. A pair of two unlinked alerts $(u_1, u_2)$ is defined as **negative** (should not be clustered together). This penalizes algorithms that blindly merge unrelated noise into giant clusters.

---

## Decision 004: 2B Parameter Model Integration for Root-Cause Explanations
- **Date:** 2026-10-29
- **Context:** User requested integration of a 2B parameter model (`llama3.2` 2B/3B running locally via Ollama) to synthesize plain-English root-cause descriptions and "water pipe" analogies for the 18 catalogued server root causes.
- **Decision:**
  - In strict compliance with **Rule 4 (Deterministic Core)**, the 2B model is **never** used for grouping, clustering, thresholding, or noise suppression decisions.
  - The 2B model is queried strictly in the advisory/presentation layer for generating human-friendly root-cause summaries and water pipe analogies.
  - Every AI-generated summary is clearly labeled `[AI Summary (Advisory)]` in the UI and API response, with the underlying mathematical weights, timestamps, and graph distances preserved as the immutable source of truth.
  - If Ollama is offline, a deterministic template engine automatically produces the exact water-pipe analogies for the 18 archetypes without failure.

---

## Decision 005: Transition from Analogies to Concise Technical Root-Cause Brief Descriptions
- **Date:** 2026-10-29
- **Context:** User requested: "dont use the llama 2B to give 'water pipe analogy' instead make it just give a brief description".
- **Decision:**
  - Shifted the 2B model prompt from colloquial "water pipe analogies" to direct, concise technical root-cause engineering briefs.
  - The model directly explains:
    1. Exactly what hardware, query, or runtime resource malfunctioned on the origin service node.
    2. Why that specific failure cascaded to downstream microservices.
  - Retained deterministic fallback using the 18 server problem catalogue.
  - The UI feed and detail modal were updated to display "Root-Cause Brief Description: 2B Parameter Model Diagnosis" with zero analogies.
