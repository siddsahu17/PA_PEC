# AI Assistive Learning UI

This folder contains the Streamlit-based user interface for the AI-powered assistive learning system designed for visually impaired students.

## Features

* **Image Learning**: Upload images of study material to receive detailed explanations and Braille conversions.
* **Voice Interaction**: Ask questions using voice recordings and receive both transcribed text and audio responses from the AI.

## Project Structure

* `app.py`: The main Streamlit application script containing the UI layout and logic.
* `api_client.py`: Client functions to communicate with the FastAPI backend.
* `utils.py`: Helper functions, for example processing temporary uploads.

## Prerequisites

Ensure your backend is running before starting the Streamlit interface. 
The UI expects the backend to be accessible at `http://localhost:8000`.

## Installation

The dependencies for this UI (primarily `streamlit` and `requests`) are defined in the project's main `pyproject.toml`.
Make sure they are installed in your environment:

```bash
# E.g., if using poetry:
poetry install
# Or simply:
pip install streamlit requests
```

## Running the App

To start the Streamlit UI, navigate to this folder and run:

```bash
cd streamlit
streamlit run app.py
```

The application will automatically open in your default browser at `http://localhost:8501`.
