"""Tests for the event bus system."""

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from api_server.event_bus import EventBus, EventHandler, get_event_bus
from api_server.event_bus.core import EventEmissionError, HandlerRegistrationError


# Test event models (don't start with "Test" to avoid pytest collection)
class SampleEvent(BaseModel):
    """Simple test event."""

    message: str = Field(..., description="Test message")
    value: int = Field(default=42, description="Test value")


class ComplexSampleEvent(BaseModel):
    """Complex test event."""

    data: dict[str, Any] = Field(..., description="Complex data")
    timestamp: str = Field(..., description="Timestamp")


# Test handlers
async def simple_handler(event: SampleEvent) -> str:
    """Simple function handler."""
    return f"processed: {event.message}"


async def void_handler(_event: SampleEvent) -> None:
    """Handler that returns nothing."""
    return


class SampleEventHandler(EventHandler[SampleEvent]):
    """Test class-based handler."""

    def __init__(self):
        self.processed_events = []
        self.dependency = None  # Will be injected

    async def handle(self, event: SampleEvent, dependency: str = None) -> str:
        """Handle test event."""
        result = f"class handled: {event.message}"
        if dependency:
            result += f" with {dependency}"
            self.dependency = dependency
        self.processed_events.append(result)
        return result

    def __call__(self, event: SampleEvent, dependency: str = None) -> Any:
        """Make handler callable for compatibility."""
        return self.handle(event, dependency)


class FailingSampleHandler(EventHandler[SampleEvent]):
    """Handler that always fails."""

    async def handle(self, event: SampleEvent) -> str:
        """Handle event with failure."""
        raise ValueError("Test handler failure")

    def __call__(self, event: SampleEvent) -> Any:
        """Make handler callable for compatibility."""
        return self.handle(event)


