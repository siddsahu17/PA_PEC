import os
import sys

# Add the parent directory (backend) to sys.path to enable importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import streamlit as st
import uuid
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

# --- Section 2: Voice Chatbot ---
st.markdown("## 🎙️ Voice Assistant Chatbot")
st.markdown('<p class="big-font">Have a continuous conversation with your AI tutor.</p>', unsafe_allow_html=True)

# Initialize chat history and session memory
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history continuously
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/mp3")

st.markdown("---")
# Input area
col1, col2 = st.columns([1, 1])
with col1:
    audio_value = st.audio_input("Record a message")
with col2:
    uploaded_audio = st.file_uploader("Upload an audio file", type=["wav", "mp3", "m4a"], key="audio_uploader")

audio_to_process = audio_value if audio_value is not None else uploaded_audio

if audio_to_process is not None:
    if st.button("Send Message", use_container_width=True, type="primary"):
        # Add a temporary user message
        st.session_state.messages.append({"role": "user", "content": "*(Voice Message)*"})
        
        with st.spinner("AI is thinking and generating voice..."):
            temp_path = utils.save_temp_file(audio_to_process)
            
            if temp_path:
                # Send the session ID so the backend remembers the context!
                result = api_client.send_audio(temp_path, session_id=st.session_state.chat_session_id)
                utils.cleanup_temp_file(temp_path)
                
                if result:
                    transcription = result.get("transcription", result.get("text", "No transcription available."))
                    response_text = result.get("response", result.get("answer", "No response text available."))
                    audio_response = result.get("audio", result.get("audio_data", None))
                    
                    # Update the placeholder user message with actual transcription
                    st.session_state.messages[-1]["content"] = f'🗣️ **You:** "{transcription}"'
                    
                    # Decode audio response
                    audio_bytes = None
                    if audio_response:
                        import base64
                        try:
                            audio_bytes = base64.b64decode(audio_response)
                        except Exception:
                            pass
                    
                    # Add AI response to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "audio": audio_bytes
                    })
                    
                    # Refresh UI to show new messages
                    st.rerun()

st.divider()
st.caption("AI Assistive System - Backend must be running on localhost:8000 for full functionality.")
