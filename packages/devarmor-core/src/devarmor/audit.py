"""Audit logging for DevArmor."""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .models import AuditLogEntry, PolicyEvaluation

logger = logging.getLogger(__name__)


class AuditLogger:
    """Log all DevArmor decisions and actions."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            log_dir: Directory for audit logs (default: ~/.devarmor/audit)
        """
        self.log_dir = log_dir or (Path.home() / ".devarmor" / "audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[AuditLogEntry] = []

    def log_action(
        self,
        actor: str,
        action: str,
        resource: str,
        result: str,
        details: Optional[dict[str, Any]] = None,
        policy_evaluation: Optional[PolicyEvaluation] = None,
    ) -> AuditLogEntry:
        """Log an action.

        Args:
            actor: Who performed the action (user, skill, system)
            action: Action performed (create, modify, delete, access, etc.)
            resource: Resource affected (skill name, policy, etc.)
            result: Outcome (success, failure, denied)
            details: Additional details about the action
            policy_evaluation: Policy evaluation result if applicable

        Returns:
            AuditLogEntry: The logged entry
        """
        event_id = str(uuid4())
        entry = AuditLogEntry(
            event_id=event_id,
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            policy_evaluation=policy_evaluation.model_dump() if policy_evaluation else None,
        )

        self.entries.append(entry)
        self._write_to_disk(entry)

        logger.info(
            f"Audit: {actor} {action} {resource} -> {result}",
            extra={
                "audit": True,
                "event_id": event_id,
                "actor": actor,
                "action": action,
                "resource": resource,
                "result": result,
            },
        )

        return entry

    def log_policy_evaluation(
        self,
        actor: str,
        action: str,
        resource: str,
        evaluation: PolicyEvaluation,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """Log a policy evaluation result.

        Args:
            actor: Who requested the action
            action: Action being evaluated
            resource: Resource being evaluated
            evaluation: PolicyEvaluation result
            details: Additional details

        Returns:
            AuditLogEntry: The logged entry
        """
        result = "allowed" if evaluation.allowed else "denied"
        return self.log_action(
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            details={**(details or {}), "evaluation_reason": evaluation.reason},
            policy_evaluation=evaluation,
        )

    def log_skill_lifecycle(
        self,
        skill_name: str,
        operation: str,
        version: Optional[str],
        result: str,
        error: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """Log skill lifecycle operation (install/upgrade/remove).

        Args:
            skill_name: Name of the skill
            operation: Operation type (install, upgrade, remove)
            version: Skill version (if applicable)
            result: Outcome (success, failure)
            error: Error message if failed
            details: Additional details

        Returns:
            AuditLogEntry: The logged entry
        """
        entry_details = {
            "operation": operation,
            "version": version,
            **(details or {}),
        }
        if error:
            entry_details["error"] = error

        return self.log_action(
            actor="system",
            action=operation,
            resource=skill_name,
            result=result,
            details=entry_details,
        )

    def get_entries(self, limit: Optional[int] = None) -> list[AuditLogEntry]:
        """Get recent audit entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of AuditLogEntry objects
        """
        if limit:
            return self.entries[-limit:]
        return self.entries.copy()

    def get_entries_for_actor(self, actor: str) -> list[AuditLogEntry]:
        """Get audit entries for a specific actor.

        Args:
            actor: Actor name to filter by

        Returns:
            List of AuditLogEntry objects
        """
        return [e for e in self.entries if e.actor == actor]

    def get_entries_for_resource(self, resource: str) -> list[AuditLogEntry]:
        """Get audit entries for a specific resource.

        Args:
            resource: Resource name to filter by

        Returns:
            List of AuditLogEntry objects
        """
        return [e for e in self.entries if e.resource == resource]

    def export_to_json(self, output_path: Path) -> None:
        """Export audit log to JSON file.

        Args:
            output_path: Path to write JSON export
        """
        with open(output_path, "w") as f:
            json.dump(
                [entry.model_dump() for entry in self.entries],
                f,
                indent=2,
                default=str,
            )
        logger.info(f"Exported audit log to {output_path}")

    def _write_to_disk(self, entry: AuditLogEntry) -> None:
        """Write audit entry to disk.

        Args:
            entry: AuditLogEntry to persist
        """
        try:
            # Use date-based log files (YYYY-MM-DD.jsonl)
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"{date_str}.jsonl"

            with open(log_file, "a") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log to disk: {str(e)}")


class AuditReader:
    """Read audit logs from disk."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize audit reader.

        Args:
            log_dir: Directory containing audit logs
        """
        self.log_dir = log_dir or (Path.home() / ".devarmor" / "audit")

    def read_logs(self, days: int = 7) -> list[AuditLogEntry]:
        """Read audit logs from last N days.

        Args:
            days: Number of days to read (default: 7)

        Returns:
            List of AuditLogEntry objects
        """
        entries: list[AuditLogEntry] = []

        if not self.log_dir.exists():
            return entries

        for log_file in sorted(self.log_dir.glob("*.jsonl")):
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entry = AuditLogEntry(**data)
                            entries.append(entry)
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse audit log entry: {str(e)}")

        return entries

    def find_entries(self, actor: Optional[str] = None, action: Optional[str] = None) -> list[AuditLogEntry]:
        """Find audit entries by criteria.

        Args:
            actor: Filter by actor name
            action: Filter by action type

        Returns:
            List of matching AuditLogEntry objects
        """
        all_entries = self.read_logs()
        results = all_entries

        if actor:
            results = [e for e in results if e.actor == actor]

        if action:
            results = [e for e in results if e.action == action]

        return results
