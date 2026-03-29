import os
import tempfile
import streamlit as st

def save_temp_file(uploaded_file):
    """Saves an uploaded file to a temporary directory and returns the path."""
    if uploaded_file is None:
        return None
    
    try:
        # Create a temporary file with the same extension
        suffix = f".{uploaded_file.name.split('.')[-1]}" if '.' in uploaded_file.name else ""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(uploaded_file.getvalue())
        temp_file.close()
        return temp_file.name
    except Exception as e:
        st.error(f"Error saving temporary file: {e}")
        return None

def cleanup_temp_file(file_path):
    """Deletes a temporary file."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
