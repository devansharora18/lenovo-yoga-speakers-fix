#!/usr/bin/env python3

"""Tray widget for the Lenovo Yoga speakers-after-sleep fix.

Monitors the HDA codec speaker pin and re-applies the fix automatically
after suspend/resume, restoring your volume afterwards.

Works without embedding a password if you set up the passwordless sudo
rule in speakers-fix.sudoers (recommended). Otherwise set SUDO_PASSWORD.
"""

import pystray
import subprocess
import threading
import time
import re
import os
from PIL import Image, ImageDraw

SUDO_PASSWORD = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HWDEV = "/dev/snd/hwC1D0"
SPEAKERS_SH = os.path.join(BASE_DIR, "speakers.sh")
PIN_EXPECTED = 0x40

auto_fix = True


def notify(title, message):
    try:
        subprocess.run(["notify-send", title, message, "--icon=audio-speakers", "-t", "5000"])
    except Exception:
        pass


def sudo_base():
    """Return (base_args, stdin) for a sudo invocation."""
    if SUDO_PASSWORD:
        return ["sudo", "-S", "-p", ""], SUDO_PASSWORD + "\n"
    return ["sudo", "-n"], None


def run_verb(nid, verb):
    try:
        base, stdin = sudo_base()
        r = subprocess.run(
            base + ["hda-verb", HWDEV, str(nid), verb, "0"],
            input=stdin, text=True, capture_output=True, timeout=10,
        )
        m = re.search(r"value = 0x([0-9a-fA-F]+)", r.stdout)
        return int(m.group(1), 16) if m else None
    except Exception:
        return None


def get_pin():
    return run_verb(0x17, "GET_PIN_WIDGET_CONTROL")


def get_speaker_volume():
    try:
        r = subprocess.run(["amixer", "-c", "1", "sget", "Speaker"], text=True, capture_output=True)
        m = re.search(r"Playback (\d+)", r.stdout)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def set_speaker_volume(val):
    if val is None:
        return
    subprocess.run(["amixer", "-c", "1", "sset", "Speaker", str(val)], capture_output=True)


def apply_script(script):
    label = os.path.basename(script)
    if not os.path.exists(script):
        notify("Speakers", f"{label} not found")
        return False
    try:
        base, stdin = sudo_base()
        result = subprocess.run(
            base + ["bash", script],
            input=stdin, text=True, capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            notify("Speakers", f"{label} applied")
            return True
        err = (result.stderr or "").strip().splitlines()
        reason = err[-1] if err else f"exit code {result.returncode}"
        if "password" in reason.lower() and not SUDO_PASSWORD:
            reason += " — set up speakers-fix.sudoers or set SUDO_PASSWORD"
        notify("Speakers", f"{label} failed: {reason}")
        return False
    except Exception as e:
        notify("Speakers", f"{label} error: {e}")
        return False


def fix_with_volume_restore():
    vol = get_speaker_volume()
    ok = apply_script(SPEAKERS_SH)
    if ok and vol is not None:
        set_speaker_volume(vol)


def monitor():
    global auto_fix
    while True:
        time.sleep(3)
        if not auto_fix:
            continue
        pin = get_pin()
        if pin is not None and pin != PIN_EXPECTED:
            notify("Speakers", "Speaker config reverted — re-applying")
            fix_with_volume_restore()


def create_image():
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([2, 2, 62, 62], radius=16, fill="#2563eb")
    draw.polygon([(18, 26), (26, 26), (36, 18), (36, 46), (26, 38), (18, 38)], fill="white")
    draw.arc([32, 20, 52, 44], start=300, end=60, fill="white", width=4)
    draw.arc([34, 26, 44, 38], start=300, end=60, fill="white", width=4)
    return image


def toggle_auto_fix():
    global auto_fix
    auto_fix = not auto_fix
    notify("Speakers", f"Auto-fix {'ON' if auto_fix else 'OFF'}")


def run_tray():
    image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem("Run speakers.sh", fix_with_volume_restore),
        pystray.MenuItem(lambda item: "Auto-fix: ON" if auto_fix else "Auto-fix: OFF", toggle_auto_fix),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda: tray.stop()),
    )
    tray = pystray.Icon("Speakers", image, "Speakers", menu)
    threading.Thread(target=monitor, daemon=True).start()
    tray.run()


if __name__ == "__main__":
    run_tray()