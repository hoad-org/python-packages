"""Tests for audit logging."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from devarmor.audit import AuditLogger, AuditReader
from devarmor.models import PolicyEvaluation


class TestAuditLogger:
    """Test AuditLogger class."""

    @pytest.fixture
    def logger(self) -> AuditLogger:
        """Create audit logger with temp directory."""
        with TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            yield logger

    def test_log_action(self, logger: AuditLogger) -> None:
        """Test logging an action."""
        entry = logger.log_action(
            actor="user",
            action="create",
            resource="skill",
            result="success",
        )

        assert entry.actor == "user"
        assert entry.action == "create"
        assert entry.resource == "skill"
        assert entry.result == "success"

    def test_log_action_with_details(self, logger: AuditLogger) -> None:
        """Test logging action with additional details."""
        entry = logger.log_action(
            actor="user",
            action="create",
            resource="skill",
            result="success",
            details={"version": "1.0.0", "metadata": "value"},
        )

        assert entry.details["version"] == "1.0.0"
        assert entry.details["metadata"] == "value"

    def test_log_policy_evaluation(self, logger: AuditLogger) -> None:
        """Test logging policy evaluation."""
        evaluation = PolicyEvaluation(
            allowed=False,
            violated_policies=["policy1", "policy2"],
            reason="Test violation",
        )

        entry = logger.log_policy_evaluation(
            actor="user",
            action="install",
            resource="skill",
            evaluation=evaluation,
        )

        assert entry.result == "denied"
        assert entry.policy_evaluation is not None
        assert entry.policy_evaluation["allowed"] is False

    def test_log_skill_lifecycle(self, logger: AuditLogger) -> None:
        """Test logging skill lifecycle operation."""
        entry = logger.log_skill_lifecycle(
            skill_name="test-skill",
            operation="install",
            version="1.0.0",
            result="success",
        )

        assert entry.action == "install"
        assert entry.resource == "test-skill"
        assert entry.result == "success"

    def test_log_skill_lifecycle_with_error(self, logger: AuditLogger) -> None:
        """Test logging skill lifecycle with error."""
        entry = logger.log_skill_lifecycle(
            skill_name="test-skill",
            operation="install",
            version="1.0.0",
            result="failure",
            error="Installation failed",
        )

        assert entry.result == "failure"
        assert entry.details["error"] == "Installation failed"

    def test_get_entries(self, logger: AuditLogger) -> None:
        """Test getting entries."""
        logger.log_action("user1", "create", "skill", "success")
        logger.log_action("user2", "delete", "skill", "success")

        entries = logger.get_entries()

        assert len(entries) == 2

    def test_get_entries_with_limit(self, logger: AuditLogger) -> None:
        """Test getting entries with limit."""
        for i in range(5):
            logger.log_action(f"user{i}", "action", "resource", "success")

        entries = logger.get_entries(limit=2)

        assert len(entries) == 2

    def test_get_entries_for_actor(self, logger: AuditLogger) -> None:
        """Test getting entries for specific actor."""
        logger.log_action("alice", "create", "skill1", "success")
        logger.log_action("bob", "create", "skill2", "success")
        logger.log_action("alice", "delete", "skill3", "success")

        entries = logger.get_entries_for_actor("alice")

        assert len(entries) == 2
        assert all(e.actor == "alice" for e in entries)

    def test_get_entries_for_resource(self, logger: AuditLogger) -> None:
        """Test getting entries for specific resource."""
        logger.log_action("user1", "create", "skill1", "success")
        logger.log_action("user2", "create", "skill2", "success")
        logger.log_action("user3", "delete", "skill1", "success")

        entries = logger.get_entries_for_resource("skill1")

        assert len(entries) == 2
        assert all(e.resource == "skill1" for e in entries)

    def test_export_to_json(self, logger: AuditLogger) -> None:
        """Test exporting audit log to JSON."""
        logger.log_action("user", "create", "skill", "success")

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "audit.json"
            logger.export_to_json(output_file)

            assert output_file.exists()

            with open(output_file) as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]["actor"] == "user"

    def test_write_to_disk(self, logger: AuditLogger) -> None:
        """Test that entries are written to disk."""
        logger.log_action("user", "create", "skill", "success")

        # Check that log file was created
        log_files = list(logger.log_dir.glob("*.jsonl"))
        assert len(log_files) > 0

        # Check file content
        with open(log_files[0]) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["actor"] == "user"


class TestAuditReader:
    """Test AuditReader class."""

    def test_read_logs(self) -> None:
        """Test reading audit logs."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Create a logger and write some entries
            logger = AuditLogger(log_dir=log_dir)
            logger.log_action("user1", "create", "skill", "success")
            logger.log_action("user2", "delete", "skill", "success")

            # Read logs
            reader = AuditReader(log_dir=log_dir)
            entries = reader.read_logs()

            assert len(entries) == 2

    def test_read_logs_not_found(self) -> None:
        """Test reading logs when directory doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "nonexistent"

            reader = AuditReader(log_dir=log_dir)
            entries = reader.read_logs()

            assert len(entries) == 0

    def test_find_entries_by_actor(self) -> None:
        """Test finding entries by actor."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            logger = AuditLogger(log_dir=log_dir)
            logger.log_action("alice", "create", "skill1", "success")
            logger.log_action("bob", "create", "skill2", "success")
            logger.log_action("alice", "delete", "skill3", "success")

            reader = AuditReader(log_dir=log_dir)
            entries = reader.find_entries(actor="alice")

            assert len(entries) == 2
            assert all(e.actor == "alice" for e in entries)

    def test_find_entries_by_action(self) -> None:
        """Test finding entries by action."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            logger = AuditLogger(log_dir=log_dir)
            logger.log_action("user1", "create", "skill1", "success")
            logger.log_action("user2", "create", "skill2", "success")
            logger.log_action("user3", "delete", "skill3", "success")

            reader = AuditReader(log_dir=log_dir)
            entries = reader.find_entries(action="create")

            assert len(entries) == 2
            assert all(e.action == "create" for e in entries)

    def test_find_entries_by_both_filters(self) -> None:
        """Test finding entries with multiple filters."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            logger = AuditLogger(log_dir=log_dir)
            logger.log_action("alice", "create", "skill1", "success")
            logger.log_action("alice", "delete", "skill2", "success")
            logger.log_action("bob", "create", "skill3", "success")

            reader = AuditReader(log_dir=log_dir)
            entries = reader.find_entries(actor="alice", action="create")

            assert len(entries) == 1
            assert entries[0].actor == "alice"
            assert entries[0].action == "create"
