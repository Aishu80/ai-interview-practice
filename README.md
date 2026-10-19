# AI-Powered Interview Practice & Rubric-Based Feedback System

A fully functional, AI-powered interview preparation platform built with **Gradio 6**, **OpenAI GPT**, and **Python 3.10+**. Upload your resume, practice with personalized MCQs, complete written assessments, and receive detailed rubric-based feedback.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Gradio](https://img.shields.io/badge/Gradio-6.x-orange)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Resume Analysis** - Upload PDF/DOCX/TXT resumes with AI-powered skill extraction
- **Personalized MCQs** - 20 AI-generated questions tailored to your resume and target role
- **Progressive & Adaptive Difficulty** - Easy -> Medium -> Hard or performance-based
- **Written Assessment** - 3 open-ended questions evaluated against explicit rubrics
- **Rubric-Based Scoring** - Grammar, communication, relevance, technical accuracy
- **Performance Dashboard** - Interactive Plotly charts and detailed analytics
- **PDF/JSON Reports** - Downloadable comprehensive interview reports
- **Interview History** - SQLite-backed session tracking
- **Demo Mode** - Fully functional without an API key (uses heuristic evaluation)

## Quick Start

### 1. Clone & Install

```bash
cd ai-interview
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
copy .env.example .env
# Edit .env and add your OpenAI API key for AI-powered features
```

### 3. Run

```bash
python app.py
```

Open **http://127.0.0.1:7860** in your browser.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | Your OpenAI API key. Without it, app runs in Demo Mode |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `GRADIO_SERVER_NAME` | `127.0.0.1` | Server bind address |
| `GRADIO_SERVER_PORT` | `7860` | Server port |
| `MAX_FILE_SIZE_MB` | `10` | Maximum resume file size |
| `ENABLE_HISTORY` | `true` | Enable SQLite interview history |

## Project Structure

```
ai-interview/
|-- app.py                         # Main Gradio application (7 tabs)
|-- requirements.txt
|-- .env.example
|-- models/
|   |-- schemas.py                 # All data models (dataclasses)
|-- services/
|   |-- ai_client.py               # OpenAI API wrapper with retries
|   |-- resume_parser.py           # PDF/DOCX/TXT parsing
|   |-- resume_analyzer.py         # AI resume analysis
|   |-- question_generator.py      # MCQ generation engine
|   |-- interview_engine.py        # Session & navigation management
|   |-- answer_evaluator.py        # Written answer rubric evaluation
|   |-- feedback_generator.py      # Comprehensive feedback reports
|   |-- report_generator.py        # PDF/JSON/CSV export
|-- utils/
|   |-- config.py                  # Environment configuration
|   |-- validators.py              # Input validation
|   |-- scoring.py                 # Deterministic scoring engine
|   |-- session_manager.py         # SQLite session persistence
|-- prompts/
|   |-- resume_analysis.txt        # Resume analysis prompt
|   |-- question_generation.txt    # MCQ generation prompt
|   |-- written_answer_evaluation.txt  # Written eval rubric prompt
|   |-- feedback_generation.txt    # Feedback synthesis prompt
|-- tests/
|   |-- test_scoring.py
|   |-- test_resume_parser.py
|   |-- test_services.py
|   |-- test_evaluation_reports.py
|   |-- test_feedback.py
```

## Scoring Methodology

| Component | Weight | Formula |
|-----------|--------|---------|
| MCQ Score | 60% | `correct_answers / 20 * 100` |
| Written Score | 40% | `mean(rubric_domain_scores)` |
| Combined | 100% | `MCQ * 0.60 + Written * 0.40` |

Combined score is only shown when both MCQ and Written assessments are complete.

## Deployment

### Hugging Face Spaces (Free)

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose **Gradio** as the SDK
3. Upload all project files
4. Add `OPENAI_API_KEY` as a Space Secret
5. The app deploys automatically

### Railway / Render

1. Push to a Git repository
2. Connect the repo to [Railway](https://railway.app) or [Render](https://render.com)
3. Set environment variables in the dashboard
4. Deploy with `python app.py` as the start command

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Demo Mode

When no `OPENAI_API_KEY` is configured, the app runs in **Demo Mode**:
- Resume analysis uses regex-based extraction
- MCQs come from a curated bank of 80+ questions
- Written answers are evaluated using heuristic scoring
- All demo results are clearly labeled

## License

MIT
