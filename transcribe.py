# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper"
# ]
# ///
import time
import subprocess
import os
import threading
import signal
from faster_whisper import WhisperModel


RECORDING_PATH = "/tmp/recordings"
RECORDING_FILE = os.path.join(RECORDING_PATH, "recording.wav")

# Ensure the recording directory exists
os.makedirs(RECORDING_PATH, exist_ok=True)

# model_size = "large-v3"
model_size = "small.en"
# model_size = "distil-medium.en"

recording_thread = None
sox_process = None  # Store the subprocess object

def red(text):
    return f"\033[91m{text}\033[0m"
def green(text):
    return f"\033[92m{text}\033[0m"
def yellow(text):
    return f"\033[93m{text}\033[0m"

def record_audio():
    global sox_process
    print(red("Recording..."))
    try:
        sox_process = subprocess.Popen(
            ["sox", "-d", "-r", "16000", "-c", "1", "-b", "16", RECORDING_FILE],
            stderr=subprocess.DEVNULL,  # Suppress "sox WARN" messages
        )
        sox_process.wait() # Wait for the process to finish
    except subprocess.CalledProcessError:
        print("Recording stopped.")
    except KeyboardInterrupt:
        print("Recording stopped.")

# Main loop
while True:
    if recording_thread is None or not recording_thread.is_alive():
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()

    # Load the model *after* starting the recording thread
    if 'model' not in locals():
        print(f"Loading model {model_size}...")
        start_time = time.time()
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        end_time = time.time()
        print(f"Model loading time: {end_time - start_time:.2f} seconds")

    if input(red("Press Enter to stop recording")):
        break

    if recording_thread and recording_thread.is_alive():
        print("Stopping recording...")
        try:
            # Terminate the sox process gracefully
            if sox_process:
                sox_process.terminate()
                sox_process.wait()
            recording_thread.join()
        except Exception as e:
            print(f"Error stopping recording: {e}")

    print(f"Transcribing...")
    start_time = time.time()

    segments, info = model.transcribe(
        RECORDING_FILE,
        beam_size=2,
        language="en",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)  # Remove silence that is longer than 500ms
    )

    transcription = " ".join([segment.text.strip() for segment in segments])
    transcription = transcription.strip()

    end_time = time.time()

    print(f"Transcription time: {end_time - start_time:.2f} seconds")
    print(green(f"+-- Transcription {'-' * 33}+"))
    print(transcription)
    print(green(f"+{'-' * 50}+"))
    subprocess.run(["wl-copy", transcription])
    print(f"Transcription copied to clipboard")
    print("")

    if input(yellow("Press Enter to record another message, or 'q' + Enter to quit: ")).lower() == 'q':
        break
