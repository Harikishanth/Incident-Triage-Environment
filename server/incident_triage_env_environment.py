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
"""

import random
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import IncidentTriageAction, IncidentTriageObservation
except ImportError:
    from models import IncidentTriageAction, IncidentTriageObservation


# ── Easy Scenarios ───────────────────────────────────────────────────────────

EASY_SCENARIOS = [
    {
        "id": "easy_db",
        "incident_report": """
🚨 INCIDENT REPORT — 02:47 UTC
Severity: P2 | Duration: 12 minutes and ongoing

Error logs:
  [ERROR] DatabaseConnectionPool: Connection timeout after 30s
  [ERROR] DatabaseConnectionPool: Pool exhausted (max_connections=100, active=100)
  [WARN]  PaymentService: Upstream dependency unavailable
  [ERROR] PaymentService: 503 returned to 847 requests in last 5 minutes
  [INFO]  AuthService: Operating normally
  [INFO]  UserService: Operating normally

User reports: "Cannot checkout", "Payment keeps failing", "Getting 503 errors"

Question: Which service is failing and what is the root cause?
""",
        "keywords": ["database", "db", "connection", "pool", "payment"],
        "required_count": 2,
    },
    {
        "id": "easy_memory",
        "incident_report": """
🚨 INCIDENT REPORT — 09:15 UTC
Severity: P2 | Duration: 7 minutes and ongoing

Error logs:
  [ERROR] UserService: OutOfMemoryError — heap space exhausted
  [ERROR] UserService: JVM crashed, restarting (attempt 3/5)
  [WARN]  APIGateway: UserService returning 502 Bad Gateway
  [ERROR] APIGateway: 1,200 requests failed in last 3 minutes
  [INFO]  OrderService: Operating normally
  [INFO]  PaymentService: Operating normally

User reports: "Can't log in", "Profile page not loading", "App keeps crashing"

Question: Which service is failing and what is the root cause?
""",
        "keywords": ["userservice", "user service", "memory", "heap", "oom", "outofmemory", "jvm"],
        "required_count": 2,
    },
    {
        "id": "easy_disk",
        "incident_report": """
🚨 INCIDENT REPORT — 16:32 UTC
Severity: P2 | Duration: 5 minutes and ongoing

Error logs:
  [ERROR] LoggingService: Disk write failed — no space left on device
  [ERROR] LoggingService: Unable to write logs, dropping messages
  [WARN]  OrderService: Cannot write audit logs, transactions blocked
  [ERROR] OrderService: 423 orders failed in last 5 minutes
  [INFO]  AuthService: Operating normally
  [INFO]  UserService: Operating normally

User reports: "Order not going through", "Getting error on checkout", "Transaction failed"

Question: Which service is failing and what is the root cause?
""",
        "keywords": ["disk", "storage", "space", "logging", "log service", "loggingservice"],
        "required_count": 2,
    },
]


# ── Medium Scenarios ─────────────────────────────────────────────────────────

MEDIUM_SCENARIOS = [
    {
        "id": "medium_gpu",
        "incident_report": """
🚨 INCIDENT REPORT — 14:23 UTC
Severity: P1 | Duration: 8 minutes and ongoing

Signal A — Application logs:
  [ERROR] RecommendationService: Response time 8400ms (threshold: 500ms)
  [ERROR] RecommendationService: Timeout calling ML model endpoint
  [WARN]  RecommendationService: Falling back to cached recommendations

Signal B — Infrastructure logs:
  [WARN]  MLModelServer: GPU memory utilization 97%
  [ERROR] MLModelServer: OOM killed worker process (3 times in 10 min)
  [INFO]  MLModelServer: Auto-restarting workers

Signal C — Network logs (RED HERRING):
  [WARN]  LoadBalancer: Elevated latency on eu-west-2 (120ms vs 40ms baseline)
  [INFO]  LoadBalancer: All health checks passing
  [INFO]  NetworkMonitor: No packet loss detected

