# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper"
# ]
# ///
import time
import subprocess
from faster_whisper import WhisperModel

# model_size = "large-v3"
model_size = "small.en"
# model_size = "distil-medium.en"

# Run on GPU with FP16
# model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
print(f"Transcribing...")
start_time = time.time()
model = WhisperModel(model_size, device="cpu", compute_type="int8")

segments, info = model.transcribe("/tmp/recordings/recording.wav", beam_size=1, language="en")

# print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

# Copy the segment texts to the clipboard
transcription = " ".join([segment.text for segment in segments])
transcription = transcription.strip()
end_time = time.time()


print(f"Model: {model_size}")
print(f"Transcription time: {end_time - start_time:.2f} seconds")
print(f"Transcription: {transcription}")

subprocess.run(["wl-copy", transcription])
print(f"Transcription copied to clipboard")


