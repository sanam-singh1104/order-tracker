import pytest
from fastapi.testclient import TestClient
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app import main


@pytest.fixture(scope="module")
def reader():
    # Instruments in app.main were created on the global proxy, so they start
    # reporting here once a real provider is installed (only once per process).
    reader = InMemoryMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
    return reader


@pytest.fixture
def client(tmp_path, monkeypatch, reader):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "orders.db")
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client


def request_counts(reader):
    counts = {}
    data = reader.get_metrics_data()
    for resource_metrics in data.resource_metrics if data else ():
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == "order_tracker.http.requests":
                    for point in metric.data.data_points:
                        attrs = point.attributes
                        key = (attrs["http.route"], attrs["http.response.status_code"])
                        counts[key] = point.value
    return counts


def test_request_metric_has_route_and_status(client, reader, monkeypatch):
    before = request_counts(reader)
    assert client.get("/api/orders/standard-1001").status_code == 200
    assert client.get("/api/orders/missing").status_code == 404

    def broken(_row):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "order_detail", broken)
    assert client.get("/api/orders/standard-1003").status_code == 500

    after = request_counts(reader)
    route = "/api/orders/{order_id}"
    for status in (200, 404, 500):
        assert after[(route, status)] - before.get((route, status), 0) == 1
