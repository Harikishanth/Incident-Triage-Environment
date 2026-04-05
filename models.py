# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Incident Triage Environment.

An AI agent receives production incident reports and must identify
the root cause, affected service, and recommended actions.
"""

from typing import Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class IncidentTriageAction(Action):
    """What the AI agent sends back — its analysis of the incident."""

    response: str = Field(default="", description="Agent's analysis of the incident report")


class IncidentTriageObservation(Observation):
    """What the AI agent sees — the incident report and context."""

    incident_report: str = Field(
        default="", description="The incident report to analyze"
    )
    task_id: str = Field(
        default="", description="Current task identifier (easy/medium/hard)"
    )
    step_number: int = Field(
        default=0, description="Current step in the episode"
    )
    feedback: str = Field(
        default="", description="Feedback from previous step if any"
    )