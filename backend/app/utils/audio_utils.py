from pydub import AudioSegment
import os

def convert_to_wav(input_path: str, output_path: str) -> str:
    """
    Converts audio to WAV format which is widely supported by STT engines like Whisper.
    """
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="wav")
        return output_path
    except Exception as e:
        raise ValueError(f"Failed to convert audio file: {e}")