Question: What is the ROOT CAUSE? Which signal is the root cause and which are symptoms/red herrings?
""",
        "root_cause_keywords": ["gpu", "memory", "oom", "ml model", "mlmodel", "out of memory", "infrastructure"],
        "red_herring_keywords": ["network", "loadbalancer", "load balancer", "latency", "not the cause", "red herring", "signal c"],
        "symptom_keywords": ["recommendationservice", "recommendation", "timeout", "signal a"],
    },
    {
        "id": "medium_cache",
        "incident_report": """
🚨 INCIDENT REPORT — 11:05 UTC
Severity: P1 | Duration: 15 minutes and ongoing

Signal A — Infrastructure logs (RED HERRING):
  [WARN]  CDNProvider: Cache hit ratio dropped from 94% to 71%
  [INFO]  CDNProvider: No errors reported, serving traffic normally
  [INFO]  CDNProvider: All edge nodes healthy

Signal B — Application logs:
  [ERROR] ProductCatalogService: Response time 12000ms (threshold: 200ms)
  [ERROR] ProductCatalogService: Redis connection refused
  [ERROR] ProductCatalogService: Falling back to database queries

Signal C — Infrastructure logs:
  [ERROR] RedisCluster: Primary node unreachable
  [ERROR] RedisCluster: Failover initiated, replica promotion failed
  [ERROR] RedisCluster: Cluster in degraded state

Question: What is the ROOT CAUSE? Which signal is the root cause and which are symptoms/red herrings?
""",
        "root_cause_keywords": ["redis", "cache", "cluster", "signal c", "primary node", "failover"],
        "red_herring_keywords": ["cdn", "signal a", "cache hit", "edge", "not the cause", "red herring"],
        "symptom_keywords": ["productcatalog", "product catalog", "signal b", "response time"],
    },
    {
        "id": "medium_cert",
        "incident_report": """
🚨 INCIDENT REPORT — 00:01 UTC
Severity: P1 | Duration: 3 minutes and ongoing

Signal A — Application logs:
  [ERROR] APIGateway: SSL handshake failed for all HTTPS requests
  [ERROR] APIGateway: Certificate validation error
  [ERROR] APIGateway: 100% of requests failing

Signal B — Infrastructure logs (RED HERRING):
  [WARN]  AutoScaler: Adding 3 new instances due to error rate spike
  [INFO]  AutoScaler: New instances healthy and serving traffic
  [INFO]  LoadBalancer: Traffic distributed across 7 instances

Signal C — Security logs:
  [ERROR] CertificateManager: TLS certificate expired at 00:00:00 UTC
  [ERROR] CertificateManager: Auto-renewal failed — DNS validation error
  [WARN]  CertificateManager: Certificate was due for renewal 7 days ago

Question: What is the ROOT CAUSE? Which signal is the root cause and which are symptoms/red herrings?
""",
        "root_cause_keywords": ["certificate", "cert", "tls", "ssl", "expired", "signal c", "certificatemanager"],
        "red_herring_keywords": ["autoscaler", "scaling", "signal b", "instances", "not the cause", "red herring"],
        "symptom_keywords": ["apigateway", "api gateway", "signal a", "handshake", "https"],
    },
]


# ── Hard Scenarios ───────────────────────────────────────────────────────────

HARD_SCENARIOS = [
    {
        "id": "hard_auth",
        "incident_report": """
🚨 INCIDENT REPORT — 03:15 UTC
Severity: P0 — Full outage | Duration: 23 minutes and escalating

Service map: APIGateway → AuthService → UserDB
             APIGateway → OrderService → InventoryService → InventoryDB
             APIGateway → OrderService → PaymentService → PaymentDB
             APIGateway → NotificationService → EmailQueue

Logs:
  [ERROR] APIGateway: 89% requests returning 502
  [ERROR] AuthService: JWT validation failing — secret key mismatch
  [ERROR] AuthService: CONFIG_VERSION=v2 but tokens signed with v1 key
  [WARN]  OrderService: Cannot validate user sessions
  [ERROR] OrderService: All orders failing auth check
  [ERROR] InventoryService: Deadlock on inventory_items table (self-resolved)
  [ERROR] PaymentService: Hanging — waiting for OrderService
  [WARN]  NotificationService: EmailQueue backed up (4,200 messages)

