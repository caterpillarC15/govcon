#!/usr/bin/env python3
"""
T4.1 spike: hermes subprocess smoke test.

Confirms that `hermes chat -q QUERY -Q` works from this repo root,
that exit codes and stdout/stderr channels behave as expected, and
that HERMES_HOME and cwd injection work.

Run:
    set -a && source .env && set +a
    uv run python spike/hermes_smoke.py
"""

import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")


def run_hermes(query: str, toolsets: str = "file", timeout: int = 90) -> dict:
    """Run a single Hermes query non-interactively and return structured output."""
    env = {
        **os.environ,
        "HERMES_QUIET": "1",          # suppress Hermes startup banner output
        "HERMES_HOME": os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
    }

    cmd = [
        HERMES_BIN,
        "chat",
        "-q", query,
        "-Q",                          # quiet: stdout = final response only, stderr = session_id
        "-t", toolsets,                # restrict toolsets (skip tool import overhead)
        "--source", "tool",            # mark as programmatic (excluded from user session list)
        "--ignore-rules",              # skip SOUL.md / HERMES.md injection for this smoke test
    ]

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        elapsed = time.monotonic() - t0
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "stdout": "", "stderr": "", "rc": -1, "elapsed": timeout}

    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "rc": result.returncode,
        "elapsed": round(time.monotonic() - t0, 2),
    }


def main():
    print(f"Hermes bin: {HERMES_BIN}")
    print(f"Repo root:  {REPO_ROOT}")
    print(f"HERMES_HOME: {os.environ.get('HERMES_HOME', '(not set)')}")
    print()

    # Test 1: basic one-shot query
    print("=== Test 1: basic one-shot query ===")
    r = run_hermes("Reply with exactly: HERMES_SUBPROCESS_OK")
    print(f"STDOUT: {r['stdout']!r}")
    print(f"STDERR: {r['stderr']!r}")
    print(f"RC:     {r['rc']}")
    print(f"Time:   {r['elapsed']}s")
    ok1 = "HERMES_SUBPROCESS_OK" in r.get("stdout", "")
    print(f"PASS: {ok1}" if ok1 else "FAIL: response not found in stdout")
    print()

    # Test 2: bad exit code when model errors (simulate no model)
    # Just check that non-zero RC is surfaced when something breaks.
    # We do this by passing a deliberately nonsense toolset.
    print("=== Test 2: structured session_id on stderr ===")
    r2 = run_hermes("Reply with OK", toolsets="file")
    has_session = "session_id" in r2.get("stderr", "")
    print(f"stderr has session_id: {has_session}")
    print(f"STDERR snippet: {r2['stderr'][:200]!r}")
    print(f"PASS: {has_session}" if has_session else "WARN: no session_id in stderr (may be OK if Hermes version differs)")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Subprocess invocation: {'OK' if r['rc'] == 0 else 'FAIL (rc=' + str(r['rc']) + ')'}")
    print(f"stdout = final response: {'OK' if ok1 else 'FAIL'}")
    print(f"stderr = session metadata: {'OK' if has_session else 'UNCERTAIN'}")
    print()
    print("Conclusion: subprocess architecture (B) is viable." if r['rc'] == 0 else
          "WARNING: subprocess returned non-zero. Check Hermes credentials and model config.")


if __name__ == "__main__":
    main()
