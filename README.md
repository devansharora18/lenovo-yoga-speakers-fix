# Lenovo Yoga Subwoofer Fix

Fixes the built-in **subwoofer** on Lenovo Yoga laptops (and similar HDA-Intel
machines) that **doesn't work in Linux**.

On these laptops the HDA codec has a separate amplifier/output for the
subwoofer that Linux never enables by default, so the subwoofer stays silent
(or very faint) while the rest of the speakers work. This repo enables that
output with raw `hda-verb` codec commands. The same output can also get reset
after a suspend/resume, which is why a small tray widget is included to
re-apply the fix automatically.

This repo provides:

- **`speakers.sh`** — the one-liner shell fix (raw `hda-verb` commands).
- **`speaker-tray.py`** — a small system tray widget that **auto-detects** the
  subwoofer output reverting after resume and re-applies the fix for you,
  restoring your volume afterwards.
- **`speakers-fix.sudoers`** — passwordless sudo rule so the widget needs no
  password.
- **`speaker-tray.desktop`** — autostart entry so the widget runs at login.

## What the fix does

`speakers.sh` issues three `hda-verb` commands to the HDA codec to enable and
drive the subwoofer output:

```sh
sudo hda-verb /dev/snd/hwC1D0 0x17 SET_PIN_WIDGET_CONTROL 0x40   # enable subwoofer output pin
sudo hda-verb /dev/snd/hwC1D0 0x17 SET_AMP_GAIN_MUTE 0xb000      # unmute the subwoofer amp
sudo hda-verb /dev/snd/hwC1D0 0x02 SET_AMP_GAIN_MUTE 0xb057      # set subwoofer output gain
```

Run it once and the subwoofer should kick in:

```sh
./speakers.sh
```

If your device node or codec nodes differ, see [Troubleshooting](#troubleshooting).

## Requirements

- `alsa-tools` (provides `hda-verb`) — Fedora: `sudo dnf install alsa-tools`
- Python 3 with `pystray` and `Pillow`
  - `pip install pystray Pillow` (or `sudo dnf install python3-pystray python3-pillow`)
- `notify-send` (usually present with a desktop environment)
- `amixer` (part of `alsa-utils`)

## Installation

```sh
git clone https://github.com/devansharora18/lenovo-yoga-speakers-fix.git
cd lenovo-yoga-speakers-fix
chmod +x speakers.sh speaker-tray.py
```

### 1. Give sudo access (choose one)

**Recommended — passwordless sudo (edit the sudoers file first):**

Open `speakers-fix.sudoers`, replace `<USER>` with your username and `<PATH>`
with the absolute path to this repo's `speakers.sh`, then:

```sh
sudo install -m 440 speakers-fix.sudoers /etc/sudoers.d/speakers-fix
```

Now the widget runs with no password prompt.

**Alternative — hardcode your password:**

Set `SUDO_PASSWORD = "your-password"` at the top of `speaker-tray.py`.
(Not recommended for sharing; a password in a script is visible to anyone
who can read the file.)

### 2. Autostart (optional)

Copy the desktop entry to your autostart folder and fix the path:

```sh
sed -e "s#/PATH/TO#$(pwd)#" speaker-tray.desktop > ~/.config/autostart/speaker-tray.desktop
```

Reboot, or launch the widget manually now:

```sh
python3 speaker-tray.py
```

## Usage

From the tray icon you can:

- **Run speakers.sh** — enable the subwoofer immediately (restores your volume).
- **Auto-fix: ON/OFF** — toggle automatic monitoring (default ON).

With auto-fix ON, the widget checks the subwoofer output pin every 3 seconds.
When the codec reverts after resume, it re-applies the fix and restores your
volume level automatically.

## How it works

`speaker-tray.py` reads the subwoofer output pin widget control via
`hda-verb`:

```sh
hda-verb /dev/snd/hwC1D0 0x17 GET_PIN_WIDGET_CONTROL 0
```

When this returns anything other than `0x40` (output enabled), the widget
knows the output has reverted and re-runs `speakers.sh`. It saves your
`Speaker` mixer level first and restores it after, so you never land on
maxed-out volume.

## Troubleshooting

**I ran `./speakers.sh` and the subwoofer is still silent.**

The gain may be too low or the wrong output was enabled. Try raising the gain
value `0x57` in the last line (up to `0x7f`), or check your card/codec nodes
below.

**The device node `hwC1D0` is wrong for my machine.**

`hwC1D0` is card 1. To find the right card, list your sound cards:

```sh
cat /proc/asound/cards
```

Find the HDA-Intel card (not your USB/HDMI device), then use its `hwC<card>D0`
path in `speakers.sh` and `speaker-tray.py`. You can check the codec nodes in:

```sh
cat /proc/asound/card<card>/codec#0
```

Look for the `Pin Complex` wired to your subwoofer/speaker — that NID replaces
`0x17`, and the `Audio Output` that feeds it replaces `0x02`.

**The fix applies but stops working after suspend.**

Your resume may also reset the amp mute, not just the pin. Toggle `Auto-fix`
off and re-apply manually, or open an issue with your
`cat /proc/asound/card*/codec#0` output.

**I don't want the volume restored / it changes the wrong control.**

The widget restores the `Speaker` mixer on card 1. Edit the card number and
control name in `get_speaker_volume()` / `set_speaker_volume()` to match your
setup.

## License

Free to use, modify and share.