Recent deploys:
  03:01 UTC — AuthService v2.1.0 (JWT_SECRET rotated)
  02:45 UTC — InventoryService v1.8.2 (index optimization)

Question: Write a PRIORITIZED action plan — FIRST, SECOND, THIRD steps to restore service and WHY.
""",
        "first_keywords": ["auth", "jwt", "secret", "rollback", "revert", "config", "authservice"],
        "second_keywords": ["order", "inventory", "restart", "orderservice", "inventoryservice", "deadlock"],
        "third_keywords": ["notification", "email", "queue", "payment", "paymentservice", "emailqueue"],
    },
    {
        "id": "hard_cascade",
        "incident_report": """
🚨 INCIDENT REPORT — 18:44 UTC
Severity: P0 — Full outage | Duration: 31 minutes and escalating

Service map: WebApp → APIGateway → UserService → UserDB
             WebApp → APIGateway → SearchService → ElasticSearch
             WebApp → APIGateway → CartService → RedisCache → FallbackDB

Logs:
  [ERROR] WebApp: 94% of page loads failing
  [ERROR] ElasticSearch: Cluster split-brain — 2 nodes lost quorum
  [ERROR] SearchService: All search queries failing (depends on ElasticSearch)
  [ERROR] CartService: Redis eviction storm — 80% cache miss rate
  [ERROR] CartService: FallbackDB connection pool exhausted (querying DB on every request)
  [ERROR] FallbackDB: CPU at 100%, query queue depth 4,200
  [ERROR] UserDB: Replication lag 47 seconds (replica overloaded)
  [WARN]  UserService: Read queries routing to lagged replica

Recent deploys:
  18:30 UTC — SearchService v3.1 (new ElasticSearch query patterns)
  18:15 UTC — CartService v2.8 (Redis TTL reduced from 1hr to 5min)

Question: Write a PRIORITIZED action plan — FIRST, SECOND, THIRD steps to restore service and WHY.
""",
        "first_keywords": ["elasticsearch", "elastic", "search", "split-brain", "quorum", "searchservice"],
        "second_keywords": ["redis", "cache", "cart", "cartservice", "ttl", "eviction"],
        "third_keywords": ["database", "db", "fallbackdb", "userdb", "replication", "cpu"],
    },
    {
        "id": "hard_deploy",
        "incident_report": """
🚨 INCIDENT REPORT — 22:05 UTC
Severity: P0 — Partial outage | Duration: 18 minutes and escalating

Service map: MobileApp → APIGateway → ProfileService → ProfileDB
             MobileApp → APIGateway → FeedService → ProfileService
             MobileApp → APIGateway → MessagingService → MessageQueue

Logs:
  [ERROR] ProfileService: Schema migration failed midway — table in inconsistent state
  [ERROR] ProfileService: 60% of requests failing (new columns missing)
  [ERROR] FeedService: Cannot fetch profile data — ProfileService errors
  [ERROR] FeedService: Feed generation failing for all users
  [WARN]  MessagingService: Degraded — message delivery delayed 8 minutes
  [INFO]  APIGateway: Routing normally
  [INFO]  ProfileDB: Healthy, accepting connections

Recent deploys:
  22:00 UTC — ProfileService v4.0.0 (major schema migration — added 12 new columns)
  21:50 UTC — MessagingService v2.3.1 (minor bug fix)

