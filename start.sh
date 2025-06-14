#!/bin/bash

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    PYTHON_EXEC="python"
else
    # Unix-like (Linux, macOS)
    PYTHON_EXEC="python3"
fi

# This script sets up a Python virtual environment, installs dependencies,
command_exists () {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check if Python is installed
if ! command_exists $PYTHON_EXEC; then
    echo "Error: Python ($PYTHON_EXEC) was not found. Please install it first."
    exit 1
fi

# 2. Create virtual environment if it does not exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in '$VENV_DIR' ..."
    $PYTHON_EXEC -m venv $VENV_DIR
    CREATED_VENV=true
else
    echo "Virtual environment found: $VENV_DIR"
    CREATED_VENV=false
fi

# 3. Activate the virtual environment
echo "Activating virtual environment in '$VENV_DIR' ..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    source "$VENV_DIR/Scripts/activate"
else
    # Unix-like (Linux, macOS)
    source "$VENV_DIR/bin/activate"
fi


# 4. Install requirements if the virtual environment is new or if modules are missing
if $CREATED_VENV || [ ! -f "$VENV_DIR/.packages_installed" ]; then
    echo "Installing dependencies from $REQUIREMENTS_FILE ..."
    pip install --upgrade pip
    pip install -r $REQUIREMENTS_FILE

    # Erfolg markieren
    touch "$VENV_DIR/.packages_installed"
else
    echo "Dependencies are already installed. Continuing ..."
fi

# 5. Start the Python script
echo "Starting Pyhton script: start.py..."
python start.py