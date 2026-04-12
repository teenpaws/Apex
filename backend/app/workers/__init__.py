"""
Apex Celery worker package.

Tasks are auto-discovered by Celery via the ``include`` list in
``app.core.celery_app``.  Import individual task modules only when you
need to call a task directly (e.g. in tests).
"""
