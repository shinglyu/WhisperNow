# WhisperNow: Voice Transcription Tool (Linux)

A real-time voice transcription tool using faster-whisper that records audio and converts speech to text on Linux systems.

## Features

- Real-time audio recording using Linux's `sox` utility
- Speech-to-text transcription using faster-whisper
- Automatic clipboard copy of transcribed text (using `wl-copy` for Wayland)
- Voice activity detection (VAD) to filter silence
- Support for different whisper models (small.en, large-v3, distil-medium.en)

## System Requirements

- Linux operating system
- Python >= 3.12
- `sox` for audio recording:
  ```bash
  # Ubuntu/Debian
  sudo apt install sox
  # Fedora
  sudo dnf install sox
  ```
- `wl-clipboard` for Wayland clipboard support:
  ```bash
  # Ubuntu/Debian
  sudo apt install wl-clipboard
  # Fedora
  sudo dnf install wl-clipboard
  ```
- `uv` package manager

## Installation

1. Install [uv](https://github.com/astral-sh/uv)
    ```
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
1. Insall dependencies
    ```
    # Ubuntu
    sudo apt install sox wl-clipboard python3
    ```
1. Clone this repository

## Usage

Run directly with Python:
```sh
OMP_NUM_THREADS=2 uv run transcribe.py
```

Or use the terminal launcher, which will open a terminal and run the script inside. Useful for sway hotkeys.
```sh
./run_in_terminal.sh
```

## Usage Instructions

1. The program will start recording automatically
2. Press Enter to stop recording
3. Wait for transcription to complete
4. The transcribed text will be copied to clipboard automatically
5. Press Enter to record another message or 'q' + Enter to quit

## Configuration

You can change the model size in `transcribe.py`:

```python
# Available options:
model_size = "small.en"     # Faster, less accurate
# model_size = "large-v3"   # Slower, more accurate
# model_size = "distil-medium.en"  # Balanced performance
```

## Notes

- This tool is designed specifically for Linux systems running Wayland
- For X11 systems, you'll need to modify the clipboard command from `wl-copy` to `xclip`
- The transcribed audio files are temporarily stored in `/tmp/recordings/`

## License
MIT
