#!/usr/bin/env python3
"""
pair-whatsapp-tenant.py — Generic Headless WhatsApp Pairing Tool for Hermes Profiles

Features:
- Spawns the Baileys bridge in `--pair-json --pair-only` mode in a detached background daemon.
- Intercepts QR events and renders a high-contrast PNG image (via Python qrcode or Node.js qrcode CLI).
- Emits `MEDIA:<path>` immediately so Hermes messaging gateways deliver the QR code as a native photo.
- Gracefully handles WhatsApp's normal 408 idle timeouts (Baileys auto-reconnects and generates fresh QRs).
- On successful scan, automatically captures the tenant's phone number, configures allowlists in .env,
  and marks the profile ready for gateway activation.
- Fully non-blocking CLI: `--start` returns in ~2 seconds; `--status` provides clear diagnostic states.

Usage:
  python3 scripts/pair-whatsapp-tenant.py --profile <name> --start
  python3 scripts/pair-whatsapp-tenant.py --profile <name> --status
  python3 scripts/pair-whatsapp-tenant.py --profile <name> --stop
"""

import os
import sys
import json
import time
import signal
import subprocess
import argparse
from pathlib import Path

# Auto-reexec under Hermes venv if running under system python and qrcode is absent
HERMES_DIR = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HERMES_PYTHON = HERMES_DIR / "hermes-agent" / "venv" / "bin" / "python"
if HERMES_PYTHON.exists() and sys.executable != str(HERMES_PYTHON):
    try:
        import qrcode  # noqa: F401
    except ImportError:
        os.execv(str(HERMES_PYTHON), [str(HERMES_PYTHON)] + sys.argv)

BRIDGE_SCRIPT = HERMES_DIR / "hermes-agent" / "scripts" / "whatsapp-bridge" / "bridge.js"
NODE_QRCODE_BIN = HERMES_DIR / "hermes-agent" / "node_modules" / ".bin" / "qrcode"

def resolve_profile_paths(profile: str) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    if profile in ("default", "", None):
        base_dir = HERMES_DIR
    else:
        base_dir = HERMES_DIR / "profiles" / profile

    wa_dir = base_dir / "whatsapp"
    session_dir = wa_dir / "session"
    qr_img_path = wa_dir / f"{profile}_qr.png"
    status_file = wa_dir / "pairing_status.json"
    pid_file = wa_dir / "bridge_pair.pid"
    log_file = wa_dir / "bridge_pair.log"
    env_file = base_dir / ".env"

    return base_dir, wa_dir, session_dir, qr_img_path, status_file, pid_file, log_file, env_file

def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def stop_existing(session_dir: Path, pid_file: Path):
    if pid_file.exists():
        try:
            content = pid_file.read_text().strip()
            pids_to_kill = []
            if content.startswith("{"):
                d = json.loads(content)
                if d.get("bridge_pid"):
                    pids_to_kill.append(int(d["bridge_pid"]))
                if d.get("daemon_pid"):
                    pids_to_kill.append(int(d["daemon_pid"]))
            elif content:
                pids_to_kill.append(int(content))

            for pid in pids_to_kill:
                if is_process_running(pid):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass

            time.sleep(0.5)

            for pid in pids_to_kill:
                if is_process_running(pid):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            pid_file.unlink(missing_ok=True)

    try:
        subprocess.run(
            ["pkill", "-f", f"bridge.js.*{session_dir}"],
            capture_output=True,
            timeout=5
        )
    except Exception:
        pass

def render_qr_image(qr_data: str, target_path: Path) -> Path:
    # 1. Try Python qrcode
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(target_path))
        return target_path
    except Exception:
        pass

    # 2. Fall back to Node.js qrcode CLI
    if NODE_QRCODE_BIN.exists():
        subprocess.run(
            [str(NODE_QRCODE_BIN), "-o", str(target_path), qr_data],
            capture_output=True,
            check=True
        )
        return target_path

    raise RuntimeError("Neither python qrcode nor node qrcode available to generate QR image.")

def get_profile_mode(env_file: Path) -> str:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("WHATSAPP_MODE="):
                val = line.split("=", 1)[1].strip().strip("\"'")
                if val in ("bot", "self-chat"):
                    return val
    return "self-chat"

