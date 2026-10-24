"""Host-only bridge; no Alipay requests, public endpoints or exported keys."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repair-existing', action='store_true')
    parser.add_argument('--repo', default='/var/www/person_gift')
    parser.add_argument('--data', default='/var/lib/person-gift-alipay')
    args = parser.parse_args()
    os.umask(0o077)
    data = Path(args.data)
    with (data / 'telemetry-sync.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with sqlite3.connect((data / 'ledger.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
            rows = [json.loads(row[0]) for row in db.execute('SELECT data_json FROM transactions ORDER BY created_at,external_id')]
        container = subprocess.check_output(['docker', 'compose', 'ps', '-q', 'backend'], cwd=args.repo, text=True, timeout=30).strip()
        if not container or '\n' in container:
            raise RuntimeError('single backend container required')
        result = subprocess.run(['docker', 'exec', '-i', container, 'python', '-m', 'app.services.alipay_import'],
                                input=json.dumps({'rows': rows, 'repair_existing': args.repair_existing}),
                                text=True, capture_output=True, timeout=90)
        if result.returncode:
            # Do not log stdin, financial rows, environment or exception secrets.
            raise RuntimeError('backend import failed; exit=' + str(result.returncode))
        output = json.loads(result.stdout)
        temporary = data / 'telemetry-sync.tmp'
        temporary.write_text(json.dumps(output))
        temporary.replace(data / 'telemetry-sync.json')
        print(json.dumps(output))


if __name__ == '__main__':
    main()
