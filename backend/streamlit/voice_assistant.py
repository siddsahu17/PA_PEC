import streamlit as st
import sys
import os
import time

# Add backend directory to sys.path so we can import the voice module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from voice.voice_assistant import VoiceAssistant
except ImportError as e:
    st.error(f"Failed to import VoiceAssistant module: {e}")
    st.stop()

st.set_page_config(page_title="Conversational Assistant", layout="centered", page_icon="🎙️")

st.markdown("""
<style>
.main-title { font-size: 32px; font-weight: bold; color: #2E86AB; }
.status-pill {
    background-color: #f0f2f6; border-radius: 15px; padding: 5px 15px; display: inline-block; font-weight: 500;
}
.listening { background-color: #d1fae5; color: #065f46; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎙️ Siri/Alexa Style Voice Assistant</div>', unsafe_allow_html=True)
st.caption("A continuous, real-time conversational AI.")
st.divider()

# Initialize State
if "assistant" not in st.session_state or not hasattr(st.session_state.assistant, "run_step_by_step"):
    st.session_state.assistant = VoiceAssistant()
if "running" not in st.session_state:
    st.session_state.running = False
if "history" not in st.session_state:
    st.session_state.history = []

# Controls
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ Start Assistant", use_container_width=True, type="primary"):
        st.session_state.running = True
        st.rerun()
with col2:
    if st.button("⏹️ Stop Assistant", use_container_width=True):
        st.session_state.running = False
        st.rerun()

status_class = "listening" if st.session_state.running else ""
status_text = "🟢 Listening... Speak now" if st.session_state.running else "🔴 Stopped"
st.markdown(f'<div class="status-pill {status_class}">{status_text}</div>', unsafe_allow_html=True)
st.markdown("---")

# Display Chat History
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        st.write(turn["assistant"])
        if turn["intent"] == "youtube":
            st.caption("*(Executed YouTube Agent Pipeline)*")

# Containers for the live interaction
next_turn_container = st.container()

# Assistant Loop Execution
if st.session_state.running:
    status_placeholder = st.empty()
    
    user_msg_placeholder = next_turn_container.empty()
    ast_msg_placeholder = next_turn_container.empty()
    
    user_text = ""
    assistant_text = ""
    intent = ""
    
    try:
        # Step through the generated states so UI updates live
        for step in st.session_state.assistant.run_step_by_step():
            state = step["status"]
            msg = step.get("message", "")
            
            if state == "error":
                status_placeholder.error(msg)
                time.sleep(3)
            else:
                status_placeholder.info(f"🔄 {msg}")
                
            if state == "user_spoken":
                user_text = step["text"]
                with user_msg_placeholder.chat_message("user"):
                    st.write(user_text)
                    
            if state == "assistant_responded":
                assistant_text = step["text"]
                intent = step["intent"]
                with ast_msg_placeholder.chat_message("assistant"):
                    st.write(assistant_text)
                    if intent == "youtube":
                        st.caption("*(Executed YouTube Agent Pipeline)*")
    except Exception as e:
        st.error(f"Critical execution loop error: {e}")
        time.sleep(3)

    # After loop finishes, store in history permanently
    if user_text and assistant_text:
        st.session_state.history.append({
            "user": user_text,
            "assistant": assistant_text,
            "intent": intent
        })
            
    # Tiny delay before restarting loop to prevent maxing out CPU
    time.sleep(0.1)
    st.rerun()
