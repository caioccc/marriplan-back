import logging
import subprocess
import sys

from app.core.constants import LLM_MODEL_NAME


def pull_ollama_model(model_name):
    # Build the pull command
    pull_command = f"ollama pull {model_name}"

    # Open the process and capture stdout, merging stderr into stdout
    process = subprocess.Popen(
        pull_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # Iterate over each line of output from the process
    for line in process.stdout:
        # Remove newline characters and prepare the progress string
        progress = line.strip()
        # Write the progress on the same line using carriage return ('\r')
        # Using ljust to ensure any previous longer text is overwritten
        sys.stdout.write("\r" + progress.ljust(80))
        sys.stdout.flush()

    # Wait for the process to finish
    process.wait()
    # Print a newline after completion to move the cursor to the next line
    print()


def check_ollama_recognized():
    try:
        result = subprocess.run("ollama --help", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        raise Exception(f"Error while executing 'ollama' command: {e}")

    # Check if the command output indicates that 'ollama' is not recognized.
    if result.returncode != 0:
        raise Exception(
            "'ollama' command is not recognized. Please ensure Ollama is installed and available in PATH.")


def check_ollama_model_available():
    try:
        # Execute 'ollama list' and capture its output (hidden from the Python console)
        list_result = subprocess.run("ollama list", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
    except Exception as e:
        raise Exception(f"Error while executing 'ollama list': {e}")

    if LLM_MODEL_NAME not in list_result.stdout:
        logging.info(f"Model '{LLM_MODEL_NAME}' not found locally. Downloading...")
        pull_ollama_model(LLM_MODEL_NAME)
    else:
        logging.info(f"Model '{LLM_MODEL_NAME}' is already downloaded.")


def check_ollama():
    # Step 1: Check if 'ollama' is installed by executing the 'ollama' command
    check_ollama_recognized()

    # Step 2: Check if the specified core is already downloaded using 'ollama list'
    check_ollama_model_available()
