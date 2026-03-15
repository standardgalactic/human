#!/usr/bin/env python3
"""
agent/agent.py — Zebra local capability-aware scheduler agent

Two operating modes:

  suggest mode (default):
    - Detects hardware, scans local corpus
    - Fetches open tasks from server
    - Ranks them by composite score
    - Presents ranked list to human operator
    - Human chooses which to claim and download

  auto mode:
    - Same sensing + ranking
    - Automatically claims tasks above score threshold
    - Downloads script bundles to a working directory
    - Polls server on schedule

Usage:
    zebra agent start           — start in suggest mode
    zebra agent start --auto    — start in auto mode
    zebra agent status          — show current claims and profile
    zebra agent scan            — re-run local corpus inspection
    zebra agent init <url>      — configure server URL
"""

import json
import os
import sys
import time
import socket
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

# Make src/ importable when run directly
_HERE = Path(__file__).resolve().parent
_SRC  = _HERE.parent
sys.path.insert(0, str(_SRC))

from agent.hardware        import detect as detect_hardware
from agent.corpus_inspector import inspect as inspect_corpus, task_affinity
from agent.scorer          import rank_tasks, format_ranked_list
from agent.config          import load as load_config, save as save_config, init_config


# ── API client (lightweight, no FastAPI dep) ──────────────────────────────────

def _api(cfg: dict, method: str, path: str, body: dict | None = None,
         timeout: int = 30) -> dict | list | None:
    import urllib.request
    import urllib.error

    url   = cfg["server"]["url"].rstrip("/") + path
    token = cfg["server"]["token"]
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", str(e))
        except Exception:
            detail = str(e)
        print(f"  API error {e.code}: {detail}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Connection error: {e}", file=sys.stderr)
        return None


def _api_get(cfg, path):   return _api(cfg, "GET",    path)
def _api_post(cfg, path, body=None): return _api(cfg, "POST", path, body)
def _api_del(cfg, path):   return _api(cfg, "DELETE", path)


# ── Sensing phase ─────────────────────────────────────────────────────────────

def run_sensing(cfg: dict, verbose: bool = False) -> tuple[dict, dict]:
    """
    Phase 1: Hardware detection.
    Phase 2: Local corpus inspection.
    Returns (hw_profile, interest_vector).
    """
    print("── Sensing hardware…")
    hw = detect_hardware()
    if verbose:
        print(f"  CPUs:        {hw.cpu_cores} cores")
        print(f"  RAM:         {hw.ram_gb} GB")
        print(f"  Disk free:   {hw.disk_free_gb} GB")
        print(f"  GPUs:        {[g.name for g in hw.gpus] or 'none'}")
        print(f"  Mic:         {hw.has_mic}  Camera: {hw.has_camera}")
        print(f"  Capabilities: {', '.join(hw.capabilities)}")

    scan_cfg = cfg.get("scan", {})
    interest_vector: dict[str, float] = {}

    if scan_cfg.get("enabled", True):
        cache_path = Path("~/.zebra/interest_cache.json").expanduser()
        cache_ttl  = scan_cfg.get("cache_ttl", 3600)

        # Use cached vector if fresh enough
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < cache_ttl:
                try:
                    interest_vector = json.loads(cache_path.read_text())
                    if verbose:
                        print(f"  Loaded cached interest vector ({int(age)}s old)")
                except Exception:
                    pass

        if not interest_vector:
            print("── Scanning local corpus…")
            scan_dirs = scan_cfg.get("directories", [])
            interest_vector = inspect_corpus(scan_dirs=scan_dirs, verbose=verbose)
            # Cache result
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(interest_vector, indent=2), encoding="utf-8")

        if verbose and interest_vector:
            print("  Interest vector:")
            for topic, w in sorted(interest_vector.items(), key=lambda x: -x[1])[:6]:
                bar = "█" * int(w * 30)
                print(f"    {topic:<22} {bar}  {w:.3f}")

    return hw, interest_vector


