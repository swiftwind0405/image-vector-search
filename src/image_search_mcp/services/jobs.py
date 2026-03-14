import json
from collections import deque
from datetime import UTC, datetime
from uuid import uuid4

from image_search_mcp.domain.models import JobRecord


class JobRunner:
    def __init__(self, repository, index_service) -> None:
        self.repository = repository
        self.index_service = index_service
        self._queue: deque[str] = deque()
        self._running_job_id: str | None = None

    def enqueue(self, job_type: str) -> JobRecord:
        now = datetime.now(UTC)
        job = JobRecord(
            id=uuid4().hex,
            job_type=job_type,
            status="queued",
            requested_at=now,
        )
        self.repository.create_job(job)
        self._queue.append(job.id)
        return job

    def run_next(self) -> JobRecord | None:
        if self._running_job_id is not None:
            raise RuntimeError("A job is already running")
        if not self._queue:
            return None

        job_id = self._queue.popleft()
        job = self.repository.get_job(job_id)
        if job is None:
            return None

        self._running_job_id = job_id
        started_at = datetime.now(UTC)
        self.repository.update_job(job_id, status="running", started_at=started_at)

        try:
            summary = self._run_job(job.job_type)
        except Exception as exc:
            finished_at = datetime.now(UTC)
            error_text = str(exc)
            self.repository.update_job(
                job_id,
                status="failed",
                finished_at=finished_at,
                error_text=error_text,
            )
            self.repository.set_system_state("last_error_summary", error_text)
        else:
            finished_at = datetime.now(UTC)
            self.repository.update_job(
                job_id,
                status="succeeded",
                finished_at=finished_at,
                summary_json=json.dumps(summary.model_dump()),
            )
        finally:
            self._running_job_id = None

        return self.repository.get_job(job_id)

    def _run_job(self, job_type: str):
        if job_type == "incremental":
            return self.index_service.run_incremental_update()
        if job_type == "full_rebuild":
            return self.index_service.run_full_rebuild()
        raise ValueError(f"Unsupported job type: {job_type}")