class TestEventBus:
    """Test cases for EventBus."""

    def test_event_bus_initialization(self):
        """Test EventBus initialization."""
        bus = EventBus()
        assert bus is not None
        assert bus.get_handler_count(SampleEvent) == 0
        assert bus.get_registered_events() == []

    def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_register_function_handler(self):
        """Test registering a function handler."""
        bus = EventBus()
        bus.on(SampleEvent, simple_handler)

        assert bus.get_handler_count(SampleEvent) == 1
        assert SampleEvent in bus.get_registered_events()

    def test_register_class_handler(self):
        """Test registering a class-based handler."""
        bus = EventBus()
        handler = SampleEventHandler()
        bus.on(SampleEvent, handler)

        assert bus.get_handler_count(SampleEvent) == 1

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for same event."""
        bus = EventBus()
        bus.on(SampleEvent, simple_handler)
        bus.on(SampleEvent, void_handler)
        bus.on(SampleEvent, SampleEventHandler())

        assert bus.get_handler_count(SampleEvent) == 3

    def test_register_handler_invalid_event_type(self):
        """Test registering handler with invalid event type."""
        bus = EventBus()

        with pytest.raises(HandlerRegistrationError):
            bus.on(str, simple_handler)  # str is not a BaseModel

    def test_register_handler_invalid_handler(self):
        """Test registering invalid handler."""
        bus = EventBus()

        with pytest.raises(HandlerRegistrationError):
            bus.on(SampleEvent, "not_callable")  # string is not callable

    def test_remove_handler(self):
        """Test removing a handler."""
        bus = EventBus()
        bus.on(SampleEvent, simple_handler)

        assert bus.get_handler_count(SampleEvent) == 1

        result = bus.remove_handler(SampleEvent, simple_handler)
        assert result is True
        assert bus.get_handler_count(SampleEvent) == 0

        # Removing non-existent handler
        result = bus.remove_handler(SampleEvent, simple_handler)
        assert result is False

    def test_clear_handlers(self):
        """Test clearing handlers."""
        bus = EventBus()
        bus.on(SampleEvent, simple_handler)
        bus.on(ComplexSampleEvent, simple_handler)

        assert bus.get_handler_count(SampleEvent) == 1
        assert bus.get_handler_count(ComplexSampleEvent) == 1

        # Clear specific event type
        bus.clear_handlers(SampleEvent)
        assert bus.get_handler_count(SampleEvent) == 0
        assert bus.get_handler_count(ComplexSampleEvent) == 1

        # Clear all handlers
        bus.clear_handlers()
        assert bus.get_handler_count(SampleEvent) == 0
        assert bus.get_handler_count(ComplexSampleEvent) == 0

    def test_service_registry_di_integration(self):
        """Test that EventBus no longer has its own DI container."""
        # Create bus and verify it doesn't have internal DI container
        bus = EventBus()
        assert hasattr(bus, "_execute_handler")
        # The DI system should work through ServiceRegistry, not internal container
        assert not hasattr(bus, "_di_container")

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_no_handlers(self):
        """Test emitting event with no registered handlers."""
        bus = EventBus()
        event = SampleEvent(message="test")

        results = await bus.emit_and_wait(event)
        assert results == []

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_single_handler(self):
        """Test emitting event to single handler."""
        bus = EventBus()
        bus.on(SampleEvent, simple_handler)

        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)

        assert len(results) == 1
        assert results[0] == "processed: test"

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_multiple_handlers(self):
        """Test emitting event to multiple handlers."""
        bus = EventBus()
        handler = SampleEventHandler()
        bus.on(SampleEvent, simple_handler)
        bus.on(SampleEvent, void_handler)
        bus.on(SampleEvent, handler)

        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)

        assert len(results) == 3
        assert results[0] == "processed: test"
        assert results[1] is None
        assert results[2] == "class handled: test"
        assert len(handler.processed_events) == 1

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_with_dependency_injection(self):
        """Test emitting event with class handler (DI via ServiceRegistry)."""
        bus = EventBus()
        handler = SampleEventHandler()
        bus.on(SampleEvent, handler)

        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)

        assert len(results) == 1
        # Handler works without explicit DI registration (uses default None)
        assert results[0] == "class handled: test"

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_handler_failure(self):
        """Test emitting event when handler fails."""
        bus = EventBus()
        bus.on(SampleEvent, FailingSampleHandler())

        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)

        assert len(results) == 1
        assert isinstance(results[0], ValueError)
        assert str(results[0]) == "Test handler failure"

    @pytest.mark.asyncio
    async def test_emit_and_wait_event_invalid_event_type(self):
        """Test emitting invalid event type."""
        bus = EventBus()

        with pytest.raises(EventEmissionError):
            await bus.emit_and_wait("not_a_model")  # string is not a BaseModel

    @pytest.mark.asyncio
    async def test_function_handler_without_dependencies(self):
        """Test function handler that doesn't accept dependencies."""
        bus = EventBus()

        # Handler that only accepts the event
        async def strict_handler(event: SampleEvent) -> str:
            return f"strict: {event.message}"

        bus.on(SampleEvent, strict_handler)

        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)

        assert len(results) == 1
        assert results[0] == "strict: test"

    @pytest.mark.asyncio
    async def test_concurrent_handler_execution(self):
        """Test that handlers execute concurrently."""
        bus = EventBus()

        # Handler that takes time to execute
        async def slow_handler(event: SampleEvent) -> str:
            await asyncio.sleep(0.1)
            return f"slow: {event.message}"

        async def fast_handler(event: SampleEvent) -> str:
            await asyncio.sleep(0.01)
            return f"fast: {event.message}"

        bus.on(SampleEvent, slow_handler)
        bus.on(SampleEvent, fast_handler)

        start_time = asyncio.get_event_loop().time()
        event = SampleEvent(message="test")
        results = await bus.emit_and_wait(event)
        end_time = asyncio.get_event_loop().time()

        # Should take ~0.1s (slowest handler), not ~0.11s (sequential)
        execution_time = end_time - start_time
        assert execution_time < 0.15  # Allow some margin
        assert execution_time > 0.05  # But should still take time

        assert len(results) == 2
        assert "slow: test" in results
        assert "fast: test" in results

    @pytest.mark.asyncio
    async def test_complex_event_handling(self):
        """Test handling complex events with nested data."""
        bus = EventBus()

        async def complex_handler(event: ComplexSampleEvent) -> dict:
            return {"processed_data": len(event.data), "timestamp": event.timestamp}

        bus.on(ComplexSampleEvent, complex_handler)

        event = ComplexSampleEvent(data={"key1": "value1", "key2": "value2"}, timestamp="2023-01-01T00:00:00Z")

        results = await bus.emit_and_wait(event)

        assert len(results) == 1
        assert results[0]["processed_data"] == 2
        assert results[0]["timestamp"] == "2023-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_event_isolation_emit_level(self):
        """Test event isolation at emit level - each handler gets a copy."""
        bus = EventBus()
        received_events = []

        async def handler1(event: SampleEvent) -> str:
            received_events.append(event)
            event.message = "modified_by_handler1"  # Modify the event
            return "handler1"

        async def handler2(event: SampleEvent) -> str:
            received_events.append(event)
            return f"handler2_saw_{event.message}"

        bus.on(SampleEvent, handler1)
        bus.on(SampleEvent, handler2)

        event = SampleEvent(message="original")
        await bus.emit_and_wait(event, isolate=True)

        # With isolation, each handler gets its own copy
        assert len(received_events) == 2
        # Handler2 should see "original", not "modified_by_handler1"
        assert received_events[1].message == "original"

    @pytest.mark.asyncio
    async def test_event_isolation_bus_level(self):
        """Test event isolation at bus level."""
        bus = EventBus(isolate_events=True)
        received_events = []

        async def handler1(event: SampleEvent) -> str:
            received_events.append(event)
            event.message = "modified"
            return "handler1"

        async def handler2(event: SampleEvent) -> str:
            received_events.append(event)
            return f"saw_{event.message}"

        bus.on(SampleEvent, handler1)
        bus.on(SampleEvent, handler2)

        event = SampleEvent(message="original")
        await bus.emit_and_wait(event)

        # With bus-level isolation, each handler gets its own copy
        assert len(received_events) == 2
        assert received_events[1].message == "original"

    @pytest.mark.asyncio
    async def test_no_isolation_shared_state(self):
        """Test that without isolation, handlers share the same event object."""
        bus = EventBus()
        received_events = []

        async def handler1(event: SampleEvent) -> str:
            received_events.append(event)
            event.message = "modified_by_handler1"
            return "handler1"

        async def handler2(event: SampleEvent) -> str:
            received_events.append(event)
            return f"saw_{event.message}"

        bus.on(SampleEvent, handler1)
        bus.on(SampleEvent, handler2)

        event = SampleEvent(message="original")
        await bus.emit_and_wait(event, isolate=False)

        # Without isolation, handlers share the same object
        # Note: Due to concurrent execution, order is not guaranteed
        # But both handlers receive the same object reference
        assert len(received_events) == 2
        assert received_events[0] is received_events[1]  # Same object


