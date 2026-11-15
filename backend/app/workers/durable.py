"""Database-backed task queue; a worker claims each task with compare-and-swap.

Interrupted running tasks are deliberately retained for operator inspection.
Never requeue a task while its original worker may still be executing it.
"""
import logging
import time
from sqlalchemy import Column, JSON, String, Table, select, update
from app.repositories.sql import metadata

tasks = Table('backend_tasks', metadata,
    Column('id', String(128), primary_key=True),
    Column('state', String(16), nullable=False, index=True),
    Column('payload', JSON, nullable=False))


class DurableJobManager:
    def __init__(self, database):
        self.database = database

    def submit(self, job_id, work=None):
        # Job and queue insert share the caller's transaction.
        with self.database.transaction() as connection:
            connection.execute(tasks.insert().values(id=job_id, state='queued', payload={}))

    def claim(self):
        with self.database.transaction() as connection:
            query = select(tasks.c.id).where(tasks.c.state == 'queued').order_by(tasks.c.id).limit(1)
            if connection.dialect.name == 'postgresql':
                query = query.with_for_update(skip_locked=True)
            task_id = connection.execute(query).scalar_one_or_none()
            if task_id is None:
                return None
            changed = connection.execute(update(tasks).where(
                tasks.c.id == task_id, tasks.c.state == 'queued').values(state='running'))
            return task_id if changed.rowcount == 1 else None

    def run_one(self, container):
        task_id = self.claim()
        if task_id is None:
            return False
        try:
            job = container.jobs_repo.get(task_id)
            spec = container.analysis._normalise(job.request)
            container.analysis._execute(job=job, spec=spec,
                result_id=task_id.replace('job_', 'result_', 1), receipt_id=task_id.replace('job_', 'receipt_', 1))
            state = 'completed'
        except Exception:
            logging.getLogger(__name__).exception('Task failed: %s', task_id)
            job = container.jobs_repo.get(task_id)
            if job is not None and job.status.value not in ('completed', 'failed'):
                from datetime import datetime, timezone
                from app.schemas.analysis import JobState
                job.status = JobState.failed
                job.error = 'Worker could not execute this task; inspect server logs.'
                job.updated_at = datetime.now(timezone.utc)
                container.jobs_repo.replace(job)
            state = 'failed'
        with self.database.transaction() as connection:
            connection.execute(update(tasks).where(tasks.c.id == task_id).values(state=state))
        return True


def main():
    from app.core.dependencies import build_container
    container = build_container()
    if not isinstance(container.job_manager, DurableJobManager):
        raise RuntimeError('Worker requires JOB_BACKEND=database and DATABASE_URL')
    try:
        while True:
            if not container.job_manager.run_one(container):
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        container.database.engine.dispose()


if __name__ == '__main__':
    main()
