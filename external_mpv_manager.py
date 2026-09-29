import socket
import json
import subprocess
import threading
import time
import platform
import os
import urllib.parse
import sys
import argparse

# --- Configuration ---
KODI_LISTENER_PORT = 65432
STABLE_FRAMES_DEBOUNCE = 75  # Number of matching frames required to register a change

parser = argparse.ArgumentParser()
parser.add_argument(
    "--headless", action="store_true", help="Run without a graphical interface"
)
parser.add_argument(
    "--mount-paths", nargs="+", required=True, help="List of mount paths"
)
parser.add_argument(
    "--split-paths", nargs="+", required=True, help="List of path strings to split on"
)

args = parser.parse_args()

IS_HEADLESS = args.headless
MOUNT_PATHS = args.mount_paths
SPLIT_PATHS = args.split_paths

if platform.system() == "Windows":
    MPV_IPC_PATH = r"\\.\pipe\mpvget"
else:
    MPV_IPC_PATH = "/tmp/mpv-socket"


class MPVManager:
    def __init__(self):
        self.proc = None
        self.current_file = None
        self.last_crop = None

        # --- Debouncing State Variables ---
        self.candidate_crop = None
        self.frame_match_counter = 0

        # Cache properties initialized safely
        self.cached_mount_path = None
        self.cached_split_prefix = None

        # --- NEW: Inactivity monitoring tracking ---
        self.last_seen = time.time()
        threading.Thread(target=self.inactivity_watchdog, daemon=True).start()

    def inactivity_watchdog(self):
        """Background loop checking if Android stopped communicating."""
        while True:
            time.sleep(5)  # Wake up every 5 seconds to inspect state

            # Check if MPV is actually running and playing a file right now
            if self.proc and self.proc.poll() is None and self.current_file is not None:
                elapsed = time.time() - self.last_seen
                if elapsed > 120:
                    print(
                        f"No communication for {int(elapsed)}s. Stopping MPV playback."
                    )
                    # Send a stop signal to MPV via IPC
                    if self.send_ipc(["stop"]):
                        self.current_file = (
                            None  # Reset tracking state so it can re-trigger later
                        )

    def start_mpv(self):
        """Spawns MPV if it is not already running."""
        if self.proc and self.proc.poll() is None:
            return

        print(f"Starting MPV (Headless={IS_HEADLESS}) with IPC and CropDetect...")
        cmd = [
            "mpv",
            f"--input-ipc-server={MPV_IPC_PATH}",
            # Added dummy crop filter container to keep video scaling 1:1 during calculation
            "--vf=cropdetect=limit=0.1:reset=55,crop=w=iw:h=ih",
            "--msg-level=all=v",
            "--idle=yes",
            "--terminal=yes",
            "--ao=null",
        ]

        if IS_HEADLESS:
            if platform.system() == "Linux":
                cmd.extend(["--vo=null", "--hwdec=yes", "--force-window=no"])
            elif platform.system() == "Windows":
                cmd.extend(["--vo=null", "--hwdec=auto-copy", "--force-window=no"])
        else:
            cmd.extend(["--ontop=no", "--hwdec=auto-copy"])

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",  # Forces Python to decode using UTF-8 matching mpv on Windows
            errors="replace",  # prevent the above from causing issues when decoding chances upon weird chars
        )

        threading.Thread(target=self.consume_output, daemon=True).start()
        time.sleep(2)

    def consume_output(self):
        """Reads MPV's console output line-by-line using debouncing logic."""
        if not self.proc.stdout:
            return
        for line in self.proc.stdout:
            print(f"{line}", end="")
            if "crop=" in line:
                try:
                    crop_str = line.split("crop=")[1].split()[0]

                    # If this matches our current candidate, increment the match counter
                    if crop_str == self.candidate_crop:
                        self.frame_match_counter += 1
                    else:
                        # Value shifted; switch candidates and reset the stability counter
                        self.candidate_crop = crop_str
                        self.frame_match_counter = 0

                    # Only update Kodi if the candidate value is completely stable
                    if self.frame_match_counter >= STABLE_FRAMES_DEBOUNCE:
                        if self.candidate_crop != self.last_crop:
                            self.last_crop = self.candidate_crop
                            print(
                                f"\n[DEBOUNCED] NEW CROP LOCKED IN: {self.last_crop}\n"
                            )
                        # Reset counter after logging a change to avoid constant assignment triggers
                        self.frame_match_counter = 0

                except (IndexError, ValueError):
                    continue

    def send_ipc(self, cmd_list, retries=10):
        """Sends commands to MPV, retrying if the socket isn't ready yet."""
        payload = json.dumps({"command": cmd_list}) + "\n"

        for i in range(retries):
            try:
                if platform.system() == "Windows":
                    with open(MPV_IPC_PATH, "w") as f:
                        f.write(payload)
                else:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.connect(MPV_IPC_PATH)
                        s.sendall(payload.encode())
                return True
            except (ConnectionRefusedError, FileNotFoundError, BrokenPipeError):
                time.sleep(0.7)
        return False

    def sync(self, filepath, timestamp):
        """Logic to switch files and seek to Kodi's time."""
        # --- NEW: Keep updating timestamp any time sync is invoked ---
        self.last_seen = time.time()

        self.start_mpv()

        decoded_path = urllib.parse.unquote(filepath)

        if self.cached_mount_path and self.cached_split_prefix:
            relative_path = decoded_path.split(self.cached_split_prefix)[1]
            local_path = os.path.join(self.cached_mount_path, relative_path)
        else:
            local_path = None
            for prefix in SPLIT_PATHS:
                if prefix in decoded_path:
                    relative_path = decoded_path.split(prefix)[1]
                    for mount_path in MOUNT_PATHS:
                        potential_path = os.path.join(mount_path, relative_path)
                        if os.path.exists(potential_path):
                            self.cached_split_prefix = prefix
                            self.cached_mount_path = mount_path
                            local_path = potential_path
                            break
                    if local_path:
                        break

            if not local_path:
                print(
                    "Warning: No matching prefix/mount found on disk. Using decoded path."
                )
                local_path = decoded_path

        print(f"Mapped Path: {local_path}")

        if local_path != self.current_file:
            print(f"Sending loadfile: {local_path}")
            if self.send_ipc(["loadfile", local_path, "replace"]):
                self.current_file = local_path
                # Reset debouncer states for the new video file
                self.candidate_crop = None
                self.frame_match_counter = 0
                self.last_crop = None
                time.sleep(1)

        self.send_ipc(["seek", timestamp, "absolute"])


def main():
    manager = MPVManager()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", KODI_LISTENER_PORT))
    server.listen(5)
    print(f"Manager listening on port {KODI_LISTENER_PORT} (Headless={IS_HEADLESS})...")

    while True:
        conn, addr = server.accept()
        try:
            data = conn.recv(4096)
            if data:
                msg = json.loads(data.decode())
                manager.sync(msg["file"], msg["time"])

                if manager.last_crop:
                    response = json.dumps({"crop": manager.last_crop})
                    conn.sendall(response.encode())
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
