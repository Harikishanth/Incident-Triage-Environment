# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Pure-Python grader logic and scenario definitions.

This module has ZERO external dependencies (no openenv, no FastAPI, no httpx).
This makes it instantly importable for local testing and pytest suites
without triggering the openenv framework's network bootstrapping.

The IncidentTriageEnvironment in incident_triage_env_environment.py
delegates all grading logic to this module.
"""

from typing import List


# ── Easy Scenarios ───────────────────────────────────────────────────────────

EASY_SCENARIOS: List[dict] = [
    {
        "id": "easy_db",
        "incident_report": """
\U0001f6a8 INCIDENT REPORT — 02:47 UTC
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
\U0001f6a8 INCIDENT REPORT — 09:15 UTC
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
\U0001f6a8 INCIDENT REPORT — 16:32 UTC
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

MEDIUM_SCENARIOS: List[dict] = [
    {
        "id": "medium_gpu",
        "incident_report": """
\U0001f6a8 INCIDENT REPORT — 14:23 UTC
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
\U0001f6a8 INCIDENT REPORT — 11:05 UTC
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
\U0001f6a8 INCIDENT REPORT — 00:01 UTC
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

HARD_SCENARIOS: List[dict] = [
    {
        "id": "hard_auth",
        "incident_report": """
\U0001f6a8 INCIDENT REPORT — 03:15 UTC
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
\U0001f6a8 INCIDENT REPORT — 18:44 UTC
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
\U0001f6a8 INCIDENT REPORT — 22:05 UTC
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

def safe_reward(raw: float) -> float:
    """Clamp the reward strictly between 0.01 and 0.99 to pass OpenEnv validation constraints."""
    return round(min(max(float(raw), 0.01), 0.99), 2)

def grade_easy(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0
    keywords = scenario["keywords"]
    required = scenario["required_count"]

    hits = sum(1 for kw in keywords if kw in r and f"not {kw}" not in r and f"not a {kw}" not in r)

    if hits >= required:
        score = 0.5 + min(0.5, (hits - required) * 0.1 + 0.3)
    elif hits == 1:
        score = 0.3

    # Bonus for mentioning root cause clearly
    root_cause_terms = ["root cause", "cause is", "failing because", "due to", "caused by", "reason is"]
    if any(term in r for term in root_cause_terms):
        score = min(1.0, score + 0.1)

    # Validate and cap easy score to 0.95 max
    return safe_reward(min(score, 0.95))


def grade_medium(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0

    target_signal = ""
    if scenario["id"] == "medium_gpu": target_signal = "signal b"
    if scenario["id"] == "medium_cache": target_signal = "signal c"
    if scenario["id"] == "medium_cert": target_signal = "signal c"

    # Root cause identification (35%)
    # Requires 2+ keywords AND explicit causal explanation connecting them
    root_hits = sum(1 for kw in scenario["root_cause_keywords"] if kw in r)
    causal_terms = ["because", "due to", "since", "causes", "resulting", "as a result", "leads to", "indicates"]
    has_explanation = any(term in r for term in causal_terms)

    if root_hits >= 2 and has_explanation:
        score += 0.35
    elif root_hits >= 1 and has_explanation:
        score += 0.15
    elif root_hits >= 1:
        score += 0.05

    # Red herring explicit identification (30%) — REQUIRED for full score
    # Strict: must use explicit flag language + name the red herring signal/service
    # "not the cause" is deliberately excluded — too common in any structured response
    strict_dismissal_terms = [
        "red herring", "false alarm", "misleading", "symptom only",
        "coincidental", "irrelevant", "not related"
    ]
    dismissal_hits = sum(1 for kw in strict_dismissal_terms if kw in r)
    signal_ident_hits = sum(1 for kw in scenario["red_herring_keywords"] if kw in r)

    # Both conditions must be satisfied: explicit dismissal word AND naming the red herring signal
    red_herring_identified = dismissal_hits >= 1 and signal_ident_hits >= 1
    if red_herring_identified:
        score += 0.30

    # Symptom identification (15%)
    symptom_hits = sum(1 for kw in scenario["symptom_keywords"] if kw in r)
    if symptom_hits >= 1:
        score += 0.15

    # Correct signal letter explicitly named as root cause (10% bonus)
    if target_signal and (target_signal in r):
        score += 0.10

    # HARD CAP: If the agent doesn't explicitly identify the red herring with strict language,
    # cap at 0.45 regardless of other points
    if not red_herring_identified:
        score = min(score, 0.45)

    # Medium task ceiling: even a perfect response cannot exceed 0.80 by design
    # This ensures medium is meaningfully harder than easy
    # and differentiates model capability — only models that nail every category reach 0.80
    return safe_reward(min(score, 0.80))


def grade_hard(response: str, scenario: dict) -> float:
    r = response.lower()
    score = 0.0
    lines = [line for line in r.split("\n") if line.strip()]

    if not lines:
        return 0.0

    # Split into thirds
    third = max(1, len(lines) // 3)
    first_part = " ".join(lines[:third])
    mid_part = " ".join(lines[third:2 * third])
    last_part = " ".join(lines[2 * third:])

    wrong_service_penalty = 0.0
    # Add a penalty if the wrong service is considered the primary failure
    if scenario["id"] == "hard_auth":
        if "inventoryservice" in first_part or "paymentservice" in first_part:
            wrong_service_penalty = 0.2
    elif scenario["id"] == "hard_cascade":
        if "userdb" in first_part or "cartservice" in first_part:
            wrong_service_penalty = 0.2
    elif scenario["id"] == "hard_deploy":
        if "feedservice" in first_part or "messagingservice" in first_part:
            wrong_service_penalty = 0.2

    # First action (40%)
    first_in_position = any(kw in first_part for kw in scenario["first_keywords"])
    if first_in_position:
        score += 0.40

    # Second action (30%)
    second_in_position = any(kw in mid_part for kw in scenario["second_keywords"])
    if second_in_position:
        score += 0.30

    # Third action (20%)
    third_in_position = any(kw in last_part for kw in scenario["third_keywords"])
    if third_in_position:
        score += 0.20

    # Exclusivity penalty: if they dump all keywords in the first part, penalize heavily.
    # LLMs tend to summarize everything at the top. We want to dock points for this.
    exclusivity_penalty = 0.0
    if any(kw in first_part for kw in scenario["second_keywords"]):
        exclusivity_penalty += 0.15
    if any(kw in first_part for kw in scenario["third_keywords"]):
        exclusivity_penalty += 0.15

    # Bonus for explicit prioritization language (10%)
    priority_terms = ["first", "second", "third", "priority", "immediately", "then", "finally", "step 1", "step 2", "step 3"]
    priority_hits = sum(1 for term in priority_terms if term in r)
    if priority_hits >= 3:
        score += 0.10

    # Apply strict penalties
    score -= wrong_service_penalty
    score -= exclusivity_penalty

    # Cap if the most critical fix isn't mentioned correctly in the FIRST third
    if not first_in_position:
        score = min(score, 0.4)

    # Require at least 5 lines of structured response for any score above 0.5
    if len(lines) < 5:
        score = min(score, 0.3)

    # Cap hard explicitly at 0.75
    return safe_reward(min(score, 0.75))

