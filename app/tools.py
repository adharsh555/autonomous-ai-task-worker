from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .config import settings
from .db import connect

# Demo-only deterministic failure injection. Globex's first write fails; retry succeeds.
_write_attempts: dict[str, int] = {}


def search_invoices(vendor: str) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, vendor, amount, due_date, issued_at FROM invoices WHERE lower(vendor)=lower(?) ORDER BY issued_at DESC",
            (vendor.strip(),),
        ).fetchall()
    return {"ok": True, "invoices": [dict(r) for r in rows], "count": len(rows)}


def get_invoice(invoice_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "invoice_not_found", "invoice_id": invoice_id}
    return {"ok": True, "invoice": dict(row)}


def write_billing_record(invoice_id: str, amount: float, due_date: str, approved: bool = False) -> dict[str, Any]:
    if amount >= settings.approval_threshold and not approved:
        return {
            "ok": False,
            "approval_required": True,
            "invoice_id": invoice_id,
            "amount": amount,
            "threshold": settings.approval_threshold,
        }

    with connect() as conn:
        source = conn.execute("SELECT amount, due_date, vendor FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not source:
            return {"ok": False, "error": "invoice_not_found", "invoice_id": invoice_id}
        if round(float(source["amount"]), 2) != round(float(amount), 2) or source["due_date"] != due_date:
            return {"ok": False, "error": "source_data_mismatch", "invoice_id": invoice_id}

        attempt = _write_attempts.get(invoice_id, 0) + 1
        _write_attempts[invoice_id] = attempt

        if source["vendor"].lower() == "globex" and attempt == 1:
            return {
                "ok": False,
                "retryable": True,
                "error": "billing_system_timeout",
                "message": "The simulated billing system timed out before confirming the write.",
                "attempt": attempt,
            }

        saved_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO billing_records(invoice_id, amount, due_date, saved_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(invoice_id) DO UPDATE SET amount=excluded.amount, due_date=excluded.due_date, saved_at=excluded.saved_at",
            (invoice_id, amount, due_date, saved_at),
        )

    return {"ok": True, "invoice_id": invoice_id, "amount": amount, "due_date": due_date, "saved_at": saved_at, "attempt": attempt}


def verify_billing_record(invoice_id: str) -> dict[str, Any]:
    with connect() as conn:
        source = conn.execute("SELECT amount, due_date, vendor FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        record = conn.execute("SELECT invoice_id, amount, due_date, saved_at FROM billing_records WHERE invoice_id=?", (invoice_id,)).fetchone()
    if not source:
        return {"ok": False, "verified": False, "error": "invoice_not_found"}
    if not record:
        return {"ok": True, "verified": False, "error": "billing_record_missing", "invoice_id": invoice_id}
    verified = round(float(source["amount"]), 2) == round(float(record["amount"]), 2) and source["due_date"] == record["due_date"]
    return {
        "ok": True,
        "verified": verified,
        "invoice_id": invoice_id,
        "vendor": source["vendor"],
        "amount": record["amount"],
        "due_date": record["due_date"],
        "saved_at": record["saved_at"],
    }


def execute(name: str, args: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    if name == "search_invoices":
        return search_invoices(str(args.get("vendor", "")))
    if name == "get_invoice":
        return get_invoice(str(args.get("invoice_id", "")))
    if name == "write_billing_record":
        return write_billing_record(str(args.get("invoice_id", "")), float(args.get("amount", 0)), str(args.get("due_date", "")), approved=approved)
    if name == "verify_billing_record":
        return verify_billing_record(str(args.get("invoice_id", "")))
    return {"ok": False, "error": "unknown_tool", "tool": name}
