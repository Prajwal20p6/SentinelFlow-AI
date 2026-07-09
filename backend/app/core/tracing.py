"""
SentinelFlow AI — OpenTelemetry Tracing Manager
Configures tracer providers, exports spans, and tracks request/service trace telemetry.
"""

import time
from typing import Dict, Any, Optional
from ..core.observability import logger

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class TraceSpan:
    """A lightweight context manager that tracks operation duration and outputs logs as span telemetry."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"span_started", span_name=self.name, **self.attributes)
        
        # OpenTelemetry integration if available
        if OTEL_AVAILABLE:
            try:
                tracer = trace.get_tracer("sentinelflow")
                self.otel_span = tracer.start_span(self.name, attributes=self.attributes)
            except Exception:
                self.otel_span = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000.0
        
        status = "SUCCESS"
        error_msg = None
        if exc_type is not None:
            status = "FAILED"
            error_msg = str(exc_val)
            
        logger.info(
            f"span_ended",
            span_name=self.name,
            duration_ms=round(duration_ms, 2),
            status=status,
            error=error_msg,
            **self.attributes
        )

        if OTEL_AVAILABLE and getattr(self, "otel_span", None):
            try:
                if exc_type is not None:
                    self.otel_span.set_status(trace.StatusCode.ERROR, description=str(exc_val))
                else:
                    self.otel_span.set_status(trace.StatusCode.OK)
                self.otel_span.end()
            except Exception:
                pass


class TracingService:
    """Configures tracing exporters and provides access to telemetry tracers."""

    @staticmethod
    def initialize_tracing(app) -> None:
        """Initializes OpenTelemetry providers and instruments the FastAPI app."""
        if not OTEL_AVAILABLE:
            logger.info("opentelemetry_tracing_not_available_locally")
            return

        try:
            provider = TracerProvider()
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            # Instrument FastAPI application
            FastAPIInstrumentor.instrument_app(app)
            logger.info("opentelemetry_fastapi_instrumented")
        except Exception as e:
            logger.warning("opentelemetry_init_failed", error=str(e))

    @staticmethod
    def span(name: str, attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """Helper to create a new TraceSpan context block."""
        return TraceSpan(name, attributes)
