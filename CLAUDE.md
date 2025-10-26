# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

COVAS: NEXT is an AI-powered integration for Elite: Dangerous that creates a conversational AI copilot. The system monitors game events in real-time, responds with speech, and can execute in-game actions through key emulation.

**Architecture**: Hybrid Electron desktop app with Angular 17 UI frontend and Python 3.12+ backend

## Development Commands

### Initial Setup

```bash
# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

# Install all dependencies
npm run install:all         # Installs Python, Electron, and UI dependencies

# Or install individually:
npm run install:py          # pip install -r requirements.txt
npm run install:electron    # npm install
npm run install:ui          # cd ui && npm install
```

### Development

```bash
# Run in development mode (hot-reload for UI)
npm start
# Launches Angular dev server on :1420, then Electron with Python backend
# Backend reloads when stopping/starting AI Assistant in UI

# Run Angular dev server only
cd ui && npx ng serve

# Run tests
cd ui && npx ng test      # Angular tests (Karma + Jasmine)
pytest                     # Python tests
pytest --timeout=10       # With timeout
```

### Building

```bash
# Build UI and Python backend
npm run build
# Equivalent to: npm run build:ui && npm run build:py

# Build UI only
npm run build:ui          # cd ui && npx ng build --configuration production

# Build Python backend (creates standalone executable)
npm run build:py          # Runs e2e/build.ps1 (Windows) or e2e/build.sh (Linux)
```

### Packaging

```bash
# Windows
npm run package:win32     # Creates MSI installer
npm run package:dir       # Creates unpacked directory
npm run package:msi       # MSI only

# Linux
npm run package:linux     # Creates Flatpak
npm run package:flatpak   # Flatpak only

# Run packaged app
npm run package:run       # Platform-specific
```

## Architecture

### Multi-Process Design

```
┌─────────────────────────────────────────────────────┐
│ Electron Main (electron/index.js)                   │
│  - Window management                                │
│  - Spawns Python subprocess                         │
│  - IPC bridge (stdin/stdout JSON)                   │
└─────────────┬───────────────────────────────────────┘
              │
      ┌───────┴────────┐
      │                │
      ▼                ▼
┌─────────────┐  ┌──────────────────────────┐
│ Angular UI  │  │ Python Backend           │
│ (ui/)       │  │ (src/Chat.py)            │
│             │  │                          │
│ - Settings  │  │ - EventManager           │
│ - Chat view │  │ - ActionManager          │
│ - Status    │  │ - Assistant (LLM)        │
│ - Overlay   │  │ - EDJournal (game watch) │
└─────────────┘  │ - STT/TTS                │
                 │ - PluginManager          │
                 └──────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
      Elite: Dangerous  OpenAI   Elite Keybinds
       Journal Files     API     (Action System)
```

### Key Components

**EventManager** ([src/lib/EventManager.py](src/lib/EventManager.py)): Event-driven processing pipeline
- Queues game events, user messages, tool calls
- Maintains projections (derived game state)
- Triggers sideeffects (event handlers)
- Enables conversation history across sessions

**ActionManager** ([src/lib/ActionManager.py](src/lib/ActionManager.py)): Tool registration and execution
- Registers 60+ actions as LLM tools (OpenAI function calling)
- Filters available tools by mode (ship/SRV/on-foot)
- ML-based action cache learns common user intents
- Validates actions against game state before execution

**Assistant** ([src/lib/Assistant.py](src/lib/Assistant.py)): LLM decision-making
- Builds context-aware prompts with character personality
- Calls LLM with available tools
- Executes actions via ActionManager
- Generates TTS responses

**EDJournal** ([src/lib/EDJournal.py](src/lib/EDJournal.py)): Real-time game monitoring
- Watches Elite: Dangerous journal directory: `%localappdata%/Frontier Developments/Elite Dangerous/`
- Parses JSON events (FSDJump, Docked, CombatEntered, etc.)
- Augments events with Market.json, Cargo.json, Status.json data
- Queues events into EventManager

**Actions** ([src/lib/actions/Actions.py](src/lib/actions/Actions.py)): Game control
- Reads Elite keybinds from `%localappdata%/Frontier Developments/Elite Dangerous/Options/Bindings/`
- Emulates key presses via DirectInput (Windows) or keyboard module (Linux)
- 60+ actions: fire weapons, set speed, deploy hardpoints, open galaxy map, etc.
- Configurable weapon types with fire groups

**Projections** ([src/lib/Projections.py](src/lib/Projections.py)): Derived game state
- CurrentStatus: Ship flags, position, cargo capacity
- Targeting: Current target information
- Cargo: Inventory state
- Custom projections via plugins

### Communication Protocol

**Electron ↔ Python**: Newline-delimited JSON via stdin/stdout

```javascript
// Electron sends to Python (stdin)
{ "type": "change_config", "config": {...}, "timestamp": "..." }

// Python sends to Electron (stdout)
{ "type": "chat", "role": "assistant", "message": "..." }
{ "type": "tool_call", "request": [...], "results": [...] }
{ "type": "event", "event": {"event": "FSDJump", ...} }
{ "type": "states", "states": {"CurrentStatus": {...}} }
```

