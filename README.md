# MeetingAI

> Turn meetings into actionable insights with AI-powered transcription and analysis.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0+-blue?style=flat&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="License">
  <img src="https://img.shields.io/badge/Build-Passing-success?style=flat" alt="Build">
</p>

## Overview

MeetingAI is a professional-grade meeting analysis tool that converts audio recordings or text transcripts into structured, actionable insights using AI.

### Features

- **Smart Transcription** - Upload audio files (mp3, wav, m4a, mp4) for automatic transcription
- **Text Analysis** - Paste meeting transcripts directly for instant analysis  
- **Structured Output** - Extract:
  - Executive Summary (3-sentence overview)
  - Action Items (task list with ownership)
  - Key Decisions Made
  - Key Topics Discussed
  - Meeting Duration Estimate

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0+, Python 3.11+ |
| AI/ML | Groq API (Llama 3 8B), OpenAI Whisper |
| Testing | pytest, pytest-cov |
| DevOps | Docker, GitHub Actions, Nginx |

## Quick Start

```bash
# Clone & setup
git clone https://github.com/yourusername/meetingai.git
cd meetingai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run
python app.py
```

Visit `http://localhost:5000`

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# With custom config
GROQ_API_KEY=your_key docker-compose up -d
```

## Configuration

All settings managed via `config.yaml`:

```yaml
app:
  name: MeetingAI
  debug: false
  host: 0.0.0.0
  port: 5000

upload:
  max_size_mb: 25
  allowed_extensions: [mp3, mp4, wav, m4a]

transcription:
  whisper_model: tiny  # tiny/base/small/medium/large

ai:
  model: llama3-8b-8192
  temperature: 0.5
  max_tokens: 1024
```

## API Reference

### POST /api/v1/summarize

Analyze meeting content.

**Request (multipart/form-data):**

| Parameter | Type | Description |
|-----------|------|-------------|
| file | File | Audio file (optional, max 25MB) |
| text | String | Plain text transcript (optional) |

**Response (200 OK):**

```json
{
  "result": "{\"summary\": \"...\", \"action_items\": [...], \"decisions\": [...], \"key_topics\": [...], \"duration_estimate\": \"...\"}",
  "transcript_length": 1234
}
```

**Error Responses:**

```json
{"error": "No audio file or text provided"}  // 400
{"error": "Invalid file type. Allowed: mp3, mp4, wav, m4a"}  // 400
{"error": "File too large. Max 25MB allowed"}  // 400
{"error": "Transcription failed"}  // 500
{"error": "Internal server error"}  // 500
```

## Project Structure

```
meetingai/
├── app.py                    # Application entry point
├── backend/
│   ├── app.py               # Flask factory
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exceptions
│   ├── services/
│   │   ├── ai_service.py    # Groq API integration
│   │   └── whisper_service.py # Audio transcription
│   ├── routes/
│   │   └── summarize.py     # API endpoints
│   └── utils/
│       └── logger.py        # Logging utility
├── tests/                    # Test suite
│   ├── conftest.py
│   └── test_routes.py
├── .github/workflows/       # CI/CD pipeline
├── templates/
│   └── index.html           # Frontend UI
├── storage/
│   └── uploads/             # File uploads directory
├── config.yaml              # Application config
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container image
├── requirements.txt         # Python dependencies
├── pytest.ini               # Test configuration
└── README.md
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Lint code
flake8 backend
```

## CI/CD Pipeline

The project includes automated CI/CD via GitHub Actions:

- **Test Job**: Runs pytest with coverage reporting
- **Lint Job**: Code quality checks with flake8
- **Build**: Docker image build on merge

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `CONFIG_PATH` | No | Path to config.yaml (default: config.yaml) |

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">Built with ❤️ using Flask + Groq + Whisper</p>