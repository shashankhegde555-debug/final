import pytest
from backend.app.redact.redactor import redactor
from backend.app.ingest.schema_detect import normalize_alert_name, build_rule_key

def test_redaction_ipv4():
    text = "Failed to connect to 192.168.1.105:5432 after 3 retries"
    redacted = redactor.redact_text(text, enabled=True)
    assert "192.168.1.105" not in redacted
    assert "ip-" in redacted
    # Stable pseudonym check
    redacted2 = redactor.redact_text("Connecting to 192.168.1.105", enabled=True)
    assert redacted.split()[4].split(':')[0] == redacted2.split()[2]

def test_redaction_hostnames():
    text = "Cluster node srv-payments-db-42.prod.internal went down"
    redacted = redactor.redact_text(text, enabled=True)
    assert "srv-payments-db-42.prod.internal" not in redacted
    assert "host-" in redacted

def test_redaction_customer_identifiers():
    text = "Error processing payload for tenant_enterprise99 and cust-492184"
    redacted = redactor.redact_text(text, enabled=True)
    assert "tenant_enterprise99" not in redacted
    assert "cust-492184" not in redacted
    assert "cust-" in redacted

def test_redaction_toggle():
    text = "Secret host db-master.internal with IP 10.0.0.1"
    disabled = redactor.redact_text(text, enabled=False)
    assert disabled == text

def test_normalize_alert_name():
    raw_name = "DBQueryTimeout_1234_node-a8f9b2"
    norm = normalize_alert_name(raw_name)
    assert "1234" not in norm
    assert "dbquerytimeout" in norm

def test_rule_key_generation():
    key = build_rule_key("Prometheus", "Orders-DB", "HighLatency_P99_4891")
    assert key == "prometheus:orders-db:highlatency p"
