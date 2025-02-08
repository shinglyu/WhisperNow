RECORDING_PATH=/tmp/recordings
# RECORDING_FILE="${RECORDING_PATH}/recording-$(date +%s).wav"
RECORDING_FILE="${RECORDING_PATH}/recording.wav"
TRANSCRIPTION_FILE="${RECORDING_FILE}.txt"
mkdir /tmp/recordings

SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )/transcribe.py"

echo "Press Ctrl+C to stop recording"

# Trap SIGINT and handle it
sox -d -r 16000 -c 1 -b 16 "${RECORDING_FILE}"

export OMP_NUM_THREADS=2
uv run $SCRIPT_PATH