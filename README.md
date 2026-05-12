# 🌟 Vidya — Multilingual Voice Learning Assistant

Welcome to the **Vidya** project! This application is designed to be an AI-powered conversational learning assistant for students (particularly supporting visually impaired students). It combines advanced vision processing, natural language Text-to-Speech (via Sarvam AI), audio transcription (via Whisper), deep learning intent classification, and Diagram RAG to create a highly accessible and interactive learning environment.

This document serves as a high-level guide to help you navigate the completely revamped full-stack project structure.

---

## 🧭 Project Architecture & Navigation Guide

The project has evolved into a modern full-stack application, split cleanly between a React Web Frontend and a robust Python/FastAPI Backend.

```text
PA_PEC/
├── frontend/                 # 🌐 React + Vite Web Application
│   ├── src/                  
│   │   ├── App.jsx           # Main layout (1/3 Voice Chat / 2/3 Information Display)
│   │   └── SiriOrb.jsx       # Interactive animated voice recording component
│   └── package.json          # Node dependencies
│
└── backend/                  # 🧠 Core Python AI Application
    ├── app/                  # FastAPI Application Core logic
    │   ├── api/routes/       # API Endpoints (e.g., `/api/siri-chat`, `/image/analyze`)
    │   └── agents/           # Specialized vision and explanation processing
    │
    ├── voice/                # The Multilingual Voice Pipeline
    │   ├── diagram_rag_agent.py # Fetches rich educational data based on voice queries
    │   ├── intent_router.py     # Classifies user intent to route to the correct agent
    │   ├── speech_to_text.py    # Whisper-powered STT
    │   └── text_to_speech.py    # Sarvam AI-powered multilingual TTS
    │
    ├── data/                 # Educational Modules (JSON files like digestive_system.json)
    │
    ├── streamlit/            # 📊 Machine Learning Evaluation UI
    │   └── evaluation_dashboard.py # Dashboard for Accuracy, Precision, F1, and ROC Curves
    │
    ├── voice_chat.py         # 🎙️ Headless pure-voice terminal chatbot script
    ├── gan_analysis.py       # ML experiments for Mel-Spectrogram GAN synthesis
    ├── pyproject.toml        # Python dependencies (managed via uv)
    └── .env.example          # Template for required environment keys (OpenAI, Sarvam)
```

---

## 🚀 Quick Start Guide

### 1. Backend Setup (FastAPI & AI Pipelines)
1. Navigate into the `backend/` directory: `cd backend`
2. Create a `.env` file by copying the contents of `.env.example`. 
   - **Crucial**: Add your `OPENAI_API_KEY` and `SARVAM_API_KEY`.
3. Install the Python dependencies using `uv`: 
   ```powershell
   uv pip install -e .
   ```
4. Start the FastAPI server:
   ```powershell
   uv run uvicorn app.main:app --reload
   ```

### 2. Frontend Setup (React UI)
1. Open a new terminal and navigate to the `frontend/` directory: `cd frontend`
2. Install the Node modules:
   ```powershell
   npm install
   ```
3. Start the Vite development server:
   ```powershell
   npm run dev
   ```
4. Open the provided `localhost` link in your browser to interact with the gorgeous Siri-orb UI!

---

## 🔬 Standalone Tools & Dashboards

The backend contains several powerful standalone tools that can be run independently of the web application:

### The ML Evaluation Dashboard (Streamlit)
To view the experimental results and comparison rubrics (Accuracy, Precision, Recall, F1) between our BiLSTM, CNN, and Transformer models, run the Streamlit dashboard:
```powershell
cd backend
streamlit run streamlit/evaluation_dashboard.py
```
*This opens a local web page with interactive Plotly graphs, including Grouped Bar Charts and ROC curves.*

### The Headless Terminal Voice Chat
Want to talk to the AI without a web browser? You can run the Siri-style script directly in your terminal. It will calibrate your microphone and talk to you continuously until you say "goodbye".
```powershell
cd backend
python voice_chat.py
```

---

## 💡 How it Works

* **Voice Chat Flow (Web)**: The user clicks the Siri Orb in the React frontend and speaks -> The browser sends the audio Blob to the `POST /api/siri-chat` FastAPI endpoint -> The backend uses `SpeechToText` to transcribe -> `IntentRouter` figures out what the user wants -> `DiagramRAGAgent` pulls JSON data (like `digestive_system.json`) -> `TextToSpeech` (Sarvam AI) generates the audio response -> The backend returns the Base64 audio + structured data -> The frontend plays the audio aloud and beautifully renders the 2/3 screen data cards.
* **Image Learning Flow**: The user uploads an image -> The backend `/image/analyze` API uses the Vision Agent to see the image -> The Explanation Agent simplifies it -> The Braille Agent converts it for tactile feedback.
