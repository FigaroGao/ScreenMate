# ScreenMate

A desktop AI assistant with vision understanding, persona-styled chat,
global hotkey capture, and screenshot history.

**Current version: v1.2.1**

## Features

- **Global Hotkey** — `Ctrl+Shift+X` captures and analyzes your screen from any app
- **Vision Analysis** — OpenAI-compatible vision API (OpenAI, DeepSeek, Qwen, OpenRouter, SiliconFlow, Ollama, etc.)
- **Persona Layer** — Create and switch between AI personas (Assistant, Developer, Teacher, Senpai)
- **Chat API** — Persona-styled responses powered by your own Chat API (separate from Vision)
- **Screenshot History** — 50 past analyses saved locally, persist across restarts
- **Windows Toast Notifications** — Native desktop alerts even when browser is minimized
- **Prompt Templates** — Assistant, Programming, Game, OCR, Translator, Study, Custom
- **Settings Persistence** — Per-section save, API keys and preferences to `config/settings.json`
- **Markdown Rendering** — Code blocks, tables, lists with syntax highlighting

## Quick Start

```bash
python -m venv ../venvs/screenmate
../venvs/screenmate/Scripts/activate   # Windows
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Configure APIs

**Vision** — Settings → Vision Provider → OpenAI Compatible → fill API Key / Base URL / Model → Save → Test Vision

**Chat (Persona)** — Settings → Chat Provider → OpenAI Compatible → fill API Key / Base URL / Model → Save → Test Chat

| Provider | Example Base URL |
|----------|-----------------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| SiliconFlow | `https://api.siliconflow.cn/v1` |
| Aliyun Bailian | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

## Usage

1. Configure Vision + Chat API in Settings (use Test buttons to verify)
2. Go to **Persona** → create or select a persona
3. Go to **Manual Mode** → choose a Persona from the dropdown
4. Press `Ctrl+Shift+X` anywhere to capture and analyze
5. **Persona Response** (Chat API) appears above **Vision Response** (raw analysis)
6. Past analyses in History section, click to expand

## Architecture

```
Screenshot → Vision API → Vision Response (raw)
                ↓
         Persona Layer (persona prompt + vision result)
                ↓
           Chat API → Persona Response (styled)
                ↓
              Web UI (dual display + history)
```

```
Keyboard → HotkeyManager → Pipeline → Providers (Vision / Chat / TTS)
                                        ↓
                                 PipelineState (shared: progress, history, persona)
                                        ↓
                              Windows Toast Notifications
```

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status + live stats |
| POST | `/api/manual` | Manual mode: screenshot → vision → persona → chat |
| GET | `/api/settings` | Get settings (keys masked) |
| POST | `/api/settings` | Save settings (persisted) |
| POST | `/api/settings/reset` | Reset to defaults |
| POST | `/api/provider/test` | Test Vision or Chat connection |
| GET | `/api/logs` | Recent log entries |
| POST | `/api/logs/clear` | Clear logs |
| GET | `/api/context` | Context state + memory |
| GET | `/api/prompts` | Prompt templates |
| GET | `/api/personas` | Personas list |
| POST | `/api/personas/create` | Create persona |
| POST | `/api/personas/update` | Update persona |
| POST | `/api/personas/delete` | Delete persona |
| GET | `/api/pipeline/status` | Pipeline state (progress, history, persona) |
| POST | `/api/pipeline/persona` | Set active persona |
| GET | `/api/hotkey/status` | Hotkey config |
| POST | `/api/hotkey/change` | Change shortcut |

## Project Structure

```
screenmate/
├── app.py                     # Entry point
├── config/                    # Settings (.env + settings.json)
├── providers/                 # AI providers (Vision / Chat / TTS)
│   ├── base/                  # Abstract base classes
│   ├── vision/                # Mock + OpenAI-compatible
│   ├── chat/                  # Mock + OpenAI-compatible
│   └── tts/                   # Mock
├── modules/
│   ├── pipeline/              # ManualPipeline, AutoPipeline, PipelineState
│   ├── persona/               # PersonaManager (CRUD + persistence)
│   ├── hotkey/                # Global hotkey listener
│   ├── notifications/         # Windows toast
│   ├── screenshot/            # mss + PIL capture
│   ├── context/               # Session / Memory / Summary
│   ├── logger/                # Unified logging + LogManager
│   ├── telemetry/             # StatsCollector for Dashboard
│   ├── prompts/               # PromptManager
│   ├── settings/              # Settings persistence
│   └── events/                # Event bus (placeholder)
├── routes/                    # Flask blueprints
├── templates/                 # Jinja2 (Bootstrap 5)
├── static/                    # CSS / JS (Vanilla + markdown-it)
├── data/                      # Runtime: logs, history.json, personas.json, prompts/
├── tests/                     # pytest (85 tests)
└── requirements.txt
```

## Roadmap

| Version | Milestone |
|---------|-----------|
| v1.0.0 | MVP: real screenshot (mss), OpenAI vision, Markdown, Settings, Dashboard |
| v1.1.0 | Global hotkey, PipelineState, shortcut recorder |
| v1.1.1 | Windows notifications, screenshot history persistence |
| **v1.2.x** | **Persona Layer, Chat API, dual response, per-section settings save** |
| v1.3.0 | Context integration: multi-turn memory + RAG |
| v2.0.0 | Auto Mode: continuous observation |
| v3.0.0 | Agent Mode, plugin system |

## License

MIT
