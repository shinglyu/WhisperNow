#!/bin/bash

# Define the path to the script
# Find the scirpt in the same folder as this script
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )/record_and_transcribe.sh"

# Open a new terminal and source the script
gnome-terminal -- bash -c "source ${SCRIPT_PATH}; sleep 5; exit"
# In gnome-terminal Edit > Rreference > Command > When command exists: Exit the teriminal"