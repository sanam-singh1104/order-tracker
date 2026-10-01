import logging
import os
import sys

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


SCOPE = "order-tracker"


def setup_telemetry():
    """Export traces, metrics, and logs.

    OTLP export (to the Collector) is on when OTEL_EXPORTER_OTLP_ENDPOINT is set.
    Console export (stdout, for `docker compose logs app`) is on unless
    ORDER_TRACKER_CONSOLE_TELEMETRY=false.
    """
    use_otlp = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    use_console = os.getenv("ORDER_TRACKER_CONSOLE_TELEMETRY", "true").lower() != "false"
    if not (use_otlp or use_console):
        return

    resource = Resource.create(
        {"service.name": os.getenv("OTEL_SERVICE_NAME", "order-tracker")}
    )

    tracer_provider = TracerProvider(resource=resource)
    logger_provider = LoggerProvider(resource=resource)
    # The export interval defaults to 60s; OTEL_METRIC_EXPORT_INTERVAL (ms) overrides it.
    metric_readers = []

    if use_otlp:
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        metric_readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    if use_console:
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout)))
        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=sys.stdout))
        )
        metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter(out=sys.stdout)))

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=metric_readers))
    set_logger_provider(logger_provider)

    app_logger = logging.getLogger(SCOPE)
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(LoggingHandler(logger_provider=logger_provider))
