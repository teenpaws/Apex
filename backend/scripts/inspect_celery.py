"""See what's actively running on Celery workers."""
import sys
sys.path.insert(0, '.')
from app.core.celery_app import celery_app

i = celery_app.control.inspect()
active = i.active() or {}
for worker, tasks in active.items():
    print(f"Worker {worker}: {len(tasks)} active task(s)")
    for t in tasks:
        print(f"  task_id={t['id']}  name={t['name']}")
        if t.get('args'):
            print(f"    args={t['args']}")

if not active:
    print("No active tasks (or worker not responding to inspect).")
