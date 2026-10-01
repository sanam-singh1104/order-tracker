import logging
import os
import sys

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


SCOPE = "order-tracker"


def setup_telemetry():
    """Export traces, metrics, and logs to stdout so `docker compose logs app` shows them."""
    if os.getenv("ORDER_TRACKER_CONSOLE_TELEMETRY", "true").lower() == "false":
        return

    resource = Resource.create(
        {"service.name": os.getenv("OTEL_SERVICE_NAME", "order-tracker")}
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout)))
    trace.set_tracer_provider(tracer_provider)

    # The export interval defaults to 60s; OTEL_METRIC_EXPORT_INTERVAL (ms) overrides it.
    reader = PeriodicExportingMetricReader(ConsoleMetricExporter(out=sys.stdout))
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=sys.stdout))
    )
    set_logger_provider(logger_provider)

    app_logger = logging.getLogger(SCOPE)
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(LoggingHandler(logger_provider=logger_provider))
