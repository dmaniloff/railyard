import os
import signal
import subprocess
import time
from typing import Any, Dict, List, Iterator


def run_garak_probe(
    cmd: List[str], probe_id: str, running_probes: Dict[str, Any]
) -> None:
    """Execute a garak probe command with robust process management"""
    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,
        )

        try:
            # Stream output line by line for real-time updates
            output_lines = []
            start_time = time.time()

            for line in process.stdout:  # type: ignore
                output_lines.append(line)
                # Update running status with current output
                running_probes[probe_id] = {
                    "status": "running",
                    "stdout": "".join(output_lines),
                    "stderr": "",
                    "returncode": None,
                }

                # Check timeout
                if time.time() - start_time > 300:
                    raise subprocess.TimeoutExpired(cmd, 300)

            process.stdout.close()
            process.wait()

            # Final completed status
            running_probes[probe_id] = {
                "status": "completed",
                "stdout": "".join(output_lines),
                "stderr": "",
                "returncode": process.returncode,
            }
        except subprocess.TimeoutExpired:
            # Kill the entire process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Process still running, kill with SIGKILL
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

            running_probes[probe_id] = {
                "status": "timeout",
                "stdout": "",
                "stderr": "Probe timed out after 5 minutes",
                "returncode": -1,
            }

    except Exception as e:
        running_probes[probe_id] = {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }
    finally:
        if process:
            try:
                process.terminate()
            except Exception:
                pass


def stream_garak_probe(cmd: List[str]) -> Iterator[str]:
    """Execute a garak probe command and yield output lines in real-time"""
    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,
        )

        start_time = time.time()
        
        if process.stdout:
            for line in process.stdout:
                elapsed = time.time() - start_time
                yield f"[{elapsed:.1f}s] {line}"
                
                # Check timeout
                if elapsed > 300:  # 5 minutes
                    yield f"[{elapsed:.1f}s] ⚠️ Probe timed out after 5 minutes\n"
                    break
        
        process.stdout.close() if process.stdout else None
        return_code = process.wait()
        
        final_elapsed = time.time() - start_time
        if return_code == 0:
            yield f"[{final_elapsed:.1f}s] ✅ Probe completed successfully (exit code: {return_code})\n"
        else:
            yield f"[{final_elapsed:.1f}s] ❌ Probe failed (exit code: {return_code})\n"
            
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        yield f"[{elapsed:.1f}s] ❌ Error: {str(e)}\n"
        
    finally:
        if process:
            try:
                # Kill process group if still running
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait()
            except Exception:
                pass


def run_guidellm_benchmark(
    cmd: List[str], benchmark_id: str, running_benchmarks: Dict[str, Any]
) -> None:
    """Execute a guidellm benchmark command with robust process management"""
    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,
        )

        try:
            stdout, stderr = process.communicate(timeout=600)
            running_benchmarks[benchmark_id] = {
                "status": "completed",
                "stdout": stdout,
                "stderr": stderr or "",
                "returncode": process.returncode,
            }
        except subprocess.TimeoutExpired:
            # Kill the entire process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Process still running, kill with SIGKILL
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

            running_benchmarks[benchmark_id] = {
                "status": "timeout",
                "stdout": "",
                "stderr": "Benchmark timed out after 10 minutes",
                "returncode": -1,
            }

    except Exception as e:
        running_benchmarks[benchmark_id] = {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }
    finally:
        if process:
            try:
                process.terminate()
            except Exception:
                pass
