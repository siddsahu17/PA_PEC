# Conversational Learning Assistant Backend

A production-ready FastAPI backend for an AI-powered conversational learning assistant designed for visually impaired students. The system uses a multi-agent pipeline to process descriptive images, provide sensory-rich explanations, transcribe audio input/output, and translate text to Braille.

## Features
- **Vision Agent**: Analyzes images to extract objects, spatial relationships, and clear labels using OpenAI's Vision model.
- **Explanation Agent**: Uses the vision data to build a sensory, step-by-step description intended for visually impaired users.
- **Braille Agent**: Transcribes textual explanations into Braille using liblouis for authentic representations.
- **Voice Agent**: Provides robust text-to-speech functionality and STT interactions via Whisper.

## Project Structure
- `app/api/`: FastAPI route definitions (`/image/analyze`, `/chat/voice`)
- `app/agents/`: Standalone agents that drive specific tasks with external models.
- `app/services/`: Service wrappers for APIs and external systems like Braille utilities, Whisper, Text-to-Speech, OpenAI.
- `app/core/`: Application orchestration (pipelines, memory management).
- `app/schemas/`: Pydantic validation schemas.
- `tests/`: Project unit tests.

## Setup Instructions

### Pre-requisites
1. **Python 3.11+**
2. **FFmpeg** (Required for processing audio inputs)
3. **Liblouis** (Required for correct Braille operations, system installation may vary based on OS. E.g., `apt-get install liblouis-bin liblouis-data` for Debian/Ubuntu)

### Local Development
1. Navigate to the `backend` folder. `uv` handles virtual environment creation automatically.
2. Install Python dependencies:
   ```bash
   uv sync
   ```
3. Set your environment variables:
   Copy `.env.example` to `.env` and fill in your details (especially `OPENAI_API_KEY`).
   
4. Start the Application:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. Go to `http://localhost:8000/docs` to see the API Documentation and test endpoints.

### Setup (Docker)
1. Build the Docker image:
   ```bash
   docker build -t conversational-learning-backend .
   ```
2. Run the Docker container:
   ```bash
   docker run -p 8000:8000 --env-file .env conversational-learning-backend
   ```