# ── Task fetching ─────────────────────────────────────────────────────────────

def fetch_tasks(cfg: dict, hw_profile) -> list[dict]:
    """Fetch open tasks from server, passing capability profile for filtering."""
    filters = cfg.get("filters", {})
    params  = {
        "status":   filters.get("status", "open"),
        "limit":    50,
        "sort_by":  "scarcity",
    }
    if filters.get("min_bounty"):
        params["min_bounty"] = filters["min_bounty"]
    if filters.get("projection_types"):
        params["projection_type"] = filters["projection_types"][0]

    query = "&".join(f"{k}={v}" for k, v in params.items())
    tasks = _api_get(cfg, f"/tasks?{query}")
    if tasks is None:
        return []
    if isinstance(tasks, list):
        return tasks
    return []


# ── Claim and download ────────────────────────────────────────────────────────

def claim_task(cfg: dict, task_id: str) -> dict | None:
    return _api_post(cfg, "/claims", {"task_id": task_id})


def download_bundle(cfg: dict, task_id: str, dest_dir: Path) -> Path | None:
    """Download script bundle zip into dest_dir. Returns extracted directory."""
    url   = cfg["server"]["url"].rstrip("/") + f"/tasks/{task_id}/bundle"
    token = cfg["server"]["token"]

    import urllib.request
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    zip_path = dest_dir / f"task_{task_id}.zip"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_path.write_bytes(resp.read())
    except Exception as e:
        print(f"  Download failed: {e}", file=sys.stderr)
        return None

    extract_dir = dest_dir / f"task_{task_id}"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    zip_path.unlink()
    print(f"  Bundle extracted → {extract_dir}")
    return extract_dir


def register_node(cfg: dict, hw_profile) -> None:
    """Register or update this node's capability profile with the server."""
    payload = {
        "node_name":    cfg["identity"].get("node_name") or socket.gethostname(),
        "capabilities": hw_profile.to_api_payload(),
    }
    _api_post(cfg, "/agent/register", payload)


# ── Suggest mode ──────────────────────────────────────────────────────────────

def suggest_mode(cfg: dict, verbose: bool = False, reasons: bool = False) -> None:
    """
    Interactive suggest loop.
    Shows ranked tasks and lets the user pick one to claim and download.
    """
    hw, interest_vector = run_sensing(cfg, verbose=verbose)

    print("\n── Fetching tasks from server…")
    raw_tasks = fetch_tasks(cfg, hw)
    if not raw_tasks:
        print("  No open tasks found. Check server connection or filters.")
        return

    print(f"  {len(raw_tasks)} tasks retrieved. Ranking…\n")
    ranked = rank_tasks(
        raw_tasks,
        capabilities    = hw.capabilities,
        interest_vector = interest_vector,
        ram_gb          = hw.ram_gb,
        cpu_cores       = hw.cpu_cores,
        has_gpu         = hw.has_gpu(),
        top_k           = 10,
    )

    if not ranked:
        print("  No tasks match this node's capabilities.")
        return

    print("── Ranked tasks for this node:\n")
    print(format_ranked_list(ranked, show_reasons=reasons))

    # Interactive selection
    if not sys.stdin.isatty():
        return

    while True:
        choice = input("  Claim task number (1-10), or q to quit: ").strip()
        if choice.lower() == "q":
            break
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(ranked)):
                print("  Invalid number.")
                continue
        except ValueError:
            print("  Enter a number or q.")
            continue

        ts = ranked[idx]
        print(f"\n  Claiming: {ts.label}")
        claim = claim_task(cfg, ts.task_id)
        if not claim:
            print("  Claim failed.")
            continue

        print(f"  Claimed. Expires: {claim.get('expires_at', '72h')}")

        work_dir = Path("~/.zebra/work").expanduser()
        work_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir = download_bundle(cfg, ts.task_id, work_dir)
        if bundle_dir:
            brief = bundle_dir / f"task_{ts.task_id}" / "brief.md"
            if brief.exists():
                print(f"\n  Brief:\n{'─'*60}")
                print(brief.read_text()[:1000])
                print("─" * 60)
            print(f"\n  Work directory: {bundle_dir}")
            print("  When done, upload via: zebra agent upload <task_id> <file>")
        break


