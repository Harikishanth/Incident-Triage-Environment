---
title: Incident Triage Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - sre
  - incident-triage
  - real-world
---

# 🚨 Incident Triage Environment

> **Meta × HuggingFace × Scaler OpenEnv Hackathon 2026**

An OpenEnv reinforcement learning environment where an AI agent reads production incident reports and must correctly identify root causes, failing services, and prioritized remediation steps.

The agent progresses through **3 tasks of increasing difficulty** — easy → medium → hard — each scored 0.0–1.0 by a deterministic grader.

---

## Tasks

| Task | Difficulty | What the Agent Must Do | Max Score |
|------|------------|------------------------|-----------|
| **Easy** | 🟢 P2 Incident | Identify the failing service and root cause from clear error logs | 1.0 |
| **Medium** | 🟡 P1 Incident | Distinguish root cause from symptoms and red herrings across 3 signal sources | 1.0 |
| **Hard** | 🔴 P0 Outage | Write a prioritized 3-step action plan with correct ordering | 1.0 |

Each task has 3 rotating scenarios selected randomly per episode, ensuring the grader is deterministic but never returns the same score for random responses.

---

## Quick Start

```python
from incident_triage_env import IncidentTriageAction, IncidentTriageEnv

# Connect to the live HuggingFace Space
env = IncidentTriageEnv(base_url="https://dardrax-incident-triage-env.hf.space")

# Reset — receive the first incident report
obs = env.reset()
print(obs.incident_report)

# Step — submit your analysis
result = env.step(IncidentTriageAction(
    response="The root cause is the DatabaseConnectionPool exhausting connections. "
             "PaymentService is the failing service due to its upstream dependency."
))
print(f"Score: {result.reward}")        # e.g. 0.8
print(f"Feedback: {result.observation.feedback}")
print(f"Done: {result.observation.done}")
```

---

## Action & Observation Spaces

### Action: `IncidentTriageAction`

| Field | Type | Description |
|-------|------|-------------|
| `response` | `str` | Agent's free-text analysis of the incident report |

### Observation: `IncidentTriageObservation`

| Field | Type | Description |
|-------|------|-------------|
| `incident_report` | `str` | Full incident report with error logs and signals |
| `task_id` | `str` | Current difficulty: `easy`, `medium`, `hard`, or `complete` |
| `step_number` | `int` | Current step index in the episode (0-indexed) |
| `feedback` | `str` | Score feedback from previous step, or welcome message on reset |
| `done` | `bool` | `true` when all 3 tasks are complete |
| `reward` | `float` | Score for the previous action (0.0–1.0) |

### Episode Structure

```
reset() → easy incident
step(response) → grade easy, return medium incident
step(response) → grade medium, return hard incident  
step(response) → grade hard, done=true
```

One episode = exactly 3 steps. Each step is independent (no carry-over state).

## API

### `POST /reset`
Starts a new episode. Returns the first incident report.

**Request Environment Override:**
The server supports reading `TASK_NAME` (e.g. `easy`, `medium`, `hard`) from environment variables to bypass strict progression and initialize at a specific task level. This allows for rigorous automated evaluation by external judging scripts.

**Response:**
```json
{
  "incident_report": "🚨 INCIDENT REPORT — 02:47 UTC\n...",
  "task_id": "easy",
  "step_number": 0,
  "feedback": "Welcome. Analyze the incident report and respond with your findings.",
  "done": false,
  "reward": 0.0
}
```

### `POST /step`
Submits the agent's response and advances to the next task.

**Request:**
```json
{ "response": "The failing service is PaymentService. Root cause: database connection pool exhausted." }
```

**Response:**
```json
{
  "incident_report": "🚨 INCIDENT REPORT — 14:23 UTC\n...",
  "task_id": "medium",
  "step_number": 1,
  "feedback": "Task scored: 0.90. Moving to next incident.",
  "done": false,
  "reward": 0.9
}
```

### `GET /state`
Returns current episode state (episode ID, step count).

### `GET /schema`
Returns Pydantic schemas for `IncidentTriageAction` and `IncidentTriageObservation`.

---

## Scoring

### Easy Grader
- Checks for **keyword hits** (failing service + root cause terms)
- Checks for **negation language** (`not <keyword>`, `not a <keyword>`) to prevent keyword stuffing and gaming.
- ≥2 hits → 0.5–1.0 | 1 hit → 0.3 | 0 hits → 0.0
- +0.1 bonus for explicit root cause language ("root cause is", "caused by", etc.)

### Medium Grader
- **Root cause** (50%): Identify the correct signal source
- **Red herring OR Action Plan** (30%): Correctly dismiss the misleading signal, or provide a structured action plan that demonstrates you ignored the red herring.
- **Symptoms** (20%): Identify the downstream symptom

### Hard Grader
- **First action** (50%): Correct service/fix mentioned first in the response
- **Second action** (30%): Correct second step in middle of response
- **Third action** (20%): Correct third step at end of response
- +0.1 bonus for explicit prioritization language (≥3 of: "first", "step 1", "then", etc.)

---

## Baseline Scores

Running `inference.py` with `Qwen/Qwen2.5-72B-Instruct` against the live HuggingFace Space produces:

| Task | Score |
|------|-------|
| Easy | 0.95 |
| Medium | 0.50 |
| Hard | 0.50 |
| **Total (normalized)** | **0.65** |

Scores are reproducible across runs with `TEMPERATURE=0.0`. `inference.py` includes a **retry mechanism** to gracefully handle HuggingFace routing timeouts/errors when scoring natively.

```
[START] task=incident_triage env=incident_triage_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=The root cause is... reward=0.95 done=false error=null
[STEP] step=2 action=Based on the logs... reward=0.50 done=false error=null
[STEP] step=3 action=First, rollback AuthService... reward=0.50 done=true error=null
[END] success=true steps=3 score=0.65 rewards=0.95,0.50,0.50
```

## Running Locally

```bash
# Install dependencies
cd incident_triage_env
uv sync

# Start the server
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

### Build Docker Image

```bash
docker build -t incident_triage_env:latest -f server/Dockerfile .
docker run -p 8000:8000 incident_triage_env:latest
```

### Run Inference Script

```bash
python inference.py
```

The inference script runs the LLM (via HuggingFace router) through all 3 tasks and prints `[START]`, `[STEP]`, `[END]` logs with scores.
You can limit evaluation to a single task by exporting `TASK_NAME=hard` before running inference.

---

## Deploy to HuggingFace Spaces

```bash
openenv push
# or with explicit repo
openenv push --repo-id DarDrax/incident-triage-env
```

---

## Project Structure

```
incident_triage_env/
├── inference.py          ← LLM inference script (with auto-retry and TASK_NAME support)
├── Dockerfile            ← Root-level Docker build
├── openenv.yaml          ← OpenEnv manifest (contains tasks metadata definitions)
├── README.md             ← This file (also rendered on HF Space)
├── models.py             ← IncidentTriageAction, IncidentTriageObservation (Pydantic)
├── client.py             ← IncidentTriageEnv client
├── pyproject.toml        ← Project metadata and dependencies
└── server/
    ├── app.py            ← FastAPI app (max_concurrent_envs=25 configured)
    ├── graders.py        ← Isolated pure-python grading and scenario extraction 
    └── incident_triage_env_environment.py  ← OS-environment aware OpenEnv class
```

---

## Live Demo

🌐 **Space URL**: https://huggingface.co/spaces/DarDrax/incident-triage-env  
📊 **Web UI**: https://dardrax-incident-triage-env.hf.space/web  
📖 **API Docs**: https://dardrax-incident-triage-env.hf.space/docs
