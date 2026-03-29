import requests
import streamlit as st

BASE_URL = "http://localhost:8000"

def analyze_image(file_path):
    """Sends an image to the backend for analysis."""
    url = f"{BASE_URL}/image/analyze"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, "image/jpeg")}
            response = requests.post(url, files=files)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with backend API for image analysis: {e}")
        return None

def send_audio(file_path, session_id="default_session"):
    """Sends an audio file to the backend for voice chat."""
    url = f"{BASE_URL}/chat/voice"
    try:
        with open(file_path, "rb") as f:
            files = {"audio": (file_path, f, "audio/wav")}
            data = {"session_id": session_id}
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with backend API for voice chat: {e}")
        return None
