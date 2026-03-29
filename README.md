# AI Assistive Learning Project

Welcome to the AI Assistive Learning project! This application is designed to be an AI-powered conversational learning assistant for visually impaired students. It combines advanced vision processing, natural language text-to-speech, audio transcription, and even Braille translation to create an accessible learning environment.

This document serves as a high-level guide to help you navigate the project structure and understand how the different components fit together.

## 🧭 Project Navigation Guide

The entire application is currently housed within the `backend/` directory, which contains both the FastAPI backend and the Streamlit frontend. Here is a breakdown of the project architecture to help you find your way around:

```text
EDA_proj/
└── backend/                  # Main application workspace
    ├── app/                  # FastAPI Application Core logic
    │   ├── agents/           # The "Brains": Agents handling Vision, Explanation, Voice, & Braille tasks
    │   ├── api/routes/       # API Endpoints (e.g., `/chat/voice`, `/image/analyze`)
    │   ├── core/             # Application orchestration (combining agents into pipelines)
    │   ├── schemas/          # Data validation models (Pydantic models)
    │   ├── services/         # External service wrappers (OpenAI calls, Whisper STT, TTS)
    │   └── utils/            # Helper scripts (audio conversion, temp file management)
    │
    ├── streamlit/            # User Interface (Frontend API Client)
    │   ├── app.py            # Main Streamlit application file (run this to see the UI!)
    │   └── api_client.py     # Functions that connect the frontend UI to the FastAPI backend
    │
    ├── tests/                # Automated unit and integration tests
    │
    ├── .env.example          # Template for required environment keys (copy this to .env)
    ├── pyproject.toml        # Python dependency definitions (using uv package manager)
    └── README.md             # Deep-dive instructions on installation, setup, and Docker config
```

## 🚀 Quick Start Guide

If you are a new developer looking to run the project locally, here is the order of operations:

1. **Environment Setup**
   * Navigate into `backend/`.
   * Create a `.env` file by copying the contents of `.env.example` and adding your real API keys (like `OPENAI_API_KEY`).
   * Install the dependencies using the `uv` package manager: run `uv sync`.

2. **Understand the Backend**
   * The entry point for the FastAPI server is `app/main.py`.
   * To see how incoming web requests are handled, check the files in `app/api/routes/`.
   * To see the core AI logic, explore the `app/agents/` folder.

3. **Start the Servers**
   * **Backend API (Terminal 1):** Inside the `backend/` folder, run `uv run uvicorn app.main:app --reload`.
   * **Frontend UI (Terminal 2):** Inside the `backend/` folder, run `uv run streamlit run streamlit/app.py`.

4. **Detailed Technical Documentation**
   * For more granular, specialized instructions regarding tools like `liblouis` and `ffmpeg`, refer to the `backend/README.md` file.

## 💡 How it Works

* **Image Learning Flow:** The user uploads an image via the Streamlit UI -> Streamlit calls the backend `/image/analyze` API -> The backend initializes the **Vision Agent** to see the image, passes it to the **Explanation Agent** to simplify it, and finally passes text to the **Braille Agent** to convert it.
* **Voice Chat Flow:** The user talks into the UI microphone -> Streaming audio goes to `/chat/voice` API -> The **Voice Agent** transcribes it, thinks of a response, and generates TTS audio to play back through the UI.
