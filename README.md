# ScreenMate

A desktop AI assistant with vision understanding, global hotkey capture,
multi-model switching, and screenshot history.

**Current version: v1.1.1**

## Features

- **Global Hotkey** — Press `Ctrl+Shift+X` to capture and analyze your screen from any application
- **Vision Analysis** — OpenAI-compatible vision API (supports OpenAI, OpenRouter, SiliconFlow, Qwen, etc.)
- **Screenshot History** — Up to 50 past analyses saved locally, persist across restarts
- **Windows Toast Notifications** — Native desktop alerts even when browser is minimized
- **Prompt Templates** — Assistant, Programming, Game, OCR, Translator, Study, Custom
- **Settings Persistence** — API keys and preferences saved to `config/settings.json`
- **Markdown Rendering** — Code blocks, tables, lists with syntax highlighting

## Quick Start

```bash
# 1. Create virtual environment
python -m venv ../venvs/screenmate

# 2. Activate
../venvs/screenmate/Scripts/activate   # Windows
# source ../venvs/screenmate/bin/activate  # Linux/Mac

# 3. Install
pip install -r requirements.txt

# 4. Run
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Configure Vision API

Go to **Settings** page, fill in:

| Field | Example |
|-------|---------|
| Provider | OpenAI Compatible |
| API Key | `sk-your-key` |
| Base URL | `https://api.openai.com/v1` |
| Model | `gpt-4o` |

Click **Save Settings**, then **Test Connection** to verify.

Other compatible endpoints:
- OpenRouter: `https://openrouter.ai/api/v1`
- SiliconFlow: `https://api.siliconflow.cn/v1`
- Ollama (local): `http://localhost:11434/v1`

## Usage

1. Configure your vision API in Settings
2. Press `Ctrl+Shift+X` anywhere to capture and analyze your screen
3. Results appear in the Manual Mode page with rendered Markdown
4. Past analyses are saved in the history section below
5. Change the shortcut in Settings → Capture Shortcut → Record

## Project Structure

```
screenmate/
├── app.py                         # Entry point
├── config/
│   ├── settings.py                # Config class (reads .env + settings.json)
│   └── settings.json              # User overrides (git-ignored)
├── providers/
│   ├── __init__.py                # Provider registry + factory methods
│   ├── response.py                # Unified ProviderResponse
│   ├── base/                      # Abstract providers (vision, chat, tts)
│   ├── vision/                    # Vision providers (mock, openai)
│   ├── chat/                      # Chat providers (mock)
│   └── tts/                       # TTS providers (mock)
├── modules/
│   ├── pipeline/                  # Pipeline layer (manual, auto)
│   │   ├── manual_pipeline.py     # Screenshot → Vision → Context → Stats
│   │   ├── pipeline_result.py     # Unified PipelineResult
│   │   └── state.py               # Shared PipelineState (history, progress)
│   ├── hotkey/                    # Global hotkey listener
│   ├── notifications/             # Windows toast notifications
│   ├── screenshot/                # Screenshot capture (mss + PIL)
│   ├── context/                   # Context/memory management
│   ├── logger/                    # Unified logging
│   ├── telemetry/                 # Stats collector for Dashboard
│   ├── prompts/                   # Prompt template manager
│   ├── settings/                  # Settings persistence
│   └── events/                    # Event bus (placeholder)
├── routes/
│   └── main.py                    # Page routes + REST API
├── templates/                     # Jinja2 templates (Bootstrap 5)
├── static/                        # CSS / JS (Vanilla JS + markdown-it)
├── data/
│   ├── logs/                      # Application logs
│   ├── prompts/                   # Prompt template files (.md)
│   └── history.json               # Screenshot history (50 entries max)
├── tests/                         # pytest (85 tests)
├── requirements.txt
└── README.md
```

## Architecture

```
Browser (UI)  ←──→  Flask Routes  →  Pipeline  →  Providers (Vision/Chat/TTS)
                                       ↓
Keyboard  →  HotkeyManager  ──────────┘
                                       ↓
                              PipelineState (shared: progress, history)
                                       ↓
                              Notifications (Windows Toast)
```

- **Provider Pattern** — New AI models: drop a class in `providers/<type>/`
- **Pipeline Layer** — All business logic in pipelines; routes and hotkeys are thin input adapters
- **PipelineState** — Shared state for all input sources (button, hotkey, future auto)
- **Mock-first** — All providers start as mocks; swap in real ones via settings

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status + live stats |
| POST | `/api/manual` | Manual mode: screenshot → vision → response |
| POST | `/api/auto/start` | Start auto-mode (stub) |
| POST | `/api/auto/stop` | Stop auto-mode (stub) |
| GET | `/api/settings` | Get settings (keys masked) |
| POST | `/api/settings` | Save settings (persisted) |
| POST | `/api/settings/reset` | Reset to defaults |
| POST | `/api/provider/test` | Test connection (real API call) |
| GET | `/api/logs` | Get recent log entries |
| POST | `/api/logs/clear` | Clear logs |
| GET | `/api/logs/api-calls` | Structured API call records |
| GET | `/api/context` | Context state + memory |
| POST | `/api/context/clear` | Clear context |
| GET | `/api/prompts` | List prompt templates |
| GET | `/api/pipeline/status` | Pipeline state (progress, history) |
| GET | `/api/hotkey/status` | Hotkey configuration |
| POST | `/api/hotkey/change` | Change hotkey shortcut |
| POST | `/api/hotkey/start` | Enable hotkey |
| POST | `/api/hotkey/stop` | Disable hotkey |

## Roadmap

| Version | Milestone |
|---------|-----------|
| v1.0.0 | MVP: real screenshot (mss), OpenAI vision, Markdown, Settings, Dashboard |
| v1.1.0 | Global hotkey, PipelineState, Settings shortcut recorder |
| v1.1.1 | Windows notifications, screenshot history persistence, UI polish |
| v1.5.0 | Multi-provider (Gemini, Claude, Ollama), real TTS |
| v2.0.0 | Auto Mode: continuous observation + context memory |
| v3.0.0 | Agent Mode, plugin system, RAG |

## License

MIT
