from app.db import init_db
from app.tools import get_invoice, search_invoices, write_billing_record, verify_billing_record


def setup_module():
    init_db()


def test_search_acme():
    result = search_invoices("Acme Corp")
    assert result["ok"] is True
    assert result["count"] == 2


def test_source_validation():
    result = write_billing_record("AC-2026-001", 999, "2026-10-15")
    assert result["error"] == "source_data_mismatch"


def test_approval_threshold():
    result = write_billing_record("UL-2026-044", 7200, "2026-10-28")
    assert result["approval_required"] is True


def test_globex_retry_then_verify():
    first = write_billing_record("GL-2026-014", 3200, "2026-10-20")
    assert first["retryable"] is True
    second = write_billing_record("GL-2026-014", 3200, "2026-10-20")
    assert second["ok"] is True
    verified = verify_billing_record("GL-2026-014")
    assert verified["verified"] is True