def update_env_file(env_file: Path, phone_number: str):
    existing_lines = []
    mode = "self-chat"
    existing_allowed = None
    if env_file.exists():
        existing_lines = env_file.read_text().splitlines()
        for line in existing_lines:
            if line.startswith("WHATSAPP_MODE="):
                val = line.split("=", 1)[1].strip().strip("\"'")
                if val in ("bot", "self-chat"):
                    mode = val
            elif line.startswith("WHATSAPP_ALLOWED_USERS="):
                existing_allowed = line.split("=", 1)[1].strip().strip("\"'")

    keys_to_set = {
        "WHATSAPP_ENABLED": "true",
        "WHATSAPP_MODE": mode,
        "WHATSAPP_HOME_CHANNEL": phone_number,
    }
    if mode == "self-chat":
        keys_to_set["WHATSAPP_ALLOWED_USERS"] = phone_number
    elif not existing_allowed:
        # In bot mode, the scanned number is the bot's; don't overwrite existing allowed users
        keys_to_set["WHATSAPP_ALLOWED_USERS"] = phone_number

    new_lines = []
    seen = set()
    for line in existing_lines:
        key = line.split("=", 1)[0].strip()
        if key in keys_to_set:
            new_lines.append(f"{key}={keys_to_set[key]}")
            seen.add(key)
        else:
            new_lines.append(line)

    for k, v in keys_to_set.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")

    import tempfile
    env_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=str(env_file.parent), delete=False, encoding="utf-8") as tf:
        tf_path = Path(tf.name)
        os.chmod(tf_path, 0o600)
        tf.write("\n".join(new_lines) + "\n")
    os.replace(tf_path, env_file)

def daemon_worker_loop(profile: str):
    import fcntl
    _, wa_dir, session_dir, qr_img_path, status_file, pid_file, log_file, env_file = resolve_profile_paths(profile)
    wa_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)

    lock_file = wa_dir / "pairing.lock"
    lock_fd = open(lock_file, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        # Another daemon worker is already active
        sys.exit(0)

    stop_existing(session_dir, pid_file)

    mode = get_profile_mode(env_file)
    log_fh = open(log_file, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            "node",
            str(BRIDGE_SCRIPT),
            "--pair-json",
            "--pair-only",
            "--session",
            str(session_dir),
            "--mode",
            mode
        ],
        cwd=str(BRIDGE_SCRIPT.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def cleanup_child(sig=None, frame=None):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        try:
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass
        if sig is not None:
            sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup_child)
    signal.signal(signal.SIGINT, cleanup_child)

    my_pid = os.getpid()
    pid_file.write_text(json.dumps({"daemon_pid": my_pid, "bridge_pid": proc.pid}))
    status_file.write_text(json.dumps({
        "status": "starting",
        "mode": mode,
        "daemon_pid": my_pid,
        "bridge_pid": proc.pid,
        "ts": time.time()
    }))

    last_qr = None
    start_time = time.time()
    max_duration_seconds = 1800  # 30 minute pairing safety window

    try:
        while time.time() - start_time < max_duration_seconds:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue

            log_fh.write(line)
            log_fh.flush()
            line = line.strip()
            if not line.startswith("{"):
                continue

            try:
                event_data = json.loads(line)
            except Exception:
                continue

            event = event_data.get("event")
            if event == "qr":
                qr_str = event_data.get("qr")
                if qr_str and qr_str != last_qr:
                    last_qr = qr_str
                    img_path = render_qr_image(qr_str, qr_img_path)
                    status_file.write_text(json.dumps({
                        "status": "waiting_for_scan",
                        "qr_image": str(img_path),
                        "daemon_pid": my_pid,
                        "bridge_pid": proc.pid,
                        "note": "QR active. Rotates every ~20s; scans link directly to WhatsApp account.",
                        "ts": time.time()
                    }))
            elif event == "disconnected":
                reason = event_data.get("reason")
                status_file.write_text(json.dumps({
                    "status": "waiting_for_scan",
                    "reason": reason,
                    "daemon_pid": my_pid,
                    "bridge_pid": proc.pid,
                    "note": f"WhatsApp rotated QR session (code {reason}); auto-reconnecting...",
                    "ts": time.time()
                }))
            elif event == "connected":
                user = event_data.get("user") or {}
                raw_id = user.get("id") or ""
                phone_digits = "".join(filter(str.isdigit, raw_id.split("@")[0].split(":")[0]))
                if phone_digits:
                    update_env_file(env_file, phone_digits)

                status_file.write_text(json.dumps({
                    "status": "connected",
                    "user": user,
                    "phone": phone_digits,
                    "ts": time.time()
                }))
                time.sleep(2)
                break
            elif event == "error":
                error_msg = event_data.get("error")
                status_file.write_text(json.dumps({
                    "status": "error",
                    "error": error_msg,
                    "reason": event_data.get("reason"),
                    "ts": time.time()
                }))
                if error_msg == "logged_out":
                    break

        cleanup_child()
    except Exception as e:
        status_file.write_text(json.dumps({"status": "exception", "error": str(e), "ts": time.time()}))
        cleanup_child()
    finally:
        log_fh.close()
        pid_file.unlink(missing_ok=True)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass

def cmd_start(profile: str):
    _, wa_dir, session_dir, qr_img_path, _, pid_file, _, _ = resolve_profile_paths(profile)
    wa_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)

    if (session_dir / "creds.json").exists():
        print(f"ALREADY_PAIRED: WhatsApp session for profile '{profile}' already exists at {session_dir / 'creds.json'}.")
        return

    if pid_file.exists():
        try:
            content = pid_file.read_text().strip()
            bridge_pid = None
            daemon_pid = None
            if content.startswith("{"):
                d = json.loads(content)
                bridge_pid = d.get("bridge_pid")
                daemon_pid = d.get("daemon_pid")
            elif content:
                bridge_pid = int(content)

            is_alive = (bridge_pid and is_process_running(bridge_pid)) or (daemon_pid and is_process_running(daemon_pid))
            if is_alive and qr_img_path.exists():
                print(f"MEDIA:{qr_img_path}")
                return
        except Exception:
            pass

    # Remove any stale QR image before starting a new worker
    qr_img_path.unlink(missing_ok=True)

    py_bin = str(HERMES_PYTHON) if HERMES_PYTHON.exists() else sys.executable
    cmd = [py_bin, str(Path(__file__).resolve()), "--profile", profile, "--internal-worker"]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    # Wait up to 8 seconds for first QR image to be generated
    t0 = time.time()
    while time.time() - t0 < 8:
        if qr_img_path.exists() and qr_img_path.stat().st_mtime >= t0 - 1:
            print(f"MEDIA:{qr_img_path}")
            return
        time.sleep(0.5)

    if qr_img_path.exists() and qr_img_path.stat().st_mtime >= t0 - 1:
        print(f"MEDIA:{qr_img_path}")
    else:
        print(f"ERROR: QR code generation timed out. Check bridge log at {wa_dir / 'bridge_pair.log'}")

