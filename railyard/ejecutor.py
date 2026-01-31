import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Job:
    job_id: str
    job_type: str
    command: list[str]
    process: subprocess.Popen[str]
    started_at: float

    @property
    def is_running(self) -> bool:
        return self.process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return self.process.poll()

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.started_at

    def stream_output(self) -> Iterator[str]:
        """Stream output lines from this job in real-time"""
        try:
            if self.process.stdout:
                for line in self.process.stdout:
                    elapsed = self.elapsed_time
                    yield f"[{elapsed:.1f}s] {line}"

                    # Check for very long running jobs (optional timeout)
                    if elapsed > 600:  # 10 minutes default timeout
                        yield f"[{elapsed:.1f}s] ⚠️ Job timed out after 10 minutes\n"
                        break

            self.process.stdout.close() if self.process.stdout else None
            return_code = self.process.wait()

            final_elapsed = self.elapsed_time
            if return_code == 0:
                yield f"[{final_elapsed:.1f}s] ✅ {self.job_type} completed successfully (exit code: {return_code})\n"
            else:
                yield f"[{final_elapsed:.1f}s] ❌ {self.job_type} failed (exit code: {return_code})\n"

        except Exception as e:
            elapsed = self.elapsed_time
            yield f"[{elapsed:.1f}s] ❌ Error: {str(e)}\n"


class JobManager:
    # TODO: this has to exist. find a good library.
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start_job(self, command: list[str], job_type: str) -> Job:
        """Start a new job with robust process management"""
        job_id = f"{job_type}_{uuid.uuid4().hex}"

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,  # Create process group for proper cleanup
        )

        job = Job(
            job_id=job_id,
            job_type=job_type,
            command=command,
            process=process,
            started_at=time.time(),
        )

        with self._lock:
            self._jobs[job_id] = job

        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID"""
        with self._lock:
            return self._jobs.get(job_id)

    def stop_job(self, job_id: str, timeout: int = 5) -> bool:
        """Stop a job with graceful termination then force kill"""
        job = self.get_job(job_id)
        if not job or not job.is_running:
            return False

        try:
            # First try SIGTERM on the process group
            os.killpg(os.getpgid(job.process.pid), signal.SIGTERM)
            try:
                job.process.wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                # Force kill with SIGKILL
                os.killpg(os.getpgid(job.process.pid), signal.SIGKILL)
                job.process.wait()
                return True
        except Exception:
            # Fallback to regular terminate
            job.process.terminate()
            return True

    def list_jobs(self) -> list[Job]:
        """List all jobs"""
        with self._lock:
            return list(self._jobs.values())

    def cleanup_finished_jobs(self) -> None:
        """Remove finished jobs from memory"""
        with self._lock:
            finished_jobs = [
                job_id for job_id, job in self._jobs.items() if not job.is_running
            ]
            for job_id in finished_jobs:
                del self._jobs[job_id]

    def get_active_jobs(self) -> list[Job]:
        """Get list of currently active jobs"""
        return [job for job in self.list_jobs() if job.is_running]

    def stop_all_jobs(self) -> int:
        """Stop all running jobs, return count of stopped jobs"""
        jobs = self.get_active_jobs()
        count = 0
        for job in jobs:
            if self.stop_job(job.job_id):
                count += 1
        return count
