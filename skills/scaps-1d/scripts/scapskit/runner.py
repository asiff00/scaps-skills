"""Run SCAPS scripts headless (blocking) and collect their output files."""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from . import processes
from .config import Settings
from .parsing import LogEntry, parse_error_log

ENCODING = "cp1252"
ERROR_LOG = "SCAPSErrorLogFile.log"
LOCK_FILE = ".scaps-run.lock"


@dataclass
class RunOutcome:
    run_id: str
    directory: Path
    files: dict[str, Path] = field(default_factory=dict)
    errors: list[LogEntry] = field(default_factory=list)
    timed_out: bool = False
    seconds: float = 0.0


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


@contextlib.contextmanager
def installation_lock(home: Path):
    """Exclusive lock on a SCAPS installation, shared with scaps-mcp and other processes."""
    with open(home / LOCK_FILE, "a+") as handle:
        _lock(handle, True)
        try:
            yield
        finally:
            _lock(handle, False)


def _lock(handle, acquire: bool) -> None:
    if sys.platform != "win32":
        fcntl.flock(handle, fcntl.LOCK_EX if acquire else fcntl.LOCK_UN)
        return
    handle.seek(0)
    if not acquire:
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    while True:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            return
        except OSError:
            continue


def run(settings: Settings, script: str, outputs: list[str], timeout: float | None = None) -> RunOutcome:
    home = settings.home
    run_id = new_run_id()
    directory = settings.runs_dir / run_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.script").write_text(script, encoding=ENCODING, newline="")
    script_path = home / "script" / f"skill_{run_id}.script"
    outcome = RunOutcome(run_id, directory)

    env = dict(os.environ)
    if settings.native:
        command = [str(settings.exe), script_path.name]
    else:
        env.update(WINEPREFIX=str(settings.wineprefix), WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=")
        command = [settings.wine, settings.exe.name, script_path.name]
        if settings.xvfb_run:
            command = [settings.xvfb_run, "-a", *command]

    with installation_lock(home):
        processes.stop_stale(home, settings.exe.name)
        (home / ERROR_LOG).unlink(missing_ok=True)
        for name in outputs:
            (home / "results" / name).unlink(missing_ok=True)
        script_path.write_text(script, encoding=ENCODING, newline="")
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=home,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=not settings.native,
        )
        processes.remember(home, process.pid)
        try:
            process.wait(timeout=timeout or settings.timeout)
        except subprocess.TimeoutExpired:
            outcome.timed_out = True
        finally:
            if process.poll() is None:
                if settings.native:
                    process.kill()
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            processes.forget(home)
            if not settings.native and settings.wineserver:
                subprocess.run([settings.wineserver, "-k"], env=env, capture_output=True, check=False)
            outcome.seconds = round(time.monotonic() - started, 2)
            script_path.unlink(missing_ok=True)

        log = home / ERROR_LOG
        if log.exists():
            text = log.read_text(encoding=ENCODING, errors="replace")
            (directory / ERROR_LOG).write_text(text, encoding=ENCODING)
            outcome.errors = parse_error_log(text)
        for name in outputs:
            source = home / "results" / name
            if source.exists():
                outcome.files[name] = Path(shutil.move(source, directory / name))
    return outcome