# ── Auto mode ─────────────────────────────────────────────────────────────────

def auto_mode(cfg: dict, verbose: bool = False) -> None:
    """
    Polling loop: sense, fetch, rank, auto-claim top tasks above threshold.
    """
    threshold   = cfg["agent"].get("auto_claim_min_score", 0.6)
    max_claims  = cfg["agent"].get("max_claims", 3)
    interval    = cfg["agent"].get("poll_interval", 300)

    print(f"── Auto mode  (threshold={threshold}, max_claims={max_claims}, "
          f"poll={interval}s)")
    print("   Press Ctrl-C to stop.\n")

    try:
        while True:
            hw, interest_vector = run_sensing(cfg, verbose=verbose)

            # Check active claim count
            mine = _api_get(cfg, "/claims/mine") or []
            active_count = len(mine)
            if active_count >= max_claims:
                print(f"  {active_count} active claims — at limit. Waiting {interval}s.")
                time.sleep(interval)
                continue

            raw_tasks = fetch_tasks(cfg, hw)
            ranked = rank_tasks(
                raw_tasks,
                capabilities    = hw.capabilities,
                interest_vector = interest_vector,
                ram_gb          = hw.ram_gb,
                cpu_cores       = hw.cpu_cores,
                has_gpu         = hw.has_gpu(),
                top_k           = 5,
            )

            claimed_this_round = 0
            for ts in ranked:
                if ts.total < threshold:
                    break
                if active_count + claimed_this_round >= max_claims:
                    break
                print(f"  Auto-claiming [{ts.total:.3f}]: {ts.label}")
                claim = claim_task(cfg, ts.task_id)
                if claim:
                    work_dir = Path("~/.zebra/work").expanduser()
                    work_dir.mkdir(parents=True, exist_ok=True)
                    download_bundle(cfg, ts.task_id, work_dir)
                    claimed_this_round += 1

            if claimed_this_round:
                print(f"  Claimed {claimed_this_round} task(s). Next poll in {interval}s.")
            else:
                print(f"  No tasks above threshold. Next poll in {interval}s.")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n  Agent stopped.")


# ── Status command ────────────────────────────────────────────────────────────

def show_status(cfg: dict) -> None:
    print("── Agent status\n")
    hw = detect_hardware()
    print(f"  Node:         {cfg['identity'].get('node_name') or socket.gethostname()}")
    print(f"  Server:       {cfg['server']['url']}")
    print(f"  Mode:         {cfg['agent']['mode']}")
    print(f"  Capabilities: {', '.join(hw.capabilities)}")
    print()

    mine = _api_get(cfg, "/claims/mine") or []
    print(f"  Active claims: {len(mine)}")
    for c in mine:
        print(f"    {c['task_id'][:12]}…  expires {c.get('expires_at','?')[:16]}")
    print()

    # Show cached interest vector if present
    cache_path = Path("~/.zebra/interest_cache.json").expanduser()
    if cache_path.exists():
        iv = json.loads(cache_path.read_text())
        print("  Interest vector (cached):")
        for topic, w in sorted(iv.items(), key=lambda x: -x[1])[:5]:
            bar = "█" * int(w * 25)
            print(f"    {topic:<22} {bar}  {w:.3f}")


# ── Upload command ────────────────────────────────────────────────────────────

