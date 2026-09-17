# Weather Advisory Support Bot

## Project Status
**Step 1 — Environment and project setup completed.**

## Technology Stack
- **Python**: 3.11+
- **LangGraph**: Agent orchestration
- **LangChain**: LLM framework & abstractions
- **OpenAI**: Intent extraction & response generation
- **FastAPI**: High-performance backend REST API
- **Streamlit**: Web frontend chat interface
- **Open-Meteo**: Live weather forecast and geocoding services (No API Key required)
- **PyYAML**: SOP policy configuration parser
- **Pydantic**: Data validation and state schemas
- **pytest**: Test runner and evaluation suite

## Setup Instructions

1. **Create Virtual Environment**:
   ```bash
   python -m venv .venv
   ```

2. **Activate Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   *(Note: Do NOT commit your `.env` file to version control.)*

## Running the Backend

Start the FastAPI backend server:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Endpoint: `http://127.0.0.1:8000/`
- Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`

## Running the Frontend

Start the Streamlit web application:
```bash
streamlit run frontend/streamlit_app.py
```

## Open-Meteo Integration
This project integrates with Open-Meteo's free APIs:
- Forecast API: `https://api.open-meteo.com/v1/forecast`
- Geocoding API: `https://geocoding-api.open-meteo.com/v1/search`

Open-Meteo services do not require an API key.