Question: Write a PRIORITIZED action plan — FIRST, SECOND, THIRD steps to restore service and WHY.
""",
        "first_keywords": ["profile", "profileservice", "rollback", "revert", "schema", "migration"],
        "second_keywords": ["feed", "feedservice", "restart", "redeploy", "cache", "clear"],
        "third_keywords": ["messaging", "messagingservice", "queue", "messagequeue", "delay", "backlog"],
    },
]


# ── Graders ──────────────────────────────────────────────────────────────────

def grade_easy(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0
    keywords = scenario["keywords"]
    required = scenario["required_count"]

    hits = sum(1 for kw in keywords if kw in r)

    if hits >= required:
        score = 0.5 + min(0.5, (hits - required) * 0.1 + 0.3)
    elif hits == 1:
        score = 0.3

    # Bonus for mentioning root cause clearly
    root_cause_terms = ["root cause", "cause is", "failing because", "due to", "caused by", "reason is"]
    if any(term in r for term in root_cause_terms):
        score = min(1.0, score + 0.1)

    return round(min(score, 1.0), 2)


def grade_medium(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0

    # Root cause identification (50%)
    root_hits = sum(1 for kw in scenario["root_cause_keywords"] if kw in r)
    if root_hits >= 2:
        score += 0.5
    elif root_hits == 1:
        score += 0.25

    # Red herring dismissal (30%)
    red_hits = sum(1 for kw in scenario["red_herring_keywords"] if kw in r)
    if red_hits >= 1:
        score += 0.3

    # Symptom identification (20%)
    symptom_hits = sum(1 for kw in scenario["symptom_keywords"] if kw in r)
    if symptom_hits >= 1:
        score += 0.2

    return round(min(score, 1.0), 2)


def grade_hard(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0
    lines = [l for l in r.split("\n") if l.strip()]

    if not lines:
        return 0.0

    # Split into thirds
    third = max(1, len(lines) // 3)
    first_part = " ".join(lines[:third])
    mid_part = " ".join(lines[third:2*third])
    last_part = " ".join(lines[2*third:])

    # Also check full response for each — partial credit
    # First action (50%) — most important
    first_in_position = any(kw in first_part for kw in scenario["first_keywords"])
    first_anywhere = any(kw in r for kw in scenario["first_keywords"])

    if first_in_position:
        score += 0.5
    elif first_anywhere:
        score += 0.25  # mentioned but not first

    # Second action (30%)
    second_in_position = any(kw in mid_part for kw in scenario["second_keywords"])
    second_anywhere = any(kw in r for kw in scenario["second_keywords"])

    if second_in_position:
        score += 0.3
    elif second_anywhere:
        score += 0.15

    # Third action (20%)
    third_in_position = any(kw in last_part for kw in scenario["third_keywords"])
    third_anywhere = any(kw in r for kw in scenario["third_keywords"])

    if third_in_position:
        score += 0.2
    elif third_anywhere:
        score += 0.1

    # Bonus for explicit prioritization language
    priority_terms = ["first", "second", "third", "priority", "immediately", "then", "finally", "step 1", "step 2", "step 3"]
    priority_hits = sum(1 for term in priority_terms if term in r)
    if priority_hits >= 3:
        score = min(1.0, score + 0.1)

    return round(min(score, 1.0), 2)


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
        self._current_task_index = 0
        self._current_scenario = None
        self._total_reward = 0.0
        self._pick_scenarios()

    def _pick_scenarios(self):
        """Pick random scenarios for this episode."""
        self._scenarios = {
            "easy": random.choice(EASY_SCENARIOS),
            "medium": random.choice(MEDIUM_SCENARIOS),
            "hard": random.choice(HARD_SCENARIOS),
        }

    def reset(self) -> IncidentTriageObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_index = 0
        self._total_reward = 0.0
        self._pick_scenarios()

        task_id = TASK_ORDER[0]
        scenario = self._scenarios[task_id]

        return IncidentTriageObservation(
            incident_report=scenario["incident_report"],
            task_id=task_id,
            step_number=0,
            feedback="Welcome. Analyze the incident report and respond with your findings.",
            done=False,
            reward=0.0,
        )

    def step(self, action: IncidentTriageAction) -> IncidentTriageObservation:
        self._state.step_count += 1

        current_task_id = TASK_ORDER[self._current_task_index]
        scenario = self._scenarios[current_task_id]

        # Grade the response
        if current_task_id == "easy":
            reward = grade_easy(action.response, scenario)
        elif current_task_id == "medium":
            reward = grade_medium(action.response, scenario)
        else:
            reward = grade_hard(action.response, scenario)

        self._total_reward += reward
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