def upload_submission(cfg: dict, task_id: str, file_path: str,
                      branch_label: str | None = None, notes: str | None = None) -> None:
    """Upload a completed media file as a submission."""
    import urllib.request, urllib.parse

    # First, find the active claim for this task
    mine = _api_get(cfg, "/claims/mine") or []
    claim = next((c for c in mine if c["task_id"] == task_id), None)
    if not claim:
        print(f"  No active claim found for task {task_id}")
        return

    path = Path(file_path)
    if not path.exists():
        print(f"  File not found: {file_path}")
        return

    # Multipart upload
    token = cfg["server"]["token"]
    url   = cfg["server"]["url"].rstrip("/") + "/submissions"

    import io
    boundary = "ZebraAgentBoundary42"
    body_parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"claim_id\"\r\n\r\n{claim['id']}",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"task_id\"\r\n\r\n{task_id}",
    ]
    if branch_label:
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"branch_label\"\r\n\r\n{branch_label}"
        )
    if notes:
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"notes\"\r\n\r\n{notes}"
        )

    body_bytes = "\r\n".join(body_parts).encode()

    # File part
    file_bytes  = path.read_bytes()
    file_header = (f"--{boundary}\r\n"
                   f"Content-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
                   f"Content-Type: application/octet-stream\r\n\r\n").encode()
    close_bytes = f"\r\n--{boundary}--\r\n".encode()

    full_body = body_bytes + b"\r\n" + file_header + file_bytes + close_bytes

    headers: dict[str, str] = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=full_body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            print(f"  Uploaded: {result.get('id')}")
            print(f"  Status:   {result.get('status')}")
    except Exception as e:
        print(f"  Upload failed: {e}", file=sys.stderr)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(
        prog="zebra agent",
        description="Zebra capability-aware task scheduler agent",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # start
    p_start = sub.add_parser("start", help="start the agent")
    p_start.add_argument("--auto",     action="store_true", help="auto-claim mode")
    p_start.add_argument("--verbose",  action="store_true")
    p_start.add_argument("--reasons",  action="store_true", help="show capability reasons")

    # status
    sub.add_parser("status", help="show agent status and active claims")

    # scan
    p_scan = sub.add_parser("scan", help="re-run local corpus inspection")
    p_scan.add_argument("--verbose", action="store_true")

    # init
    p_init = sub.add_parser("init", help="configure server URL")
    p_init.add_argument("url",      help="ZebraTube API URL")
    p_init.add_argument("--token",  default=None, help="auth token")
    p_init.add_argument("--user",   default=None, help="username")

    # upload
    p_up = sub.add_parser("upload", help="upload a completed submission")
    p_up.add_argument("task_id",  help="task ID")
    p_up.add_argument("file",     help="path to media file")
    p_up.add_argument("--branch", default=None, help="branch label")
    p_up.add_argument("--notes",  default=None)

    args = ap.parse_args(argv)
    cfg  = load_config()

    if args.cmd == "init":
        cfg = init_config(args.url, username=args.user, token=args.token)
        print(f"  Config saved to ~/.zebra/agent.yaml")
        print(f"  Server: {args.url}")

    elif args.cmd == "start":
        mode = "auto" if args.auto else cfg["agent"].get("mode", "suggest")
        if mode == "auto":
            auto_mode(cfg, verbose=args.verbose)
        else:
            suggest_mode(cfg, verbose=args.verbose, reasons=args.reasons)

    elif args.cmd == "status":
        show_status(cfg)

    elif args.cmd == "scan":
        scan_cfg = cfg.get("scan", {})
        # Force fresh scan by deleting cache
        cache = Path("~/.zebra/interest_cache.json").expanduser()
        if cache.exists():
            cache.unlink()
        iv = inspect_corpus(scan_dirs=scan_cfg.get("directories"), verbose=True)
        print("\nInterest vector:")
        for topic, w in sorted(iv.items(), key=lambda x: -x[1]):
            bar = "█" * int(w * 30)
            print(f"  {topic:<22} {bar}  {w:.3f}")
        # Re-cache
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(iv, indent=2))

    elif args.cmd == "upload":
        upload_submission(cfg, args.task_id, args.file,
                          branch_label=args.branch, notes=args.notes)


if __name__ == "__main__":
    main()
