import pytest
import time
from app.services.circuit_breaker_service import CircuitBreakerService, CircuitBreakerOpenException

def test_circuit_breaker_trip_and_recover():
    service_name = "test_flaky_service"
    breaker = CircuitBreakerService.get_breaker(service_name)
    breaker.reset()
    
    # Pre-condition: closed
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0

    # Define a helper function that raises an error
    def failing_api_call():
        raise ValueError("API error")

    def successful_api_call():
        return "success"

    # Make 5 failing calls to trip the circuit
    for _ in range(5):
        with pytest.raises(ValueError):
            CircuitBreakerService.call(service_name, failing_api_call)

    # After 5 failures, the circuit breaker should be OPEN
    assert breaker.state == "OPEN"
    assert breaker.failure_count == 5

    # Any subsequent call should fail fast raising CircuitBreakerOpenException immediately
    with pytest.raises(CircuitBreakerOpenException):
        CircuitBreakerService.call(service_name, successful_api_call)

    # Fast-forward / mock recovery timeout
    breaker.last_state_change = time.time() - 61.0  # mock 61 seconds in OPEN state
    
    # State check should transition it to HALF_OPEN
    assert breaker.check_state() == "HALF_OPEN"

    # In HALF_OPEN: test call succeeds -> resets to CLOSED
    res = CircuitBreakerService.call(service_name, successful_api_call)
    assert res == "success"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0
