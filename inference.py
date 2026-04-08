"""
Incident Triage Environment - Inference Script

MANDATORY environment variables:
    HF_TOKEN       Your Hugging Face API key
    API_BASE_URL   LLM API endpoint (default: HF router)
    MODEL_NAME     Model identifier (default: Qwen2.5-72B-Instruct)
    ENV_URL        Live environment URL (default: HF Space)

STDOUT FORMAT (required by hackathon, strictly):
    [START] task=<name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""

import asyncio
import os
import textwrap
from typing import List, Optional
import httpx
from openai import OpenAI
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import IncidentTriageEnv
from models import IncidentTriageAction

# ── Environment variables ────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "https://dardrax-incident-triage-env.hf.space")

# Removed strict required check for HF_TOKEN to allow validator initialization checks

# ── Constants ────────────────────────────────────────────────────────────────
BENCHMARK = "incident_triage_env"
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE = 0.0
MAX_TOKENS = 512

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert Site Reliability Engineer (SRE) with 10 years of
    experience triaging production incidents at large-scale systems.

    You will receive incident reports containing error logs, service signals,
    and user complaints. Your job is to:
    1. Identify which service is failing
    2. Identify the root cause (not just symptoms)
    3. Recommend prioritized actions to resolve the incident

    Be specific. Reference exact service names and log entries.
    Keep your response concise and structured.
""").strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    clean_action = action.replace("\n", " ").replace("\r", " ")
    print(
        f"[STEP] step={step} action={clean_action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )

def get_model_response(client: OpenAI, incident_report: str, task_id: str, feedback: str) -> str:
    user_prompt = textwrap.dedent(f"""
        Task difficulty: {task_id}
        Previous feedback: {feedback}

        INCIDENT REPORT:
        {incident_report}

        Analyze this incident report and provide your findings.
    """).strip()

    if not HF_TOKEN:
        return "Dummy response due to missing HF_TOKEN."

    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False,
            )
            text = (completion.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception as exc:
            if attempt < max_retries - 1:
                import time
                wait = (attempt + 1) * 2
                time.sleep(wait)
            else:
                pass
    return "Unable to analyze incident after retries."

def run_task(env_client, llm_client, task_id: str):
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)
    rewards = []
    success = False
    score = 0.0
    
    try:
        # Request environment override for this specific task
        result = env_client.reset(task_id=task_id)
        obs = result.observation
        
        response = get_model_response(
            llm_client,
            incident_report=obs.incident_report,
            task_id=obs.task_id,
            feedback=obs.feedback,
        )

        result = env_client.step(IncidentTriageAction(response=response))
        reward = result.reward

        rewards.append(reward)
        log_step(step=1, action=response, reward=reward, done=True, error=None)

        score = round(min(max(reward, 0.01), 0.99), 2)
        success = score >= SUCCESS_SCORE_THRESHOLD
        
    except Exception as e:
        score = 0.0
    finally:
        log_end(success=success, steps=1, score=score, rewards=rewards)


def main() -> None:
    # Optional task selection from environment
    target_task = os.getenv("TASK_NAME")
    tasks_to_run = [target_task] if target_task else ["easy", "medium", "hard"]
    
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy")

    with IncidentTriageEnv(base_url=ENV_URL).sync() as env:
        for t in tasks_to_run:
            run_task(env, llm_client, t)


if __name__ == "__main__":
    main()