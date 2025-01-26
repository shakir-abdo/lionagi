from datetime import datetime

import pytest

from lionagi.protocols.generic.event import Event, EventStatus, Execution


def test_event_status_enum():
    assert EventStatus.PENDING == "pending"
    assert EventStatus.PROCESSING == "processing"
    assert EventStatus.COMPLETED == "completed"
    assert EventStatus.FAILED == "failed"


def test_execution_initialization():
    execution = Execution()
    assert execution.status == EventStatus.PENDING
    assert execution.duration is None
    assert execution.response is None
    assert execution.error is None


def test_execution_str_representation():
    execution = Execution(
        duration=1.23,
        response="test",
        status=EventStatus.COMPLETED,
        error=None,
    )
    assert "Execution(status=completed" in str(execution)
    assert "duration=1.23" in str(execution)
    assert "response=test" in str(execution)


def test_event_initialization():
    event = Event()
    assert event.status == EventStatus.PENDING
    assert event.response is None
    assert isinstance(event.execution, Execution)


def test_event_properties():
    event = Event()
    event.status = EventStatus.PROCESSING
    event.response = "test response"

    assert event.status == EventStatus.PROCESSING
    assert event.response == "test response"
    assert event.request == {}


def test_event_serialization():
    event = Event()
    event.status = EventStatus.COMPLETED
    event.response = {"result": "success"}

    serialized = event.model_dump()
    assert serialized["execution"]["status"] == "completed"
    assert serialized["execution"]["response"] == {"result": "success"}


import pytest_asyncio


@pytest.mark.asyncio
async def test_event_invoke_not_implemented():
    event = Event()
    with pytest.raises(NotImplementedError):
        await event.invoke()


def test_event_from_dict_not_implemented():
    with pytest.raises(NotImplementedError):
        Event.from_dict({})


def test_event_with_error():
    execution = Execution(status=EventStatus.FAILED, error="Test error")
    event = Event(execution=execution)

    assert event.status == EventStatus.FAILED
    assert event.execution.error == "Test error"


def test_event_duration():
    start = datetime.now().timestamp()
    execution = Execution(duration=1.5)
    event = Event(execution=execution)

    assert event.execution.duration == 1.5
    assert event.created_at >= start
