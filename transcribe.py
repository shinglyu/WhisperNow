# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper",
#     "pyaudio",
#     "speechrecognition",
# ]
# ///
import sys
import select
import time
import subprocess
import os
import threading
import signal
import speech_recognition as sr
import io
from queue import Queue
from tempfile import NamedTemporaryFile
from faster_whisper import WhisperModel


RECORDING_PATH = "/tmp/recordings"
RECORDING_FILE = os.path.join(RECORDING_PATH, "recording.wav")
TIMEOUT_SECONDS = 600 # If there is no input for 10 minutes, exit

# Ensure the recording directory exists
os.makedirs(RECORDING_PATH, exist_ok=True)

model_size = "small.en"

data_queue = Queue()
recorder = sr.Recognizer()
source = sr.Microphone(sample_rate=16000)
temp_file = NamedTemporaryFile().name

recording_thread = None

def red(text):
    return f"\033[91m{text}\033[0m"
def green(text):
    return f"\033[92m{text}\033[0m"
def yellow(text):
    return f"\033[93m{text}\033[0m"

def record_callback(_, audio: sr.AudioData) -> None:
    """Threaded callback function to receive audio data."""
    data = audio.get_raw_data()
    data_queue.put(data)


# Start background recording
with source:
    recorder.adjust_for_ambient_noise(source)
    recorder.pause_threshold = 1.5  # Adjust pause_threshold as needed
stop_listening = recorder.listen_in_background(source, record_callback, phrase_time_limit=None)  # Adjust phrase_time_limit as needed
print(red("Background recording started... Press Enter to stop recording and transcribe."))

transcriptions = ['']  # Transcription list

def transcribe_available_audio():
    if not data_queue.empty():
        # Get audio data from queue
        last_sample = bytes()
        while not data_queue.empty():
            data = data_queue.get()
            last_sample += data

        audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
        wav_data = io.BytesIO(audio_data.get_wav_data())

        with open(temp_file, 'w+b') as f:
            f.write(wav_data.read())

        text = ""
        start_time = time.time()
        segments, info = model.transcribe(temp_file, beam_size=2, language="en", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
        for segment in segments:
            text += segment.text
        transcriptions.append(text.strip())  # Update transcription
        stop_time = time.time()

        # Print current transcription (optional, for visual feedback)
        # print("\rTranscribing live: " + transcription[-1][-60:], end="")  # Print last 60 chars
        print(f"{green(transcriptions[-1])} ({stop_time - start_time:.2f} s)")

# Main loop for transcription
while True:
    try:
        if 'model' not in locals():
            # Load model at the beginning
            print(f"Loading model {model_size}...")
            start_time = time.time()
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            end_time = time.time()
            print(f"Model loading time: {end_time - start_time:.2f} seconds")
            print("Model loaded.\n")

        transcribe_available_audio()

        # User input check (non-blocking)
        read_list, _, _ = select.select([sys.stdin], [], [], 0.1)  # Non-blocking check
        if read_list:
            user_input = sys.stdin.readline().strip().lower()
            if user_input == '':  # Enter pressed to stop current segment
                print("\nStopping... Transcribing last segment.")
                stop_listening(wait_for_stop=True)
                transcribe_available_audio()
                full_transcription = " ".join(transcriptions).strip()

                print(green(f"+-- Transcription {'-' * 33}+"))
                print(full_transcription)
                print(green(f"+{'-' * 50}+"))
                subprocess.run(["wl-copy", full_transcription])
                print(f"Transcription copied to clipboard")
                print("")
                transcriptions = ['']

                print(yellow("Press Enter to record another message, or 'q' + Enter to quit: "))
                read_list_timeout, _, _ = select.select([sys.stdin], [], [], TIMEOUT_SECONDS)
                if read_list_timeout:
                    if sys.stdin.readline().strip().lower() == 'q':
                        break  # Quit program
                else:
                    print(f"\nNo input received within {TIMEOUT_SECONDS} seconds. Exiting.")
                    break  # Timeout exit
            elif user_input == 'q':
                break  # Quit program

        time.sleep(0.1)  # Small sleep to reduce CPU usage

    except KeyboardInterrupt:
        break

print("\nExiting.")
