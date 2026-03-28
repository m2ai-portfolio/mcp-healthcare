"""Tests for care pathway recommender."""

import pytest
from mcp_healthcare.pathway import CarePathwayRecommender
from mcp_healthcare.models import PathwayStep
from mcp_healthcare.audit import AuditLogger


def test_known_diagnosis(db_manager):
    """Test that a known diagnosis returns a non-empty ordered list of steps."""
    recommender = CarePathwayRecommender(db_manager=db_manager)
    steps = recommender.recommend("pneumonia", context={}, user_id="test-user")

    # Should return non-empty list
    assert len(steps) > 0

    # Each step should be a PathwayStep
    for step in steps:
        assert isinstance(step, PathwayStep)
        assert step.action
        assert step.detail


def test_unsupported_diagnosis(db_manager):
    """Test that an unsupported diagnosis returns empty list."""
    recommender = CarePathwayRecommender(db_manager=db_manager)
    steps = recommender.recommend("unknown_rare_condition", context={}, user_id="test-user")

    # Should return empty list
    assert len(steps) == 0


def test_audit_integrity(db_manager):
    """Test that audit entry includes recommendation count."""
    recommender = CarePathwayRecommender(db_manager=db_manager)
    steps = recommender.recommend("pneumonia", context={}, user_id="test-user")

    # Check audit log
    audit_logger = AuditLogger(db_manager=db_manager)
    logs = audit_logger.get_recent_logs(limit=1)

    assert len(logs) > 0
    latest_log = logs[0]
    assert latest_log["user_id"] == "test-user"
    # Response summary should include recommendation count
    assert f"recommendation_count={len(steps)}" in latest_log["response_summary"]
