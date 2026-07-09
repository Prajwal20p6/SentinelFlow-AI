import pytest
from app.core.tracing import TracingService

def test_tracing_span_measurement(capsys):
    # Test entering and exiting a trace span
    with TracingService.span("test_custom_span", {"custom_attr": "value1"}) as span:
        # Simulate work
        assert span.name == "test_custom_span"
        assert span.attributes["custom_attr"] == "value1"

    # Verify that entering/exiting spans prints log messages to stdout
    captured = capsys.readouterr()
    assert "span_started" in captured.out
    assert "span_ended" in captured.out
