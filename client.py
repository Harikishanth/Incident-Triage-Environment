# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Incident Triage Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import IncidentTriageAction, IncidentTriageObservation
except ImportError:
    from models import IncidentTriageAction, IncidentTriageObservation


class IncidentTriageEnv(
    EnvClient[IncidentTriageAction, IncidentTriageObservation, State]
):
    """
    Client for the Incident Triage Environment.

    Connects via WebSocket to the environment server.
    The agent receives production incident reports and must
    identify root causes and recommend fixes.

    Example:
        >>> with IncidentTriageEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.incident_report)
        ...     result = client.step(IncidentTriageAction(response="The database is failing."))
        ...     print(result.reward)
    """

    def _step_payload(self, action: IncidentTriageAction) -> Dict:
        """Convert action to JSON payload."""
        return {
            "response": action.response,
        }

    def _parse_result(self, payload: Dict) -> StepResult[IncidentTriageObservation]:
        """Parse server response into StepResult."""
        obs_data = payload.get("observation", {})
        observation = IncidentTriageObservation(
            incident_report=obs_data.get("incident_report", ""),
            task_id=obs_data.get("task_id", ""),
            step_number=obs_data.get("step_number", 0),
            feedback=obs_data.get("feedback", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )