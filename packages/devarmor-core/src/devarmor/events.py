"""Event publishing and subscription system."""

import asyncio
import logging
from typing import Any, Callable, Optional
from uuid import uuid4

from .models import Event, EventType

logger = logging.getLogger(__name__)


class EventSubscriber:
    """A subscriber for events."""

    def __init__(
        self, subscriber_id: str, callback: Callable[[Event], Any], event_types: Optional[list[EventType]] = None
    ):
        """Initialize subscriber.

        Args:
            subscriber_id: Unique identifier for this subscriber
            callback: Async function to call when events are published
            event_types: List of event types to subscribe to (None = all)
        """
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.event_types = set(event_types) if event_types else None
        self.received_events: list[Event] = []

    def matches(self, event: Event) -> bool:
        """Check if this subscriber matches the event.

        Args:
            event: Event to check

        Returns:
            True if subscriber should receive this event
        """
        if self.event_types is None:
            return True
        return event.event_type in self.event_types

    async def notify(self, event: Event) -> None:
        """Notify subscriber of an event.

        Args:
            event: Event to send to subscriber
        """
        self.received_events.append(event)
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(event)
        else:
            self.callback(event)


class EventBus:
    """Publish and subscribe to events."""

    def __init__(self) -> None:
        """Initialize event bus."""
        self.subscribers: dict[str, EventSubscriber] = {}
        self.published_events: list[Event] = []
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        callback: Callable[[Event], Any],
        event_types: Optional[list[EventType]] = None,
        subscriber_id: Optional[str] = None,
    ) -> str:
        """Subscribe to events.

        Args:
            callback: Async function to call when events are published
            event_types: List of event types to subscribe to (None = all)
            subscriber_id: Optional identifier for this subscriber

        Returns:
            Subscriber ID for later unsubscription
        """
        if subscriber_id is None:
            subscriber_id = str(uuid4())

        subscriber = EventSubscriber(subscriber_id, callback, event_types)
        self.subscribers[subscriber_id] = subscriber

        logger.debug(f"Subscriber {subscriber_id} registered for {len(event_types or []) or 'all'} event types")

        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscriber_id: ID of subscriber to remove

        Returns:
            True if subscriber was removed, False if not found
        """
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            logger.debug(f"Subscriber {subscriber_id} unregistered")
            return True
        return False

    async def publish(self, event: Event) -> None:
        """Publish an event.

        Args:
            event: Event to publish
        """
        async with self._lock:
            self.published_events.append(event)

            logger.info(f"Publishing event: {event.event_type.value}", extra={"event_id": id(event)})

            # Notify all matching subscribers
            tasks = []
            for subscriber in self.subscribers.values():
                if subscriber.matches(event):
                    tasks.append(subscriber.notify(event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_skill_installed(
        self, skill_name: str, version: str, actor: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ) -> None:
        """Publish skill installed event.

        Args:
            skill_name: Name of installed skill
            version: Version of installed skill
            actor: Who triggered the installation
            details: Additional details
        """
        event = Event(
            event_type=EventType.SKILL_INSTALLED,
            skill_name=skill_name,
            actor=actor or "system",
            action="install",
            details={**(details or {}), "version": version},
            severity="info",
        )
        await self.publish(event)

    async def publish_skill_upgraded(
        self,
        skill_name: str,
        old_version: str,
        new_version: str,
        actor: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Publish skill upgraded event.

        Args:
            skill_name: Name of upgraded skill
            old_version: Previous version
            new_version: New version
            actor: Who triggered the upgrade
            details: Additional details
        """
        event = Event(
            event_type=EventType.SKILL_UPGRADED,
            skill_name=skill_name,
            actor=actor or "system",
            action="upgrade",
            details={**(details or {}), "old_version": old_version, "new_version": new_version},
            severity="info",
        )
        await self.publish(event)

    async def publish_skill_removed(
        self, skill_name: str, actor: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ) -> None:
        """Publish skill removed event.

        Args:
            skill_name: Name of removed skill
            actor: Who triggered the removal
            details: Additional details
        """
        event = Event(
            event_type=EventType.SKILL_REMOVED,
            skill_name=skill_name,
            actor=actor or "system",
            action="remove",
            details=details or {},
            severity="info",
        )
        await self.publish(event)

    async def publish_policy_violated(
        self,
        skill_name: str,
        violated_policies: list[str],
        actor: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Publish policy violated event.

        Args:
            skill_name: Name of skill that violated policy
            violated_policies: List of violated policy names
            actor: Who triggered the violation
            details: Additional details
        """
        event = Event(
            event_type=EventType.POLICY_VIOLATED,
            skill_name=skill_name,
            actor=actor or "system",
            action="policy_violation",
            details={**(details or {}), "violated_policies": violated_policies},
            severity="warning",
        )
        await self.publish(event)

    async def publish_access_denied(
        self,
        actor: str,
        action: str,
        resource: str,
        reason: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Publish access denied event.

        Args:
            actor: Who was denied access
            action: Action attempted
            resource: Resource being accessed
            reason: Reason for denial
            details: Additional details
        """
        event = Event(
            event_type=EventType.ACCESS_DENIED,
            actor=actor,
            action=action,
            details={**(details or {}), "resource": resource, "reason": reason},
            severity="warning",
        )
        await self.publish(event)

    def get_published_events(self, limit: Optional[int] = None) -> list[Event]:
        """Get recent published events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of published events
        """
        if limit:
            return self.published_events[-limit:]
        return self.published_events.copy()

    def get_subscriber_count(self) -> int:
        """Get number of active subscribers.

        Returns:
            Number of subscribers
        """
        return len(self.subscribers)

    def get_event_count(self) -> int:
        """Get number of published events.

        Returns:
            Number of events published
        """
        return len(self.published_events)
