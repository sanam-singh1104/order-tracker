import os

# Keep console exporters out of test output; tests install their own in-memory readers.
os.environ.setdefault("ORDER_TRACKER_CONSOLE_TELEMETRY", "false")
