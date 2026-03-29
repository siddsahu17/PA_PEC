import os
import sys

# Add the parent directory (backend) to sys.path to enable importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import streamlit as st
import api_client
import utils

# Custom CSS for larger text and better accessibility
st.markdown("""
    <style>
    .big-font {
        font-size: 24px !important;
        font-weight: 500;
    }
    .main-title {
        font-size: 36px !important;
        font-weight: 700;
        color: #1E3A8A;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">AI Assistive Learning for Visually Impaired Students</p>', unsafe_allow_html=True)

st.divider()

# --- Section 1: Image Learning ---
st.markdown("## 🖼️ Image Learning")
st.markdown('<p class="big-font">Upload an image to get a detailed explanation and Braille output.</p>', unsafe_allow_html=True)

uploaded_image = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"], key="image_uploader")

if uploaded_image is not None:
    st.image(uploaded_image, caption="Uploaded Image", use_container_width=True)
    
    if st.button("Analyze Image", use_container_width=True, type="primary"):
        with st.spinner("Analyzing image... Please wait."):
            temp_path = utils.save_temp_file(uploaded_image)
            
            if temp_path:
                result = api_client.analyze_image(temp_path)
                utils.cleanup_temp_file(temp_path)
                
                if result:
                    st.success("Analysis Complete!")
                    
                    explanation = result.get("explanation", result.get("text", "No explanation provided."))
                    braille_text = result.get("braille", "No braille output provided.")
                    structured_data = result.get("structured_data", result.get("objects", None))
                    
                    st.markdown("### 📝 Explanation")
                    st.write(explanation)
                    
                    st.markdown("### ⠨⠃⠗⠁⠊⠇⠇⠑ Braille Output")
                    st.code(braille_text, language="text")
                    
                    # Display structured data if available
                    data_to_show = structured_data if structured_data else {k: v for k, v in result.items() if k not in ["explanation", "text", "braille"]}
                    if data_to_show:
                        with st.expander("View Structured Data"):
                            st.json(data_to_show)

st.divider()

# --- Section 2: Voice Interaction ---
st.markdown("## 🎙️ Voice Interaction")
st.markdown('<p class="big-font">Upload or record an audio question.</p>', unsafe_allow_html=True)

audio_value = st.audio_input("Record an audio question")
uploaded_audio = st.file_uploader("Or upload an audio file", type=["wav", "mp3", "m4a"], key="audio_uploader")

audio_to_process = audio_value if audio_value is not None else uploaded_audio

if audio_to_process is not None:
    st.audio(audio_to_process)
    
    if st.button("Send Audio", use_container_width=True, type="primary"):
        with st.spinner("Processing audio... Please wait."):
            temp_path = utils.save_temp_file(audio_to_process)
            
            if temp_path:
                result = api_client.send_audio(temp_path)
                utils.cleanup_temp_file(temp_path)
                
                if result:
                    st.success("Response Received!")
                    
                    transcription = result.get("transcription", result.get("text", "No transcription available."))
                    response_text = result.get("response", result.get("answer", "No response text available."))
                    audio_response = result.get("audio", result.get("audio_data", None))
                    
                    st.markdown("### 🗣️ You Said:")
                    st.info(transcription)
                    
                    st.markdown("### 🤖 AI Response:")
                    st.write(response_text)
                    
                    if audio_response:
                        import base64
                        try:
                            # Attempt base64 decode if raw audio bytes provided
                            audio_bytes = base64.b64decode(audio_response)
                            st.audio(audio_bytes, format="audio/mp3")
                        except Exception:
                            # Fallback if its a valid URL
                            if isinstance(audio_response, str) and (audio_response.startswith("http") or audio_response.startswith("/")):
                                st.audio(audio_response)
                            else:
                                st.error("Could not play the returned audio. Invalid format.")

st.divider()
st.caption("AI Assistive System - Backend must be running on localhost:8000 for full functionality.")
