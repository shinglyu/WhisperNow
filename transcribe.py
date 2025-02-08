# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "faster-whisper",
# ]
# ///
import time
from faster_whisper import WhisperModel

# model_size = "large-v3"
model_size = "small.en"

# Run on GPU with FP16
# model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
start_time = time.time()
model = WhisperModel(model_size, device="cpu", compute_type="int8")

segments, info = model.transcribe("temp_audio.wav", beam_size=1, language="en")

# print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    # print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
    print(segment.text)

end_time = time.time()
print(f"Model: {model_size}")
print(f"Transcription time: {end_time - start_time:.2f} seconds")