**Angular Services**: RxJS observables filtered by message type
- [TauriService](ui/src/app/services/tauri.service.ts): Electron IPC bridge
- [ChatService](ui/src/app/services/chat.service.ts): Chat history
- [ConfigService](ui/src/app/services/config.service.ts): Settings state
- [EventService](ui/src/app/services/event.service.ts): Game events
- [ProjectionsService](ui/src/app/services/projections.service.ts): Game state

## Plugin System

Plugins extend functionality without modifying core code.

**Structure**:
```
plugins/my_plugin/
├── manifest.json          # Metadata (guid, name, version, entrypoint)
├── my_plugin.py           # Main class extends PluginBase
└── deps/
    └── requirements.txt   # Optional plugin dependencies
```

**Extension Points**:
- `register_actions()`: Add LLM tools
- `register_projections()`: Add game state calculations
- `register_sideeffects()`: Add event handlers
- `register_prompt_event_handlers()`: Inject LLM prompt context
- `register_status_generators()`: Add status display text

**PluginHelper API** provides access to:
- ActionManager, EventManager, PromptGenerator
- Config, LLM client, Vision client
- SystemDatabase, EDKeys

## Configuration

**config.json** (persisted by Angular UI):
- API keys (OpenAI, custom endpoints)
- Character personalities with custom system prompts
- LLM/TTS/STT provider selection
- Game event filtering (enable/disable reactions)
- Weapon configurations with fire groups
- Overlay positioning and display options
- Plugin settings

**Character Switching**: Supports multiple character profiles with distinct personalities, voices, and event preferences

**Action Permissions**: Optional whitelist to restrict available actions

## Important Implementation Details

### Event Processing Flow

1. **EDJournal** parses game event → queues in EventManager
2. **EventManager.process()** updates projections, triggers sideeffects
3. **Assistant.on_event()** decides if AI should reply (based on event type, config)
4. **Assistant.reply()** (threaded):
   - PromptGenerator builds context with character, game state, history
   - Check action cache for predicted action (fast path)
   - Call LLM with tools (filtered by active mode: ship/SRV/on-foot)
   - Execute tool_calls via ActionManager
   - Generate TTS audio
   - Emit conversation/tool events to UI

### Action Execution Validation

Before executing actions:
1. Check game state (CurrentStatus projection)
2. Validate not docked/landed for ship actions
3. Verify correct mode (mainship/fighter/SRV/on-foot)
4. Check permission whitelist if configured
5. Look up key binding from EDKeys
6. Emulate key press with optional hold duration

### Multi-Platform Considerations

- **Windows**: DirectInput for key emulation, PowerShell build script
- **Linux**: keyboard module, Bash build script, Flatpak packaging
- **Path handling**: Use `os.path.join()` and handle Windows backslashes
- **Electron builder**: Different targets per platform (MSI vs Flatpak)

## Key Dependencies

**Python**:
- `openai==1.99.2`: LLM, TTS, STT, Vision
- `faster-whisper==1.0.3`: Local STT alternative
- `edge_tts==7.2.0`: Free TTS alternative
- `keyboard==0.13.5`: Key emulation (Linux)
- `pynput==1.7.7`: Input monitoring
- `sqlite-vec==0.1.3`: Vector embeddings for RAG
- `EDMesg`: Custom library for Elite keybind parsing

**Angular**:
- `@angular/core@17`: Framework
- `@angular/material@17`: UI components
- `rxjs@7`: Reactive streams

**Electron**:
- `electron@38`: Desktop shell
- `wait-on@8`: Wait for Angular dev server

## Testing

**Python**: pytest with timeout support
- Tests in [test/](test/) directory
- Run with `pytest` or `pytest --timeout=10`

**Angular**: Karma + Jasmine
- Run with `cd ui && npx ng test`
- Config in [ui/angular.json](ui/angular.json)

## Documentation

- **User docs**: [docs/](docs/) (MkDocs site)
- **Getting Started**: https://ratherrude.github.io/Elite-Dangerous-AI-Integration/
- **Discord**: https://discord.gg/9c58jxVuAT

## File Paths Reference

| Path | Purpose |
|------|---------|
| [electron/index.js](electron/index.js) | Main process entry, window management, Python subprocess |
| [electron/preload.js](electron/preload.js) | Context bridge for Angular IPC |
| [src/Chat.py](src/Chat.py) | Python backend entry, initialization |
| [src/lib/EventManager.py](src/lib/EventManager.py) | Event queue, projections, sideeffects |
| [src/lib/ActionManager.py](src/lib/ActionManager.py) | Tool registration, action cache |
| [src/lib/Assistant.py](src/lib/Assistant.py) | LLM decision-making |
| [src/lib/EDJournal.py](src/lib/EDJournal.py) | Game journal monitoring |
| [src/lib/actions/Actions.py](src/lib/actions/Actions.py) | Game control actions |
| [ui/src/app/app.component.ts](ui/src/app/app.component.ts) | Angular root component |
| [ui/src/app/services/tauri.service.ts](ui/src/app/services/tauri.service.ts) | Electron IPC bridge |
| [package.json](package.json) | Root build scripts |
| [requirements.txt](requirements.txt) | Python dependencies |
