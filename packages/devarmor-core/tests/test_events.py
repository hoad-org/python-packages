"""Tests for event system."""

import pytest

from devarmor.events import EventBus
from devarmor.models import Event, EventType


class TestEventBus:
    """Test EventBus class."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self) -> None:
        """Test subscribing to events and publishing."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        subscriber_id = bus.subscribe(callback)

        assert subscriber_id is not None
        assert bus.get_subscriber_count() == 1

        # Publish event
        event = Event(
            event_type=EventType.SKILL_INSTALLED,
            skill_name="test-skill",
        )
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].event_type == EventType.SKILL_INSTALLED

    @pytest.mark.asyncio
    async def test_subscribe_to_specific_event_types(self) -> None:
        """Test subscribing to specific event types."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        # Subscribe to only install events
        bus.subscribe(callback, event_types=[EventType.SKILL_INSTALLED])

        # Publish install event
        event1 = Event(event_type=EventType.SKILL_INSTALLED, skill_name="skill1")
        await bus.publish(event1)

        # Publish upgrade event
        event2 = Event(event_type=EventType.SKILL_UPGRADED, skill_name="skill1")
        await bus.publish(event2)

        # Should only receive install event
        assert len(received) == 1
        assert received[0].event_type == EventType.SKILL_INSTALLED

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        """Test unsubscribing from events."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        subscriber_id = bus.subscribe(callback)

        # Unsubscribe
        result = bus.unsubscribe(subscriber_id)
        assert result is True

        # Publish event
        event = Event(event_type=EventType.SKILL_INSTALLED, skill_name="test")
        await bus.publish(event)

        # Should not have received event
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_not_found(self) -> None:
        """Test unsubscribing when subscriber doesn't exist."""
        bus = EventBus()

        result = bus.unsubscribe("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_skill_installed(self) -> None:
        """Test publishing skill installed event."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(callback)

        await bus.publish_skill_installed(
            skill_name="test-skill",
            version="1.0.0",
            actor="user",
        )

        assert len(received) == 1
        assert received[0].event_type == EventType.SKILL_INSTALLED
        assert received[0].skill_name == "test-skill"

    @pytest.mark.asyncio
    async def test_publish_skill_upgraded(self) -> None:
        """Test publishing skill upgraded event."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(callback)

        await bus.publish_skill_upgraded(
            skill_name="test-skill",
            old_version="1.0.0",
            new_version="2.0.0",
            actor="user",
        )

        assert len(received) == 1
        assert received[0].event_type == EventType.SKILL_UPGRADED
        assert received[0].details["old_version"] == "1.0.0"
        assert received[0].details["new_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_publish_skill_removed(self) -> None:
        """Test publishing skill removed event."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(callback)

        await bus.publish_skill_removed(skill_name="test-skill", actor="user")

        assert len(received) == 1
        assert received[0].event_type == EventType.SKILL_REMOVED

    @pytest.mark.asyncio
    async def test_publish_policy_violated(self) -> None:
        """Test publishing policy violated event."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(callback)

        await bus.publish_policy_violated(
            skill_name="blocked-skill",
            violated_policies=["skill_permissions:blocked"],
            actor="user",
        )

        assert len(received) == 1
        assert received[0].event_type == EventType.POLICY_VIOLATED
        assert "blocked" in str(received[0].details)

    @pytest.mark.asyncio
    async def test_publish_access_denied(self) -> None:
        """Test publishing access denied event."""
        bus = EventBus()
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(callback)

        await bus.publish_access_denied(
            actor="user",
            action="install",
            resource="blocked-skill",
            reason="Skill is blocked",
        )

        assert len(received) == 1
        assert received[0].event_type == EventType.ACCESS_DENIED
        assert received[0].actor == "user"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self) -> None:
        """Test multiple subscribers receiving same event."""
        bus = EventBus()
        received1: list[Event] = []
        received2: list[Event] = []

        async def callback1(event: Event) -> None:
            received1.append(event)

        async def callback2(event: Event) -> None:
            received2.append(event)

        bus.subscribe(callback1)
        bus.subscribe(callback2)

        event = Event(event_type=EventType.SKILL_INSTALLED, skill_name="test")
        await bus.publish(event)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_get_published_events(self) -> None:
        """Test getting published events."""
        bus = EventBus()

        event1 = Event(event_type=EventType.SKILL_INSTALLED, skill_name="skill1")
        event2 = Event(event_type=EventType.SKILL_UPGRADED, skill_name="skill2")

        bus.published_events.append(event1)
        bus.published_events.append(event2)

        events = bus.get_published_events()
        assert len(events) == 2

        # With limit
        events = bus.get_published_events(limit=1)
        assert len(events) == 1

    def test_get_subscriber_count(self) -> None:
        """Test getting subscriber count."""
        bus = EventBus()

        async def callback(event: Event) -> None:
            pass

        assert bus.get_subscriber_count() == 0

        bus.subscribe(callback)
        assert bus.get_subscriber_count() == 1

        bus.subscribe(callback)
        assert bus.get_subscriber_count() == 2

    def test_get_event_count(self) -> None:
        """Test getting event count."""
        bus = EventBus()

        assert bus.get_event_count() == 0

        event = Event(event_type=EventType.SKILL_INSTALLED, skill_name="test")
        bus.published_events.append(event)

        assert bus.get_event_count() == 1

    @pytest.mark.asyncio
    async def test_sync_callback_support(self) -> None:
        """Test that sync callbacks are supported."""
        bus = EventBus()
        received: list[Event] = []

        def sync_callback(event: Event) -> None:
            received.append(event)

        bus.subscribe(sync_callback)

        event = Event(event_type=EventType.SKILL_INSTALLED, skill_name="test")
        await bus.publish(event)

        assert len(received) == 1
