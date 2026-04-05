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

# ── Environment variables ────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# Custom for Incident Triage Environment
ENV_URL = os.getenv("ENV_URL", "https://dardrax-incident-triage-env.hf.space")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

# ── Constants ────────────────────────────────────────────────────────────────
TASK_NAME_ENV = os.getenv("TASK_NAME")  # e.g., 'easy', 'medium', 'hard'
BENCHMARK = "incident_triage_env"
MAX_STEPS = 3           # 3 tasks: easy → medium → hard
MAX_TOTAL_REWARD = 3.0  # max 1.0 per task
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE = 0.0       # deterministic for evaluation
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


# ── Logging (strict hackathon format) ────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    # If TASK_NAME_ENV is set, the overall task reported is the specific level
    report_task = task if not TASK_NAME_ENV else f"{task}:{TASK_NAME_ENV}"
    print(f"[START] task={report_task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    clean_action = action.replace("\n", " ").replace("\r", " ")[:200]
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


# ── LLM call with Retry Logic ────────────────────────────────────────────────
def get_model_response(client: OpenAI, incident_report: str, task_id: str, feedback: str) -> str:
    user_prompt = textwrap.dedent(f"""
        Task difficulty: {task_id}
        Previous feedback: {feedback}

        INCIDENT REPORT:
        {incident_report}

        Analyze this incident report and provide your findings.
    """).strip()

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
                print(f"[DEBUG] Model request failed (attempt {attempt+1}): {exc}. Retrying in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"[DEBUG] Model request failed after {max_retries} attempts: {exc}", flush=True)

    return "Unable to analyze incident after retries."


# ── Environment HTTP calls ────────────────────────────────────────────────────
async def env_reset(http: httpx.AsyncClient) -> dict:
    r = await http.post(f"{ENV_URL}/reset", json={})
    r.raise_for_status()
    return r.json()


async def env_step(http: httpx.AsyncClient, response_text: str) -> dict:
    r = await http.post(f"{ENV_URL}/step", json={"action": {"response": response_text}})
    r.raise_for_status()
    return r.json()


# ── Main loop ─────────────────────────────────────────────────────────────────
async def main() -> None:
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    # The benchmark-level task name
    log_start(task="incident_triage", env=BENCHMARK, model=MODEL_NAME)

    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            # Reset — get first incident report
            result = await env_reset(http)
            obs = result["observation"]
            done = result.get("done", False)

            # Define iteration limit based on whether we are in single-task mode
            loop_limit = 1 if TASK_NAME_ENV else MAX_STEPS
            total_possible_reward = 1.0 if TASK_NAME_ENV else MAX_TOTAL_REWARD

            for step in range(1, loop_limit + 1):
                if done:
                    break

                # Ask LLM to analyze this incident
                response = get_model_response(
                    llm_client,
                    incident_report=obs["incident_report"],
                    task_id=obs["task_id"],
                    feedback=obs["feedback"],
                )

                # Submit to grader
                result = await env_step(http, response)
                obs = result["observation"]
                reward = result.get("reward") or 0.0
                done = result.get("done", False)

                rewards.append(reward)
                steps_taken = step

                log_step(step=step, action=response, reward=reward, done=done, error=None)

                if done:
                    break

        score = sum(rewards) / total_possible_reward if total_possible_reward > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Error during episode: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())