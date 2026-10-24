"""Read-only operational summary; never prints cookies, QR tokens or bill details."""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def read_status(data: Path):
    status = json.loads((data / "status.json").read_text())
    result = {"status": status}
    start = status.get("session_observed_at")
    last = status.get("last_success_at")
    if start and last:
        result["verified_query_span_seconds"] = max(0, int((datetime.fromisoformat(last) - datetime.fromisoformat(start)).total_seconds()))
    failed = status.get("first_auth_required_at")
    if failed and last:
        result["auth_failure_observed_between"] = {"last_success": last, "first_auth_required": failed}
    db = sqlite3.connect((data / "ledger.sqlite3").as_uri() + "?mode=ro", uri=True)
    result["stored_transactions"] = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    result["recent_runs"] = [
        {"started_at": row[0], "finished_at": row[1], "state": row[2], "result": json.loads(row[3])}
        for row in db.execute("SELECT started_at,finished_at,state,metadata_json FROM runs ORDER BY id DESC LIMIT 6")
    ]
    result["recent_session_events"] = [
        {"observed_at": row[0], "state": row[1], "result": json.loads(row[2])}
        for row in db.execute("SELECT observed_at,state,metadata_json FROM session_events ORDER BY id DESC LIMIT 8")
    ]
    db.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("/var/lib/person-gift-alipay"))
    args = parser.parse_args()
    print(json.dumps(read_status(args.data.resolve()), ensure_ascii=False, indent=2))
