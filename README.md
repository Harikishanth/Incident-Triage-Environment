---
title: Incident Triage Env
emoji: "🚨"
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
license: mit
base_path: /web
tags:
  - openenv
  - sre
  - incident-triage
  - production
  - real-world
short_description: Deterministic evaluation of AI SRE capabilities
---

[![CI](https://github.com/Harikishanth/Incident-Triage-Environment/actions/workflows/ci.yml/badge.svg)](https://github.com/Harikishanth/Incident-Triage-Environment/actions/workflows/ci.yml)
[![Docker](https://github.com/Harikishanth/Incident-Triage-Environment/actions/workflows/docker.yml/badge.svg)](https://github.com/Harikishanth/Incident-Triage-Environment/actions/workflows/docker.yml)

> [!NOTE]
> This is a verified Phase 2 deep-validation submission for the **Meta × HuggingFace × Scaler OpenEnv Hackathon 2026**.

> [!TIP]
> A live deployed version of this environment is available at: **https://dardrax-incident-triage-env.hf.space**

# 🚨 SRE Incident Triage Environment

A zero-LLM deterministic OpenEnv reinforcement learning environment evaluating the root-cause analysis capabilities of AI agents against real-world production outages. 

```mermaid
xychart-beta
    title "Incident RCA Resolution Leaderboard (0-Shot)"
    x-axis ["Llama-3.3-70B", "Qwen-72B", "Gemma-2-27B", "Hermes-3-8B", "Mistral-Nemo"]
    y-axis "Heuristic Score" 0.00 --> 1.00
    bar [0.83, 0.83, 0.40, 0.28, 0.25]
```

Production incidents cost millions in downtime. This environment tests whether an LLM can simulate a Staff Site Reliability Engineer (SRE): reading raw failure logs, filtering out downstream system symptoms, identifying the root cause, and synthesizing a prioritized step-by-step remediation plan.

## Quick Start

The simplest way to interact with the environment via python:

```python
import asyncio
from client import IncidentTriageEnv
from models import IncidentTriageAction

async def main():
    try:
        # Connect to the live HuggingFace Space
        env = await IncidentTriageEnv(base_url="https://dardrax-incident-triage-env.hf.space")

        # Reset the environment with a specific scenario tier
        result = await env.reset(task_id="medium")
        obs = result.observation
        
        print("====== INCIDENT REPORT ======")
        print(obs.incident_report)

        # Step — submit the agent's analysis 
        action = IncidentTriageAction(
            response="The root cause is an expired mutual TLS certificate. "
                     "First, manually rotate the cert. Second, restart the ingress pods."
        )
        result = await env.step(action)
        
        print(f"\nScore: {result.reward:.2f}")
        print(f"Feedback: {result.observation.feedback}")

    finally:
        await env.close()

asyncio.run(main())
```

---

## 💡 Why This Problem?
Production outages cost organizations millions of dollars per hour. Resolving them involves:
- **Noise Filtering** — pinpointing the source failing service amidst thousands of downstream symptomatic alerts.
- **Deductive Reasoning** — separating the actual root cause from false red-herrings.
- **Strict Execution Order** — knowing that restarting a database *before* failing over to a replica causes catastrophic data loss.

No existing automated benchmark accurately evaluates LLM agents on SRE disaster recovery. **Incident Triage Env** fills this gap by testing agents dynamically across all dimensions simultaneously using zero-LLM deterministic bounds.

---

## 🚀 Try It Now (No Setup Required)
The environment exposes standard OpenEnv HTTP endpoints natively deployed on HuggingFace Spaces.

```bash
# Health check
curl -X GET https://dardrax-incident-triage-env.hf.space/health

# Pull dynamic multi-tier tasks
curl -X GET https://dardrax-incident-triage-env.hf.space/tasks

# Start a specific evaluation session
curl -X POST https://dardrax-incident-triage-env.hf.space/reset \
     -H "Content-Type: application/json" \
     -d '{"task_id": "medium"}'

# Submit an Agent Action
curl -X POST https://dardrax-incident-triage-env.hf.space/step \
     -H "Content-Type: application/json" \
     -d '{"action": {"response": "Rollback the payment service."}}'
```

---

## Agent Loop Architecture

```mermaid
flowchart TD
    classDef config fill:#1f2937,stroke:#6b7280,color:#f9fafb
    classDef env   fill:#7f1d1d,stroke:#b91c1c,color:#fef2f2
    classDef obs   fill:#1e3a5f,stroke:#3b82f6,color:#dbeafe
    classDef agent fill:#3b0764,stroke:#9333ea,color:#f3e8ff
    classDef step  fill:#78350f,stroke:#f59e0b,color:#fef3c7
    classDef score fill:#14532d,stroke:#4ade80,color:#bbf7d0

    CFG["⚙️ Task Config\ntask_id = easy | medium | hard"]:::config
    CFG -->|"env.reset()"| ENV["🚨 IncidentTriageEnv\nP0 / P1 / P2 Scenarios"]:::env
    ENV --> OBS["📡 Observation\n• Raw Error Logs\n• Datadog Metric Drops\n• Slack User Reports"]:::obs
    OBS -->|"incident_report"| AGT["🤖 Agent\nLLM (Qwen, Llama, etc.)"]:::agent
    AGT -->|"IncidentTriageAction"| STEP["⚡ Action → env.step()\nAgent submits RCA and Remediation Plan"]:::step
    STEP --> SCORE["🏁 Deterministic Grader\nFinal Score 0.00 – 1.00"]:::score
```

---

## Tasks & Scenarios

The environment evaluates agents across 3 distinct difficulty tiers, with scenarios rotating dynamically per episode reset to prevent hard-coding.

| Task ID | Difficulty | Active Challenge | Core Competency Evaluated |
|---------|------------|------------------|---------------------------|
| `easy` | 🟢 P2 Incident | Single-system failure | Identifying explicit failures from clear trace logs. |
| `medium` | 🟡 P1 Incident | Cascading failure | Distinguishing the origin root cause from misleading downstream red-herrings across 3 separate log domains. |
| `hard` | 🔴 P0 Outage | Catastrophic crash | Synthesizing a strict, order-dependent 3-step disaster recovery action plan. |

---

## Action & Observation Spaces

### Action: `IncidentTriageAction`

| Field | Type | Description |
|-------|------|-------------|
| `response` | `str` | Agent's free-text analysis of the incident report. |

### Observation: `IncidentTriageObservation`

| Field | Type | Description |
|-------|------|-------------|
| `incident_report` | `str` | Full incident diagnostic packet containing logs, metrics, and charts. |
| `task_id` | `str` | Current difficulty tier being evaluated. |
| `feedback` | `str` | Textual feedback from the deterministic evaluator regarding missing keywords or incorrect scoping. |
| `done` | `bool` | Episode completion flag. |
| `reward` | `float` | Normalized reward score (`0.00` – `1.00`). |

**Example Observation Payload:**
```json
{
  "incident_report": "🚨 INCIDENT REPORT — 14:23 UTC\n[FATAL] GatewayTimeout on path /api/checkout ...",
  "task_id": "medium",
  "feedback": "Task scored: 0.90. Root cause correctly identified. Moving to next incident.",
  "done": false,
  "reward": 0.9
}
```

---

## Reward Evaluation (Deterministic Heuristic Graders)

To ensuring absolute zero-LLM reproducibility, fairness, and speed across millions of inference runs, all grading is performed via hardened regex and deductive heuristics (see `server/graders.py`). 

Rewards are clipped strictly to `[0.01, 0.99]` to maintain OpenEnv strict boundary validation compliance. 

- **Easy Tier Strategy**: Validates against root cause extraction and implements **negation filtering** (e.g. failing responses containing `"not a connection pool issue"`). 
- **Medium Tier Strategy**: Fractional credit allocation: `50%` Root Cause Isolation, `30%` Red-Herring Dismissal, `20%` Symptom Tracking.
- **Hard Tier Strategy**: Fractional ordered credit allocation. Penalizes out-of-order action steps (e.g. diagnosing before rolling back).

---

## Baseline Inference Scores

Evaluation executed via `inference.py` using `Qwen/Qwen2.5-72B-Instruct` operating strictly at `TEMPERATURE=0.0`. 

| Tier | Task | Max Steps | Mean Score | Max |
|---|---|---|---|---|
| **Easy** | `easy` | 1 | 0.95 | 0.95 |
| **Medium** | `medium` | 1 | 0.50 | 0.80 |
| **Hard** | `hard` | 1 | 0.40 | 0.75 |
| **OVERALL** | — | — | **0.62** | **0.83** |

*Note: The inference baseline runs each task natively in isolated `[START]...[END]` loop blocks as required by the OpenEnv Phase 2 strict stdout protocols.*

```bash
# Run the automated inference loop on all tasks
uv run python inference.py

# Evaluate a specific tier
TASK_NAME=hard uv run python inference.py
```

---

## Deployment & Setup

### Local Run

```bash
git clone https://github.com/Harikishanth/Incident-Triage-Environment.git
cd Incident-Triage-Environment
uv sync
uvicorn server.app:app --reload --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t incident_triage_env:latest .
docker run -p 7860:7860 incident_triage_env:latest
```

### Hugging Face Space (OpenEnv Push)

```bash
openenv push --repo-id DarDrax/incident-triage-env
```
The deployed space automatically binds to HuggingFace's exposed infrastructure using port 7860 and natively provisions the OpenEnv Web UI, WebSocket (`/ws`), and automatic `/tasks` endpoints.

---

## 🔮 Future Roadmap

To evolve this environment into an enterprise-standard AI benchmark, the following architectural upgrades are mapped for Phase 3:

*   **Procedural Log Generation (Anti-Contamination)**: Migrating from static dictionaries to dynamic generators that fuzz timestamps, IP structures, and latency metrics on every execution to mathematically guarantee zero benchmark memorization.
*   **Interactive Tool-Use (POMDP Arch)**: Maturing from zero-shot ingestion to a multi-step Partially Observable Markov Decision Process where agents must actively invoke `read_logs()` and `query_metrics()` endpoints to hunt down errors.
*   **Fuzzy Semantic Determinism**: Integrating lightweight Levenshtein-distance metrics into the heuristic grading algorithm to accommodate LLM vocabulary variance while strictly avoiding the unreliability of LLM-as-a-judge patterns.
*   **Massive Outage Scaling**: Expanding the incident repertoire from 9 to 50+ hyper-specific cloud catastrophes (e.g., Cache Stampedes, BGP Routing Leaks, Orphaned Zombie Processes).
*   **Live SRE War-Room UI**: Developing a sleek Vue/React dashboard to visually plot the LLM agent's real-time reasoning traces against a live system architecture topology map.

---

## Citation

```bibtex
@software{incidenttriageenv2026,
  title   = {Incident Triage Environment: Evaluating Foundation Models on SRE Root Cause Analysis},
  author  = {Tech Tridents (DarDrax)},
  year    = {2026},
  url     = {https://huggingface.co/spaces/DarDrax/incident-triage-env},
  note    = {Deterministic text-based RL environment for production incident resolution}
}
```
