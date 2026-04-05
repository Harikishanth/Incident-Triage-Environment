import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.incident_triage_env_environment import (
    grade_easy,
    grade_medium,
    grade_hard,
    EASY_SCENARIOS,
    MEDIUM_SCENARIOS,
    HARD_SCENARIOS
)

def test_grade_easy():
    scenario = EASY_SCENARIOS[0] # db connection pool
    
    # 1. Full hit
    resp1 = "The database is failing due to connection pool exhaustion."
    score1 = grade_easy(resp1, scenario)
    assert score1 > 0.6
    
    # 2. Negation hit (should not score for keywords preceded by 'not')
    resp2 = "This is not a database issue, and not a pool issue."
    score2 = grade_easy(resp2, scenario)
    assert score2 == 0.0

def test_grade_medium():
    scenario = MEDIUM_SCENARIOS[0] # gpu / memory
    
    # 1. Correct root cause and dismissal of red herring
    resp = "The root cause is GPU out of memory. The network latency is a red herring."
    score = grade_medium(resp, scenario)
    assert score > 0.7
    
def test_grade_hard():
    scenario = HARD_SCENARIOS[0] # hard auth
    
    # 1. Perfect structure
    resp = "First, rollback the authservice config version.\nSecond, restart the inventoryservice to clear the deadlock.\nThird, flush the notification emailqueue."
    score = grade_hard(resp, scenario)
    assert score > 0.8