def cmd_status(profile: str):
    _, wa_dir, session_dir, qr_img_path, status_file, pid_file, _, _ = resolve_profile_paths(profile)
    if (session_dir / "creds.json").exists():
        print("STATUS: PAIRED (creds.json exists)")
        if status_file.exists():
            try:
                print(status_file.read_text())
            except Exception:
                pass
        return

    if pid_file.exists():
        try:
            content = pid_file.read_text().strip()
            bridge_pid = None
            daemon_pid = None
            if content.startswith("{"):
                d = json.loads(content)
                bridge_pid = d.get("bridge_pid")
                daemon_pid = d.get("daemon_pid")
            elif content:
                bridge_pid = int(content)

            is_alive = (bridge_pid and is_process_running(bridge_pid)) or (daemon_pid and is_process_running(daemon_pid))
            if is_alive:
                print(f"STATUS: WAITING_FOR_SCAN (listener active, bridge PID {bridge_pid}, daemon PID {daemon_pid})")
                if qr_img_path.exists():
                    print(f"MEDIA:{qr_img_path}")
                print("NOTE: WhatsApp rotates QR every ~20s; listener automatically maintains fresh QR.")
                return
        except Exception:
            pass

    print("STATUS: NOT_RUNNING")

def cmd_stop(profile: str):
    _, _, session_dir, _, _, pid_file, _, _ = resolve_profile_paths(profile)
    stop_existing(session_dir, pid_file)
    print(f"Pairing bridge stopped for profile '{profile}'.")

def main():
    parser = argparse.ArgumentParser(description="Headless WhatsApp Pairing Helper for Hermes Profiles")
    parser.add_argument("--profile", "-p", default="default", help="Hermes profile name (default: 'default')")
    parser.add_argument("--start", action="store_true", help="Start pairing listener in background and emit QR MEDIA path")
    parser.add_argument("--status", action="store_true", help="Check current pairing status")
    parser.add_argument("--stop", action="store_true", help="Stop pairing bridge")
    parser.add_argument("--daemon", action="store_true", help="Alias for background start")
    parser.add_argument("--internal-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.internal_worker:
        daemon_worker_loop(args.profile)
    elif args.stop:
        cmd_stop(args.profile)
    elif args.status:
        cmd_status(args.profile)
    else:
        cmd_start(args.profile)

if __name__ == "__main__":
    main()
