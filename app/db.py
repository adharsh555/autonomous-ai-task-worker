from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent / "data" / "company.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL,
                due_date TEXT NOT NULL,
                issued_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS billing_records (
                invoice_id TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                due_date TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            );
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO invoices VALUES (?, ?, ?, ?, ?)",
                [
                    ("AC-2026-001", "Acme Corp", 1250.00, "2026-10-15", "2026-10-01T09:00:00"),
                    ("AC-2026-002", "Acme Corp", 1890.00, "2026-10-03", "2026-10-03T11:30:00"),
                    ("GL-2026-014", "Globex", 3200.00, "2026-10-20", "2026-10-02T14:15:00"),
                    ("UL-2026-044", "Umbrella Labs", 7200.00, "2026-10-28", "2026-10-03T16:40:00"),
                ],
            )
