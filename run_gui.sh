#!/bin/bash
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export TCL_LIBRARY=~/.local/share/uv/python/cpython-3.12.0-linux-x86_64-gnu/lib/tcl8.6
uv run --python 3.12 "${SCRIPT_PATH}/transcribe_gui.py"