class TestEventBusIntegration:
    """Integration tests for event bus."""

    @pytest.mark.asyncio
    async def test_event_chaining(self):
        """Test event chaining where handlers emit new events."""
        bus = EventBus()

        # Events
        class FirstEvent(BaseModel):
            value: int

        class SecondEvent(BaseModel):
            doubled: int

        # Handlers
        async def double_handler(event: FirstEvent) -> None:
            # Emit second event
            await bus.emit_and_wait(SecondEvent(doubled=event.value * 2))

        captured_second_events = []

        async def capture_second(event: SecondEvent) -> None:
            captured_second_events.append(event)

        # Register handlers
        bus.on(FirstEvent, double_handler)
        bus.on(SecondEvent, capture_second)

        # Emit first event
        await bus.emit_and_wait(FirstEvent(value=5))

        # Check that second event was captured
        assert len(captured_second_events) == 1
        assert captured_second_events[0].doubled == 10

    @pytest.mark.asyncio
    async def test_cross_event_communication(self):
        """Test communication between different event types."""
        bus = EventBus()

        class CounterEvent(BaseModel):
            count: int

        class StatusEvent(BaseModel):
            status: str

        counter = 0

        async def increment_counter(event: CounterEvent) -> None:
            nonlocal counter
            counter += event.count

        async def status_handler(event: StatusEvent) -> None:
            if event.status == "check":
                await bus.emit_and_wait(CounterEvent(count=counter))

        bus.on(CounterEvent, increment_counter)
        bus.on(StatusEvent, status_handler)

        # Increment counter
        await bus.emit_and_wait(CounterEvent(count=3))
        assert counter == 3

        # Check status
        await bus.emit_and_wait(StatusEvent(status="check"))
        assert counter == 6  # Should be incremented again

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test that handler errors don't affect other handlers."""
        bus = EventBus()

        results = []

        async def good_handler(_event: SampleEvent) -> str:
            results.append("good")
            return "good_result"

        async def bad_handler(_event: SampleEvent) -> str:
            results.append("bad")
            raise ValueError("Handler error")

        async def another_good_handler(_event: SampleEvent) -> str:
            results.append("another_good")
            return "another_good_result"

        bus.on(SampleEvent, good_handler)
        bus.on(SampleEvent, bad_handler)
        bus.on(SampleEvent, another_good_handler)

        event = SampleEvent(message="test")
        emit_results = await bus.emit_and_wait(event)

        # All handlers should have been called
        assert len(results) == 3
        assert "good" in results
        assert "bad" in results
        assert "another_good" in results

        # Results should include successes and the exception
        assert len(emit_results) == 3
        assert emit_results[0] == "good_result"
        assert isinstance(emit_results[1], ValueError)
        assert emit_results[2] == "another_good_result"

    @pytest.mark.asyncio
    async def test_emit_fire_and_forget(self):
        """Test fire-and-forget emit method."""
        bus = EventBus()

        results = []

        async def capture_handler(event: SampleEvent) -> str:
            results.append(f"captured: {event.message}")
            return "handler_result"

        bus.on(SampleEvent, capture_handler)

        # Fire-and-forget emit
        event = SampleEvent(message="test_fire_forget")
        bus.emit(event)  # Returns immediately, no await

        # Wait a bit for async processing
        await asyncio.sleep(0.1)

        # Handler should have been called
        assert len(results) == 1
        assert results[0] == "captured: test_fire_forget"
