# ScreenMate

A desktop AI assistant with vision understanding, chat, text-to-speech,
multi-model switching, and context memory.

**Current version: v0.1.0 — Project Skeleton**

## Quick Start

```bash
# 1. Create virtual environment (recommended)
python -m venv ../venvs/screenmate
../venvs/screenmate/Scripts/activate   # Windows
# source ../venvs/screenmate/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Project Structure

```
screenmate/
├── app.py                     # Entry point
├── config/
│   ├── settings.py            # Unified configuration (from .env)
│   └── .env                   # Environment variables
├── providers/
│   ├── __init__.py            # Provider registry
│   ├── base/                  # Abstract base classes
│   │   ├── vision.py
│   │   ├── chat.py
│   │   └── tts.py
│   ├── vision/                # Vision provider implementations
│   ├── chat/                  # Chat provider implementations
│   └── tts/                   # TTS provider implementations
├── modules/
│   ├── screenshot/            # Screenshot capture
│   ├── context/               # Context / memory management
│   ├── logger/                # Unified logging
│   ├── monitor/               # Auto-mode monitor (stub)
│   └── settings/              # Settings accessor
├── routes/
│   └── main.py                # Page routes + REST API
├── templates/                 # Jinja2 templates
├── static/                    # CSS / JS / images
├── data/                      # Runtime data (logs, cache, context)
├── tests/                     # Unit tests
├── requirements.txt
└── README.md
```

## Architecture

- **Provider Pattern** — Add new AI models by dropping a class file in the
  appropriate `providers/<type>/` directory. No existing code changes needed.
- **MVC** — Routes (controllers) → Modules (models) → Templates (views).
- **Singleton Config** — All settings from `.env` → `Config` class, one
  source of truth.
- **Mock-first** — Every provider returns mock data. The skeleton runs
  without any API keys.

## REST API (all mock)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status |
| POST | `/api/manual` | Manual mode: screenshot → vision → response |
| POST | `/api/auto/start` | Start auto-mode (stub) |
| POST | `/api/auto/stop` | Stop auto-mode (stub) |
| GET | `/api/auto/status` | Auto-mode status |
| GET | `/api/settings` | Get settings |
| POST | `/api/settings` | Save settings (mock) |
| POST | `/api/provider/test` | Test provider connection (mock) |
| GET | `/api/logs` | Get recent logs |
| POST | `/api/logs/clear` | Clear logs |
| GET | `/api/context` | Get context state |
| POST | `/api/context/clear` | Clear context |

## Roadmap

See the About page in the app for the full roadmap.

## License

MIT
