import json
import os
import signal
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict


class Job(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str
    job_type: str
    command: list[str]
    process: subprocess.Popen[str] | None = None
    started_at_timestamp: float | None = None

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return self.process.poll() if self.process else None

    @property
    def elapsed_time(self) -> float:
        if self.started_at_timestamp is None:
            return 0.0
        return time.time() - self.started_at_timestamp

    @property
    def started_at(self) -> str:
        if self.started_at_timestamp is None:
            return "Not started"
        return datetime.fromtimestamp(self.started_at_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @property
    def command_display(self) -> str:
        """Return command as a display string"""
        return " ".join(self.command)

    def stream_output(self) -> Iterator[str]:
        """Stream output showing last 5 lines in real-time"""
        # TODO: should this be in the job manager?
        if self.process and self.process.stdout:
            line_buffer: deque[str] = deque(maxlen=5)  # Keep last 5 lines

            for line in self.process.stdout:
                elapsed = self.elapsed_time
                line_buffer.append(f"[{elapsed:.1f}s] {line.rstrip()}")
                yield "\n".join(line_buffer)

            self.process.stdout.close()

        self.process.wait()


class GarakJob(Job):
    """Specialized Job for garak security probes with built-in result processing"""

    job_type: str = "garak_probe"
    probe_type: str
    use_guardrails: bool
    reports_dir: Path

    def _parse_garak_reports(self) -> dict[str, Any] | None:
        """Parse garak report files and extract basic statistics"""
        jsonl_files = list(self.reports_dir.glob("*.report.jsonl"))

        if not jsonl_files:
            return None

        main_report_file = jsonl_files[0]

        total_prompts = 0
        successful_attacks = 0
        failed_attacks = 0
        errors = 0

        with open(main_report_file, "r") as f:
            # JSONL format - each line is a JSON object
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line.strip())
                        # Only count final attempt entries (status 2 = final result with detector analysis)
                        if (
                            data.get("entry_type") == "attempt"
                            and data.get("status") == 2
                        ):
                            total_prompts += 1
                            # Check if the attack succeeded by looking at detector results
                            detector_results = data.get("detector_results", {})
                            if detector_results:
                                # If there are detector results, check if any detected the attack (value > 0)
                                detected = any(
                                    any(score > 0 for score in scores)
                                    for scores in detector_results.values()
                                    if isinstance(scores, list)
                                )
                                if detected:
                                    failed_attacks += 1  # Attack was detected/blocked
                                else:
                                    successful_attacks += 1  # Attack succeeded
                            else:
                                # No detector results usually means the attack wasn't detected
                                successful_attacks += 1
                    except json.JSONDecodeError:
                        errors += 1

        # Calculate success rate
        success_rate = (
            (successful_attacks / total_prompts * 100) if total_prompts > 0 else 0.0
        )

        # Calculate a basic score (lower is better for security)
        score = f"{success_rate:.1f}%"

        # Find both report files for download
        jsonl_file = main_report_file
        html_files = list(self.reports_dir.glob("*.report.html"))
        html_file = html_files[0] if html_files else None

        return {
            "total_prompts": total_prompts,
            "successful_attacks": successful_attacks,
            "failed_attacks": failed_attacks,
            "errors": errors,
            "success_rate": f"{success_rate:.1f}%",
            "score": score,
            "jsonl_file": str(jsonl_file),
            "html_file": str(html_file) if html_file else None,
        }

    def callback(self) -> dict[str, Any] | None:
        """Return a probe summary after job completion."""
        if self.exit_code == 0 and self.reports_dir and self.reports_dir.exists():
            if (stats := self._parse_garak_reports()) is not None:
                score = stats.get("score", "N/A")
                success_rate = stats.get("success_rate", "N/A")
            else:
                score = "Error"
                success_rate = "Error"

            # Return history entry
            return {
                "timestamp": self.started_at,
                "probe_type": self.probe_type,
                "guardrails": "Yes" if self.use_guardrails else "No",
                "score": score,
                "success_rate": success_rate,
                "duration": f"{self.elapsed_time:.1f}s",
            }

        return None


class JobManager:
    # TODO: this has to exist. find a good library.
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start_job(self, job: Job) -> Job:
        """Start a job with robust process management"""
        process = subprocess.Popen(
            job.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,  # Create process group for proper cleanup
        )

        # Update the job with the actual process and start time
        job.process = process
        job.started_at_timestamp = time.time()

        with self._lock:
            self._jobs[job.job_id] = job

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
