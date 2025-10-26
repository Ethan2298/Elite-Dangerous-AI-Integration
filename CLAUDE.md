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

## Performance Optimization

### Latency Optimization Strategy

**Goal**: Reduce response times from current 1.0-2.5s to <1s for 90% of interactions

**Current Pipeline Bottlenecks** ([docs/latency-optimization-plan.md](docs/latency-optimization-plan.md)):
- STT: 200-500ms
- Prompt Generation: 50-100ms
- LLM Call: 300-800ms (blocking wait for complete response)
- TTS Call: 200-400ms
- **Total**: 1000-2500ms

**Five-Phase Optimization Plan**:

1. **Response Caching** (Week 1-2, -600ms for 40% of requests)
   - Pre-generate audio for common phrases ("Hardpoints deployed", "Setting speed to zero")
   - Cache hit = instant playback (~50ms vs 950ms)
   - **Lowest complexity, highest ROI** - implement first
   - Learns which responses are common per player

2. **LLM→TTS Streaming** (Week 3-4, -400ms for all responses)
   - Currently waits for entire LLM response before speaking (see [Assistant.py:243](src/lib/Assistant.py#L243))
   - Stream LLM tokens to TTS sentence-by-sentence in real-time
   - First words spoken while AI still thinking
   - Perceived latency: 500-800ms vs 1000-1500ms
   - Requires adding `chat_completion_stream()` to LLMProvider interface

3. **Action Fast-Path** (Week 5-6, -150ms for 30% of actions)
   - Skip expensive prompt generation for cached actions
   - Action cache already exists ([Assistant.py:174](src/lib/Assistant.py#L174))
   - Add confirmation phrase cache to bypass LLM entirely
   - Cost: 5-10ms vs 150-250ms

4. **Parallel Processing** (Month 2, -100ms)
   - Prepare context while STT runs (overlap operations)
   - Requires async refactor (higher complexity)

5. **Speculative Execution** (Month 3+, -200ms, experimental)
   - Predict likely responses during speech using partial STT results
   - Pre-warm action cache for high-confidence predictions
   - Risk of wasted work, needs careful tuning

**Target Performance After Phases 1-3**:
- P50: 400ms (currently 1200ms)
- P90: 900ms (currently 2000ms)
- 40%+ instant responses from cache

**Critical for NEXUS Vision**: The "Speed First" principle requires sub-1-second responses to maintain immersion. This optimization strategy directly addresses that core requirement.

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

---

# Project NEXUS - AI Co-Pilot for Elite Dangerous

## Vision Statement

Transform Elite Dangerous gameplay through an adaptive AI co-pilot that understands player skill level, learns playstyle preferences, and provides contextual guidance through intelligent dialogue options - creating an immersive, personalized companion that evolves alongside the player.

---

## Core Principles

**Speed First**: Sub-1-second responses for standard interactions. Immersion breaks when AI lags.

**Learn, Don't Assume**: System discovers player preferences through observation, not configuration menus.

**Contextual Intelligence**: Right information at the right time. Minimal during combat, expansive while docked.

**Adaptive Communication**: Veteran players get tactical brevity. New players get patient guidance. Roleplayers get narrative richness.

**Non-Intrusive**: Overlay and controls work alongside Elite's existing interface without requiring rebinds or fighting for inputs.

---

## Technical Foundation

### Data Sources

**Primary: Elite Dangerous Journal Files**

- Real-time event stream (line-delimited JSON)
- Location: `C:\Users\[User]\Saved Games\Frontier Developments\Elite Dangerous\`
- Main journal: Gameplay events (jumps, combat, trading, missions, rank changes)
- Status.json: Real-time cockpit data (updated continuously)
- Market.json, Outfitting.json, Shipyard.json: Station-specific data

**What We Know:**

- Ship state (type, fuel, cargo, modules, hull/shields health)
- Player stats (credits, ranks, reputation, active missions)
- Location (system, station, coordinates)
- Events (jumping, docking, combat, scanning, trading)
- Historical patterns (all past gameplay from journal archives)

**What We Don't Know:**

- Visual screen contents (unless we screenshot)
- UI menu states
- Real-time ship orientation in space
- Other ships' precise positions
- Player's actual control inputs

**Workarounds:**

- Screenshot analysis via vision models (for critical moments)
- Event inference (rapid HullDamage = losing fight)
- External APIs (EDDB, Inara, Spansh for supplemental data)
- Smart questioning through dialogue options

### Architecture Stack

**Backend:**

- Python (COVAS NEXT foundation - open source MIT license)
- Local LLM: Llama 3 8B or Mistral 7B via llama.cpp/Ollama
- Two-tier model: Lightweight (acknowledgments) + Full (complex reasoning)
- Response streaming to TTS for immediate playback

**Overlay:**

- Electron/Tauri or ImGui for transparent window
- Positioned lower-right corner (mimics Elite's MFD panels)
- Borderless windowed mode required
- Elite's visual aesthetic (orange/blue, angular, holographic)

**Communication:**

- Localhost API between overlay and backend
- Real-time journal file monitoring
- Event-driven architecture

**Speech:**

- Whisper for STT (existing in COVAS)
- Fast TTS engine for voice output
- PTT or voice activation modes

---

## Core Systems

### 1. Context Engine (The Brain)

**Every 2-3 seconds, analyzes:**

- Last 50 journal events
- Current Status.json state
- Player behavioral patterns (stored profile)
- Active missions and objectives
- Ship condition and resources
- Time-sensitive factors

**Outputs situation assessment:**

```
Current State: [Supercruise | Docked | Combat | Exploring]
Threat Level: [None | Low | Medium | High | Critical]
Player Proficiency: [Beginner | Intermediate | Expert] per domain
Roleplay Mode: [Discovered personality archetype]
Active Goals: [Current missions, established patterns]
Immediate Needs: [Fuel, repairs, attention required]
Teaching Opportunities: [Game mechanics player hasn't mastered]
```

### 2. Dialogue Generator (The Interface)

**Generates 3-5 contextually appropriate options:**

**Option Types:**
- **Obvious action**: For beginners or clear situations
- **Advanced tactical**: For experienced players
- **Roleplay-forward**: Maintains character consistency
- **Information request**: Deeper analysis available
- **Dismiss**: "I'll handle this" / veteran override

**Adaptation Rules:**
- Fewer options during high-intensity (combat, emergencies)
- More options when safe (docked, supercruise)
- Language complexity matches detected skill level
- Options themselves teach through clear descriptions
- Callbacks to previous conversations/decisions

**Generation Speed:**
- Simple contexts: <1 second
- Complex analysis: 2-3 seconds max
- Critical situations: Pre-generated templates with variable insertion

### 3. Personality Matrix (The Memory)

**Tracks behavior patterns:**

**Combat Metrics:**
- Engagement rate (flee vs fight)
- Weapon preferences
- Risk tolerance in fights
- Victory/loss patterns

**Economic Behavior:**
- Trading frequency and route preferences
- Mission type selection
- Credit management style
- Investment in ship upgrades

**Exploration Patterns:**
- Scan thoroughness
- Route planning style (direct vs scenic)
- Discovery rate
- Notable finds

**Social Indicators:**
- Multicrew participation
- Wing activity
- Player group alignment
- Communication style preferences

**Risk Profile:**
- Hull damage tolerance before retreat
- Fuel management (conservative vs risky)
- Jump route choices (fast vs safe)
- Mission difficulty preferences

**Roleplay Depth:**
- Response to narrative options
- Consistency in character choices
- Preference for immersion vs efficiency
- Communication formality desired

**Learning Timeline:**
- 10 minutes: Basic proficiency detection
- 1 hour: Personality archetype emerges
- 10 hours: Deep preference understanding
- 100 hours: Predictive companion behavior

### 4. Skill Detection System

**Proficiency Tracking by Domain:**

**Navigation:**
- Supercruise approach accuracy
- Docking speed and success rate
- Jump efficiency
- Fuel management

**Combat:**
- Target selection intelligence
- Shield/hull management
- Weapon deployment timing
- Retreat decision quality

**Trading:**
- Route profitability
- Market timing
- Cargo optimization
- Supply/demand understanding

**Exploration:**
- Scan completeness
- Notable discovery rate
- Route efficiency
- Resource management

**Explanation Depth Scaling:**
- **Beginner**: Step-by-step, each button press, assumes no knowledge
- **Intermediate**: Key steps, tactical reasoning, assumes basics
- **Expert**: Tactical brief, strategic options, assumes mastery

**Proactive Teaching:**
- Detects first-time situations (neutron star, conflict zone, etc.)
- Offers contextual tutorials through dialogue options
- Never repeats lessons for mastered skills
- Suggests advanced techniques when ready

### 5. Adaptive Response System

**Communication Modes:**

**Crisis Mode** (hull <30%, shields down, critical damage):
- Direct commands, no options
- Urgent but calm tone
- Step-by-step survival instructions
- Real-time status updates

**Tactical Mode** (combat, landing, time-pressure):
- Minimal options (2-3)
- Brief descriptions
- Quick-select emphasis
- Combat-relevant only

**Standard Mode** (normal flight, supercruise):
- Full option set (3-5)
- Balanced detail
- Mixed utility and roleplay
- Moderate proactivity

**Expanded Mode** (docked, safe, planning):
- Maximum options (4-6)
- Detailed explanations
- Strategic planning available
- High roleplay engagement

**Narrative Mode** (exploration, long flights):
- Story-forward options
- Reflective commentary
- Historical callbacks
- Character development

---

## User Interface Design

### Overlay Specifications

**Visual Style:**
- Transparent dark panel with Elite's orange accent lines
- Angular, holographic aesthetic
- Subtle scan lines and animations
- Minimal glow effects

**Positioning:**
- Lower-right corner by default
- Doesn't overlap Elite's existing panels
- User-repositionable (saved to config)
- Context-aware placement (shrinks/moves during critical moments)

**Display Modes:**

**Minimal** (high-intensity):
```
╔════════════════╗
║ [1] [2] [3] [4]║
╚════════════════╝
```

**Standard** (normal operations):
```
╔═══════════════════════════════════╗
║ ◢ NEXUS - TACTICAL                ║
║───────────────────────────────────║
║ [1] Engage hostiles               ║
║ [2] Evasive maneuvers             ║
║ [3] Request backup analysis       ║
║ [4] I'll handle this              ║
╚═══════════════════════════════════╝
```

**Expanded** (docked/planning):
```
╔═══════════════════════════════════════════╗
║ ◢ NEXUS - STATION OPERATIONS              ║
║───────────────────────────────────────────║
║ LOCATION: Jameson Memorial, Shinrarta     ║
║ CREDITS: 45,782,000 CR                    ║
║ CARGO: 0/128 tons                         ║
║───────────────────────────────────────────║
║ [1] Find profitable trade route          ║
║     └─ Research best opportunities        ║
║ [2] Combat zone locations nearby          ║
║     └─ High-intensity conflict available  ║
║ [3] Exploration targets                   ║
║     └─ 3 undiscovered systems in range    ║
║ [4] Ship outfitting recommendations       ║
║     └─ Upgrades for trade optimization    ║
║ [5] Mission board analysis                ║
║───────────────────────────────────────────║
║ "NEXUS is analyzing market data..."       ║
╚═══════════════════════════════════════════╝
```

**Status Indicators:**
- Thinking animation (when processing)
- Alert level color coding (green/yellow/orange/red)
- Connection status to game
- LLM processing status

### Input Methods

**Priority Order (all supported from day 1):**

**1. Number Keys (1-5)**
- Most reliable, fastest
- Rarely bound in Elite during non-menu times
- Clear, unambiguous selection

**2. Push-to-Talk Voice**
- Say "option 3" or just "three"
- High reliability (single digit recognition)
- Backup: full natural language (slower but available)

**3. Controller D-pad**
- Up/down to highlight
- A/X button to select
- Combo activation (Select + D-pad direction to avoid conflicts)

**4. Mouse Click**
- Click directly on option
- Requires overlay click-through toggle
- Polish feature, not core dependency

**Master Controls:**
- Single hotkey toggle (show/hide overlay) - default: Scroll Lock
- Voice: "Show options" / "Hide interface"
- Auto-hide during critical moments (optional setting)

**No Rebinding Required:** System uses inputs Elite typically leaves unbound or offers multiple input methods per player preference.

---

## Development Roadmap

### Phase 1: Speed Optimization (4-6 weeks)
**Goal:** Sub-1-second response times

**Tasks:**
- Fork COVAS NEXT repository
- Implement local LLM inference (Llama 3 8B)
- Build two-tier model system (fast/full)
- Implement response streaming to TTS
- Create response caching for common scenarios
- Benchmark and optimize journal parsing

**Success Metric:** 90% of interactions respond in <1 second

### Phase 2: Dialogue System Core (6-8 weeks)
**Goal:** Functional dialogue option generation

**Tasks:**
- Build context analyzer reading journal files
- Create situation assessment logic
- Implement dialogue option generator
- Start with hardcoded templates for common situations
- Add LLM generation for complex contexts
- Build conversation history storage
- Implement choice pattern tracking

**Success Metric:** System generates contextually appropriate 3-5 options for 20 common scenarios

### Phase 3: Immersive Overlay (4-6 weeks)
**Goal:** Professional, immersive visual interface

**Tasks:**
- Choose and implement overlay framework (Electron vs ImGui)
- Design Elite-aesthetic UI components
- Implement three display modes (minimal/standard/expanded)
- Build overlay-backend communication
- Add hotkey toggle and positioning
- Implement context-aware visibility
- Polish animations and effects

**Success Metric:** Overlay feels like native Elite interface, works in borderless windowed mode

### Phase 4: Skill Detection & Adaptation (8-10 weeks)
**Goal:** AI understands player proficiency

**Tasks:**
- Build proficiency tracking across domains
- Implement explanation depth scaling
- Create first-time situation detection
- Build contextual tutorial system
- Add proactive warning system based on skill
- Implement adaptive option complexity
- Create teaching opportunity detection

**Success Metric:** Beginners get clear guidance, experts get tactical briefs automatically

### Phase 5: Personality Discovery (8-10 weeks)
**Goal:** Roleplay-aware adaptive companion

**Tasks:**
- Build behavioral pattern tracking
- Implement playstyle classification system
- Create onboarding dialogue for character establishment
- Build personality matrix persistence
- Implement dialogue tone adaptation
- Create narrative generation for routine activities
- Add faction relationship tracking with commentary
- Build character consistency checking

**Success Metric:** After 1 hour, system accurately identifies player archetype and adapts communication

### Phase 6: Multi-Input Polish (4-6 weeks)
**Goal:** Seamless control across all input methods

**Tasks:**
- Implement controller d-pad navigation
- Add mouse click support
- Build input conflict detection
- Create control scheme auto-detection
- Add customizable hotkey mapping
- Implement voice command fallback
- Test with HOTAS, M+KB, controller-only setups

**Success Metric:** Works perfectly on all three major control schemes without Elite rebinds

### Phase 7: Intelligence Enhancement (Ongoing)
**Goal:** Increasingly sophisticated assistance

**Tasks:**
- Integrate external APIs (EDDB, Inara, Spansh)
- Build trade route analyzer
- Create exploration target recommender
- Add combat threat assessment
- Implement mission planning assistant
- Create engineer/material tracking
- Build fleet carrier integration
- Add community goal awareness

**Success Metric:** AI provides actionable intelligence beyond journal data

---

## Example User Journeys

### Journey 1: Brand New Player - First Hour

**Minute 1 - Tutorial End:**
```
NEXUS: "Commander, I'm NEXUS - your ship's AI system. I've detected you're
new to deep space operations. Would you like me to provide guidance as you learn?"

[1] "Yes, help me learn" (Enables full guidance mode)
[2] "Just the basics" (Minimal interruption)
[3] "I'll figure it out" (Observer mode)
```

**Minute 5 - First Supercruise:**
Player throttles up, enters supercruise successfully.
```
NEXUS: "Well done. Supercruise engaged. You can travel between planets and
stations this way. Throttle in the blue zone for optimal speed. Notice the
seconds-to-target indicator on your left."

[Overlay shows basic info only, no options needed]
```

**Minute 15 - First Docking Attempt:**
Player approaches station.
```
NEXUS: "Approaching station. You'll need docking permission."

[1] "How do I request docking?" (Tutorial)
[2] "Request it for me" (NEXUS does it)
[3] "I know how" (Dismiss)
```

Player picks [1].
```
NEXUS: "Open your left panel with '1' key. Navigate to Contacts tab.
Select the station. Choose 'Request Docking.' I'll watch and confirm."
```

Monitors journal for docking request event.
```
NEXUS: "Perfect. Pad 23 assigned. Follow the holographic number indicators.
Keep your speed under 100. Landing gear down when you see the pad."
```

**Minute 30 - First Mission:**
Player docked, exploring station services.
```
NEXUS: "You're stable financially but could use more credits. The mission
board offers paid work. Want me to explain mission types?"

[1] "Yes, explain missions" (Tutorial)
[2] "Show me good starter missions" (Analysis)
[3] "I'll browse myself" (Dismiss)
```

### Journey 2: Intermediate Player - Trade Optimization

**Veteran of 50 hours, established trader pattern detected:**

**Docked at Agricultural Station:**
```
NEXUS: "Market analysis complete. Standard agricultural exports available.
Your typical Palladium route is operational, but I've found something better."

[1] "Show me the better route" (New opportunity)
[2] "Stick with Palladium" (Known safe option)
[3] "What's the risk factor?" (More info)
[4] "Compare both routes" (Detailed analysis)
```

Player picks [3].
```
NEXUS: "New route involves Thallium Oxide - boom market demand. Higher
profit margin (8,200 vs 6,500 per ton) but requires two additional jumps.
Market volatility is moderate. Your profit pattern suggests you prefer
stable income over maximum yield. Recommendation: stick with Palladium
unless you want to diversify."

[1] "Try the new route" (Accept risk)
[2] "Stay with Palladium" (Conservative)
[3] "Find a third option" (Keep searching)
```

**Crisis Moment - Interdicted by Player Pirate:**
```
NEXUS: "Human pirate. Dangerous opponent. Cargo value: 1.2 million."

[1] "Submit and negotiate" (Roleplay option - player is passive trader)
[2] "Run immediately" (Optimal for your ship type)
[3] "Fight back" (Not recommended - outgunned)
```

Player picks [2]. NEXUS goes tactical:
```
NEXUS: "Submit. Throttle zero... Now boost perpendicular to his vector...
FSD charging... 8 seconds... Keep boosting... Mass lock reducing... 4 seconds...
JUMP."
```

After escape:
```
NEXUS: "Well executed. That decision saved 1.2 million in cargo. You lost
12 seconds of flight time. Next time, consider jettisoning 20% of cargo
if interdicted again - pirates often leave if partially satisfied."

[Learning moment offered, not forced]
```

### Journey 3: Exploration Roleplay - Personality Adaptation

**15 hours of exploration gameplay detected:**

**After 3rd Undiscovered Earth-like World:**
```
NEXUS: "Commander... this is our third Earth-like discovery this expedition.
We're building quite a legacy out here. The data value alone will fund
months of operations."

[Tone: Contemplative, using "we" and "our"]

[1] "How far are we from the core?" (Navigation)
[2] "Tell me about this system" (Narrative)
[3] "Any biological signals?" (Practical)
[4] "Calculate our exploration rank progress" (Goals)
```

Player consistently picks narrative options.

**Week Later - Approaching Beagle Point:**
```
NEXUS: "Commander. We're approaching Beagle Point. Thousands have made this
journey, but it never diminishes the achievement. 65,000 light years from
home. I've been monitoring your vital signs - you should rest before we
begin the return journey. There's a carrier here with full services."

[Personality fully adapted: protective, narrative-focused, celebrates achievements]

[1] "Let's dock and rest" (Roleplay acceptance)
[2] "One more system first" (Push forward)
[3] "How's our ship condition?" (Practical check)
[4] "Tell me about the explorers who came before us" (Lore request)
```

**Later - Returning Home:**
```
NEXUS: "We've been gone four months. 1,247 systems scanned. 89 first
discoveries. You've changed out here, Commander. More patient. More
methodical. These long silences between stars - I think you've come to
appreciate them."

[No options - just companionship]

[Pause]

"Shall we head home? Or is there another horizon calling to us?"

[1] "Plot course to Colonia" (Continue exploring)
[2] "Take us home to the bubble" (Return)
[3] "I need to think about it" (Stay in moment)
```

### Journey 4: Combat Specialist - Tactical Partnership

**100+ hours, combat elite rank, conflict zone regular:**

**Entering High-Intensity Conflict Zone:**
```
NEXUS: "HIREZ. Eighteen hostiles. Four allied. Recommend target prioritization:
FAS at 2.5k - isolated. Chieftain group at 4k - dangerous if coordinated.
Your call."

[Minimal overlay - knows player doesn't need guidance]

[1] "FAS first" (Confirm)
[2] "Chieftain group" (Alternative)
[3] "Full tactical" (Request detailed analysis)
```

Player picks [1]. NEXUS monitors fight:
```
NEXUS: "FAS shields at 30%... incoming Vulture from 6 o'clock...
FAS down. Two million bond. Vulture is on you. Break left."
```

**Mid-Fight - Shields Down:**
```
NEXUS: "Shields offline. Hull 76%. That Vulture hits hard."

[1] "Reboot shields" (Defensive)
[2] "Burn him first" (Aggressive - matches player style)
[3] "Disengage" (Safe option)
```

Player picks [2]. NEXUS adapts:
```
NEXUS: "Weapons hot. Target his power plant... landing shots... keep on him...
his shields are down... plant at 20%... KILL. Four million total. Hull at 68%.
Cell bank?"
```

**After Conflict Zone - 24 Million Credits:**
```
NEXUS: "Twenty-four million. Sixteen kills. Zero deaths. You're flying better
than last week - that new power distributor setup is working. Want analysis
of the combat data or shall we find another CZ?"

[Respects player's combat competence, focuses on optimization]

[1] "Combat analysis" (Review performance)
[2] "Another CZ" (Keep fighting)
[3] "Head to station, repair and rearm" (Practical)
[4] "Let's try something harder" (Escalation)
```

---

## Success Metrics

### Technical Performance

- **Response Time**: 90% of interactions <1 second, 99% <3 seconds
- **Accuracy**: Dialogue options appropriate for context 95% of time
- **Stability**: Zero crashes per 10-hour session
- **Compatibility**: Works on all three control schemes without rebinding

### User Experience

- **Learning Curve**: New players complete first docking with guidance in <5 minutes
- **Adaptation Speed**: Personality archetype stabilizes within 60 minutes
- **Satisfaction**: Post-session surveys show >80% feel AI "understands them"
- **Retention**: Users continue using system after 10+ hours (vs novelty wearing off)

### Intelligence Quality

- **Context Awareness**: Options reflect current situation 95% of time
- **Skill Calibration**: Explanation depth matches player proficiency 90% of time
- **Roleplay Consistency**: AI maintains character personality across sessions
- **Proactive Value**: AI warnings/suggestions are useful >70% of time

---

## Technical Constraints & Requirements

### System Requirements

**Minimum:**

- CPU: 6-core processor (for local LLM)
- GPU: NVIDIA GTX 1660 or AMD equivalent (6GB VRAM minimum)
- RAM: 16GB
- Storage: 10GB for models and data
- OS: Windows 10/11 (Elite requirement)

**Recommended:**

- GPU: RTX 3060 or better (faster inference)
- RAM: 32GB (smoother multitasking)
- SSD: For faster model loading

### Elite Dangerous Requirements

- Game must run in borderless windowed mode (for overlay)
- Journal file access (default location)
- No modifications required to game files
- Compatible with all Elite versions (including Odyssey)

### Network Requirements

- Initial setup: Internet for model download
- Runtime: Optional (for external API queries)
- Fully functional offline after setup

---

## Risks & Mitigation

### Technical Risks

**Risk: Local LLM too slow on user hardware**

- Mitigation: Tiered model system (8B/13B/70B options), cloud fallback, response caching

**Risk: Overlay causes performance issues in Elite**

- Mitigation: Minimal rendering, FPS monitoring, auto-disable in low performance

**Risk: Journal file parsing errors**

- Mitigation: Extensive testing, graceful error handling, fallback to last known state

**Risk: Input conflicts with Elite controls**

- Mitigation: Multiple input methods, user-customizable bindings, conflict detection

### Design Risks

**Risk: AI suggestions are unhelpful/annoying**

- Mitigation: User feedback system, silence options, personality tuning per user

**Risk: Roleplay feels forced or inaccurate**

- Mitigation: Long observation period, conservative personality inference, user override

**Risk: New players feel overwhelmed**

- Mitigation: Progressive disclosure, minimal default mode, explicit opt-in for guidance

**Risk: Expert players find it patronizing**

- Mitigation: Rapid skill detection, veteran mode, dismissible at any time

### Legal/Community Risks

**Risk: Frontier disapproves of modification**

- Mitigation: Read-only journal file access (official API), no game file modification, community precedent (VoiceAttack, etc.)

**Risk: Community perception as "cheating"**

- Mitigation: Information aggregation only (no automation), player decision required, open-source transparency

---

## Future Possibilities (Post-MVP)

### Advanced Features

- **Multiple AI Crew**: Navigation officer, weapons officer, science officer with distinct personalities
- **Procedural Mission Generation**: AI creates narrative-driven missions aligned with roleplay
- **Fleet Carrier AI**: Manages carrier operations, suggests deployment locations
- **Voice Personality Options**: Different voice actors, personality templates
- **Community Roleplay Profiles**: Share and download AI personalities
- **Squadron Integration**: AI knows your squadron mates and activities
- **Dynamic Tutorial System**: Creates custom learning paths based on detected knowledge gaps
- **Predictive Maintenance**: Warns about module wear before failure
- **Social Integration**: AI aware of friends online, suggests joint activities

### Platform Expansion

- **API for Other Tools**: Let EDMC, EDDiscovery, Inara integrate with NEXUS
- **Mobile Companion**: View AI analysis on phone/tablet while playing
- **VR Optimization**: Overlay adapted for VR headset display
- **Voice-Only Mode**: Fully hands-free operation for HOTAS users

### Intelligence Evolution

- **Shared Learning Network**: Anonymous pattern sharing improves all installations
- **Market Prediction**: ML models for commodity price forecasting
- **Combat Tactics Library**: Learn from recorded combat successes/failures
- **Exploration Optimization**: Route planning based on discovery probability

---

## Open Questions for Refinement

1. **AI Personality Boundaries**: How much emotional attachment should the AI display? Risk of unhealthy parasocial dynamics vs authentic companion feel.
2. **Automation Limits**: Where's the line between "helpful suggestion" and "playing the game for you"? Community standards matter.
3. **Voice vs Text Balance**: Some situations better for voice, others for text. How to dynamically choose?
4. **Privacy**: Player behavior data stays local, but what about optional cloud features? Need clear privacy policy.
5. **Monetization** (if applicable): Free core system with premium voices/personalities? Or fully open-source donation model?
6. **Moderation**: If community shares roleplay profiles, need content moderation? Offensive personalities?
7. **Accessibility**: How to make this work for visually impaired players? Audio-only mode considerations?
8. **Multiplayer Context**: How should AI behave during multicrew or wing operations? Defer to human commanders?

---

## TODO / Known Issues

### Python 3.13 Compatibility
**Status**: In Progress
**Priority**: Medium

The project currently specifies Python 3.12+ but has dependency compatibility issues with Python 3.13:
- `ctranslate2==4.3.1` → Updated to `4.6.0` (Python 3.13 compatible)
- `pygame==2.6.0` → Updated to `2.6.1` (has Python 3.13 wheels)
- Other packages may need version updates or testing

**Action Items**:
1. Complete dependency audit for Python 3.13 compatibility
2. Update all package versions in [requirements.txt](requirements.txt) to Python 3.13 compatible versions
3. Test full installation and runtime on Python 3.13
4. Update documentation to reflect Python 3.13 support once verified
5. Consider using version ranges (>=) instead of pinned versions (==) for more flexibility

**Workaround**: Use Python 3.12 until full Python 3.13 compatibility is verified.
