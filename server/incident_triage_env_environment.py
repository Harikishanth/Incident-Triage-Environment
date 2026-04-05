# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Incident Triage Environment Implementation.

An AI agent receives production incident reports and must correctly
identify the failing service, root cause, and recommended fix.
3 tasks: easy -> medium -> hard, with multiple rotating scenarios.

Scenarios and grader logic live in server/graders.py (zero external deps)
so they can be imported and tested without triggering the openenv framework.
"""

import random
import os
from uuid import uuid4
from typing import List, Optional
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Import pure-Python graders (zero framework deps — fast import for tests)
try:
    from .graders import (
        EASY_SCENARIOS, MEDIUM_SCENARIOS, HARD_SCENARIOS,
        grade_easy, grade_medium, grade_hard,
    )
except ImportError:
    from graders import (
        EASY_SCENARIOS, MEDIUM_SCENARIOS, HARD_SCENARIOS,
        grade_easy, grade_medium, grade_hard,
    )

try:
    from ..models import IncidentTriageAction, IncidentTriageObservation
except ImportError:
    from models import IncidentTriageAction, IncidentTriageObservation


# ── Environment ───────────────────────────────────────────────────────────────

TASK_ORDER = ["easy", "medium", "hard"]


class IncidentTriageEnvironment(Environment):
    """
    Incident Triage Environment.

    The agent receives production incident reports and must identify
    root causes and recommended actions. 3 tasks of increasing difficulty,
    each with multiple rotating scenarios.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._total_reward = 0.0
        self._pick_scenarios()
        
        target_task = os.getenv("TASK_NAME")
        if target_task in TASK_ORDER:
            self._current_task_index = TASK_ORDER.index(target_task)
            self._is_single_task = True
        else:
            self._current_task_index = 0
            self._is_single_task = False

    def _pick_scenarios(self):
        """Pick random scenarios for this episode."""
        self._scenarios = {
            "easy": random.choice(EASY_SCENARIOS),
            "medium": random.choice(MEDIUM_SCENARIOS),
            "hard": random.choice(HARD_SCENARIOS),
        }

    def reset(self) -> IncidentTriageObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._total_reward = 0.0
        self._pick_scenarios()

        # Support TASK_NAME purely from environment variables to comply with OpenEnv signatures
        target_task = os.getenv("TASK_NAME")
        
        if target_task in TASK_ORDER:
            self._current_task_index = TASK_ORDER.index(target_task)
            self._is_single_task = True
        else:
            self._current_task_index = 0
            self._is_single_task = False

        task_id = TASK_ORDER[self._current_task_index]
        scenario = self._scenarios[task_id]

        return IncidentTriageObservation(
            incident_report=scenario["incident_report"],
            task_id=task_id,
            step_number=0,
            feedback=f"Welcome. Analyze the {task_id} incident and respond with your findings.",
            done=False,
            reward=0.0,
        )

    def step(self, action: IncidentTriageAction) -> IncidentTriageObservation:
        self._state.step_count += 1

        current_task_id = TASK_ORDER[self._current_task_index]
        scenario = self._scenarios[current_task_id]

        # Grade the response (pure-Python logic in graders.py)
        if current_task_id == "easy":
            reward = grade_easy(action.response, scenario)
        elif current_task_id == "medium":
            reward = grade_medium(action.response, scenario)
        else:
            reward = grade_hard(action.response, scenario)

        self._total_reward += reward
        
        # Advance logic
        if self._is_single_task:
            done = True
        else:
            self._current_task_index += 1
            done = self._current_task_index >= len(TASK_ORDER)

        if not done:
            next_task_id = TASK_ORDER[self._current_task_index]
            next_scenario = self._scenarios[next_task_id]
            return IncidentTriageObservation(
                incident_report=next_scenario["incident_report"],
                task_id=next_task_id,
                step_number=self._state.step_count,
                feedback=f"Task scored: {reward:.2f}. Moving to next incident.",
                done=False,
                reward=reward,
            )
        else:
            return IncidentTriageObservation(
                incident_report="All incidents resolved.",
                task_id="complete",
                step_number=self._state.step_count,
                feedback=f"Final task scored: {reward:.2f}. All tasks complete. Total: {self._total_reward:.2f}/3.00",
                done=True,
                reward=reward,
            )

    @property
    def state(self) -> State:
        return self._state