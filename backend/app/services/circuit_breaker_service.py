"""
SentinelFlow AI — External Dependency Circuit Breaker Service
Implements Closed, Open, and Half-Open circuit breaker states with cascading fallbacks.
"""

import time
from typing import Callable, Any, Dict, Optional
from ..core.observability import logger

class CircuitBreakerOpenException(Exception):
    """Raised when a request is blocked because the service's circuit breaker is open."""
    pass

class CircuitBreaker:
    """Represents a circuit breaker for a specific service."""
    
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()

    def trip(self):
        """Trips the circuit breaker to OPEN state."""
        self.state = "OPEN"
        self.last_state_change = time.time()
        logger.warning(
            "circuit_breaker_tripped",
            service=self.name,
            state="OPEN",
            failures=self.failure_count
        )
        # Emit metrics if Prometheus client is active
        try:
            from ..core.observability import logger as obs_logger
            # Prometheus counter can be added here or logs recorded
        except Exception:
            pass

    def reset(self):
        """Resets the circuit breaker back to CLOSED state."""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
        logger.info("circuit_breaker_reset", service=self.name, state="CLOSED")

    def half_open(self):
        """Transitions the circuit breaker to HALF_OPEN state."""
        self.state = "HALF_OPEN"
        self.last_state_change = time.time()
        logger.info("circuit_breaker_half_open", service=self.name, state="HALF_OPEN")

    def check_state(self) -> str:
        """
        Updates and returns the current state of the circuit breaker.
        Handles timeout transitions from OPEN to HALF_OPEN.
        """
        if self.state == "OPEN" and self.last_state_change is not None:
            now = time.time()
            if now - self.last_state_change >= self.recovery_timeout:
                self.half_open()
        return self.state

    def record_success(self):
        """Records a successful operation, resetting the breaker."""
        if self.state == "HALF_OPEN":
            self.reset()
        else:
            self.failure_count = 0
            self.last_failure_time = None

    def record_failure(self):
        """Records a failed operation, incrementing count and potentially tripping."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state in ("CLOSED", "HALF_OPEN") and self.failure_count >= self.failure_threshold:
            self.trip()


class CircuitBreakerService:
    """Global manager for registering, checking, and calling services through circuit breakers."""
    
    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_breaker(cls, service_name: str) -> CircuitBreaker:
        """Gets or creates a circuit breaker instance for a given service."""
        if service_name not in cls._breakers:
            cls._breakers[service_name] = CircuitBreaker(service_name)
        return cls._breakers[service_name]

    @classmethod
    def call(cls, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Executes a callable protected by the circuit breaker for service_name.
        Raises CircuitBreakerOpenException if the circuit is OPEN.
        """
        breaker = cls.get_breaker(service_name)
        state = breaker.check_state()

        if state == "OPEN":
            logger.debug("circuit_breaker_blocked_call", service=service_name)
            raise CircuitBreakerOpenException(f"Circuit breaker for service '{service_name}' is OPEN. Failing fast.")

        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            logger.warning("circuit_breaker_call_failed", service=service_name, error=str(e))
            raise e

    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        """Returns details of all registered circuit breakers."""
        # Pre-seed standard breakers so they always show on UI
        standard_services = ["openai", "anthropic", "gemini", "virustotal", "qdrant", "redis", "smtp", "cloud_provider"]
        for s in standard_services:
            cls.get_breaker(s)

        status = {}
        for name, breaker in cls._breakers.items():
            status[name] = {
                "name": name,
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
                "recovery_timeout": breaker.recovery_timeout,
                "fallback_active": breaker.state in ("OPEN", "HALF_OPEN")
            }
        return status
