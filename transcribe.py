# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper"
# ]
# ///
import time
import subprocess
import os
from faster_whisper import WhisperModel

RECORDING_PATH = "/tmp/recordings"
RECORDING_FILE = os.path.join(RECORDING_PATH, "recording.wav")

# Ensure the recording directory exists
os.makedirs(RECORDING_PATH, exist_ok=True)

# model_size = "large-v3"
model_size = "small.en"
# model_size = "distil-medium.en"

# Run on GPU with FP16
# model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
start_time = time.time()
model = WhisperModel(model_size, device="cpu", compute_type="int8")
end_time = time.time()
print(f"Model loading time: {end_time - start_time:.2f} seconds")

while True:
    print("Recording... Press Ctrl+C to stop.")
    try:
        subprocess.run(
            ["sox", "-d", "-r", "16000", "-c", "1", "-b", "16", RECORDING_FILE],
            check=True,
            stderr=subprocess.DEVNULL, # Suppress "sox WARN" messages
        )
    except subprocess.CalledProcessError:
        print("Recording stopped.")
    except KeyboardInterrupt:
        print("Recording stopped.")

    print(f"Transcribing...")
    start_time = time.time()

    segments, info = model.transcribe(RECORDING_FILE, beam_size=1, language="en")

    # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    # Copy the segment texts to the clipboard
    transcription = " ".join([segment.text for segment in segments])
    transcription = transcription.strip()
    end_time = time.time()

    print(f"Model: {model_size}")
    print(f"Transcription time: {end_time - start_time:.2f} seconds")
    print(f"Transcription copied to clipboard")
    print("+" + "-- Transcription " + "-" * 33 + "+")
    print(transcription)
    print("+" + "-" * 50 + "+")
    subprocess.run(["wl-copy", transcription])
    print("")

    # Start again
    if input("Press Enter to start recording, or type 'q' + Enter to quit: ").lower() == 'q':
        break
