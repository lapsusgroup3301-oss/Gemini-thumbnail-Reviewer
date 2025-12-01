import uuid
from typing import Dict, Any

_jobs: Dict[str, Dict[str, Any]] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}
    return job_id


def set_job_result(job_id: str, result: Dict[str, Any]):
    if job_id in _jobs:
        _jobs[job_id] = {"status": "done", "result": result}


def set_job_error(job_id: str, error: str):
    if job_id in _jobs:
        _jobs[job_id] = {"status": "error", "error": error}


def get_job(job_id: str) -> Dict[str, Any]:
    return _jobs.get(job_id, {"status": "not_found"})
