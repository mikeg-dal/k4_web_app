# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with the K4 Web Controller codebase.

## Project Overview

K4 Web Controller is a FastAPI-based web application prototype that provides remote control for Elecraft K4 radios. It features real-time audio streaming, realistic panadapter visualization with K4-matching waterfall colors, responsive VFO controls, and CAT (Computer Aided Transceiver) commands through WebSocket connections.

**Key Project Details:**
- **Languages**: Python (backend), JavaScript (frontend), HTML/CSS
- **Type**: Real-time web application with WebSocket communication
- **Target Users**: Amateur radio operators using Elecraft K4 transceivers
- **Architecture**: FastAPI backend, WebSocket communication, modular frontend components

## Architecture & Design Principles

### Core Principle: Single Source of Truth
**CRITICAL**: All configuration values must originate from `config.py`. This is non-negotiable.

**Configuration Flow** (always follow this path):
```
config.py → server.py API endpoints → config-loader.js → frontend components
```

**Never:**
- Add hardcoded fallback values in JavaScript
- Create duplicate configuration systems
- Store configuration in multiple files

### K4 Integration-First Development
Every UI element must have complete K4 integration before implementation:
1. **Research**: Understand K4 CAT command completely
2. **Backend**: Add command support to k4_commands.py
3. **Sync**: Implement bidirectional synchronization
4. **UI**: Build interface that maintains K4 sync

## New Feature Implementation Workflow

**⚠️ MANDATORY SEQUENCE - Never skip steps or change order**

### Step 1: K4 Command Research
Before writing any code:
- Identify the exact K4 CAT command (e.g., `#AVG` for averaging)
- Determine command formats:
  - GET syntax: `#AVG;`
  - SET syntax: `#AVG{value};`
- Confirm value ranges and response formats
- Test commands with actual K4 radio if possible

### Step 2: Backend Integration (`k4_commands.py`)
Add command definition to the appropriate category:
```python
'#XYZ': CommandInfo(
    base_command='#XYZ',
    command_type=CommandType.GET_SET,
    description='Feature description',
    supports_sub_receiver=False,  # True if supports $ suffix
    operations={
        OperationType.SET: OperationInfo(
            operation_type=OperationType.SET,
            format_pattern='#XYZ{value};',
            value_type='int',
            range_min=1,
            range_max=20,
            response_format='#XYZn;',
            description='Set XYZ value (1-20)'
        ),
        OperationType.GET: OperationInfo(
            operation_type=OperationType.GET,
            format_pattern='#XYZ;',
            response_format='#XYZn;',
            description='Get XYZ value'
        )
    },
    ui_updates={
        'main': 'xyz_value'
    },
    ai_eligible=True
)
```

### Step 3: Response Handling (`app.js`)
Add response parsing in the `updateCAT()` function:
```javascript
// Handle #XYZ response
if (text.startsWith('#XYZ') && text.length > 4) {
  const xyzValueStr = text.slice(4, -1); // Remove #XYZ and ;
  const xyzValue = parseInt(xyzValueStr);
  if (!isNaN(xyzValue) && xyzValue >= 1 && xyzValue <= 20) {
    if (typeof handleXYZResponse === 'function') {
      handleXYZResponse(xyzValue);
    }
  }
}
```

### Step 4: UI Implementation
Create the UI components with proper event handling:

**HTML** (in appropriate component file):
```html
<div class="xyz-control">
  <label>XYZ Control:</label>
  <input type="range" id="xyzSlider" min="1" max="20" value="4" 
         oninput="updateXYZ(this.value)">
  <span id="xyzValue">4</span>
</div>
```

**JavaScript** (in appropriate component file):
```javascript
function updateXYZ(value) {
  const xyzValue = parseInt(value);
  document.getElementById('xyzValue').textContent = value;
  
  // Send command to K4
  if (typeof send === 'function') {
    send(`#XYZ${xyzValue};`);
  }
}

function handleXYZResponse(xyzValue) {
  const slider = document.getElementById('xyzSlider');
  const display = document.getElementById('xyzValue');
  
  if (slider && display) {
    slider.value = xyzValue;
    display.textContent = xyzValue;
  }
}

// Export for global access
window.updateXYZ = updateXYZ;
window.handleXYZResponse = handleXYZResponse;
```

### Step 5: Connection Initialization
Add initial query to `config.py` `INIT_COMMANDS` if the UI needs to reflect K4's current state:
```python
INIT_COMMANDS = [
    # ... existing commands ...
    "#XYZ;",  # Query current XYZ value
]
```

### Example Complete Implementation
Adding a button for K4 feature XYZ:
1. **Research**: `XY` command, range 0-10, format `XY{value};`
2. **k4_commands.py**: Add `XY` CommandInfo with GET/SET operations
3. **app.js**: Add `XY` parsing in updateCAT(), call `handleXYZResponse(value)`
4. **UI**: Add button HTML, `updateXYZ(value)` function, `handleXYZResponse(value)` for sync
5. **Result**: Button controls K4, K4 changes update button - perfect bidirectional sync

## Project Structure

### Directory Overview
```
k4_web_app/
├── server.py              # FastAPI entry point
├── config.py              # Single source of truth for all configuration
├── connection.py          # TCP connection to K4 radio
├── packet_handler.py      # K4 packet processing
├── k4_commands.py         # K4 protocol implementation
├── requirements.txt       # Python dependencies
├── static/               # Frontend files
│   ├── index.html        # Main HTML template
│   ├── app.js           # Core application logic
│   ├── config-loader.js  # Configuration system
│   ├── panadapter.js    # Spectrum/waterfall display
│   ├── vfo-control.js   # VFO controls
│   ├── sidebar.js       # Settings sidebar
│   └── styles.css       # Global styles
├── audio/               # Audio processing modules
│   ├── decoder.py       # RX audio (Opus/PCM)
│   ├── encoder.py       # TX audio processing
│   ├── controls.py      # Audio routing/volume
│   └── utils.py         # Audio utilities
└── venv/               # Python virtual environment
```

### Key File Responsibilities

**Backend Core:**
- `server.py`: FastAPI application, WebSocket endpoints, config API
- `config.py`: **ONLY place for hardcoded values**
- `connection.py`: K4 TCP connection management, authentication
- `packet_handler.py`: Routes K4 packets (CAT, audio, panadapter)
- `k4_commands.py`: Complete K4 protocol implementation (219 commands)

**Frontend Core:**
- `index.html`: Main template, loads components dynamically
- `app.js`: WebSocket communication, audio processing, CAT handling
- `config-loader.js`: Configuration utilities, K4*Utils functions
- `panadapter.js`: Real-time spectrum display with K4-matching colors
- `vfo-control.js`: VFO controls with K4 integration

**Audio System:**
- `decoder.py`: Handles K4 RX audio (Opus/PCM), dual receiver mixing
- `encoder.py`: Manages TX audio from browser microphone
- `controls.py`: Audio routing patterns, volume control
- `utils.py`: Debugging utilities, packet capture

## Development Setup

### Prerequisites
- Python 3.x
- Virtual environment support
- SSL certificates for HTTPS (required for microphone access)

### Setup Commands
```bash
# Activate virtual environment (includes DYLD_LIBRARY_PATH for opuslib on macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate SSL certificates (required for microphone access)
python3 generate_ssl_certs.py

# Run the server (auto-detects HTTPS based on cert availability)
python3 server.py

# Server runs on https://localhost:8000 (or http if no certs)
```

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_audio.py

# Run with coverage
pytest --cov=.
```

## Code Quality Standards & Goals

### Mandatory Practices
- **Dead code removal**: Actively identify and remove unused functions, variables, imports
- **Comment maintenance**: Update or remove outdated comments
- **Best practices enforcement**: Follow established patterns consistently
- **Avoid redundancy**: Use existing structures instead of creating new ones
- **File responsibility separation**: Keep JavaScript lightweight, heavy computation in Python
- **Purposeful coding**: Every line must serve a specific function

### Coding Conventions
- **Python**: snake_case naming, async/await throughout
- **JavaScript**: camelCase naming, modular component approach
- **Configuration**: All values must flow through config.py → server → frontend
- **No hardcoded fallbacks**: Configuration system must be complete

### File Organization Patterns
- **Modular components**: panadapter.js, vfo-control.js, sidebar.js
- **Single responsibility**: Each file has clear, focused purpose
- **Configuration utilities**: Centralized in config-loader.js
- **Audio processing**: Isolated in audio/ directory

## Key Features & Architecture

### Core Functionalities
1. **Real-time Audio Streaming**: Bidirectional audio with K4 radio
2. **Panadapter Visualization**: Spectrum/waterfall with K4-matching colors
3. **VFO Controls**: Dual VFO with complete K4 integration
4. **CAT Commands**: Full K4 protocol support (219 commands)
5. **Multi-Radio Support**: Hot-swappable radio configurations with persistent storage

### Important Modules
- **Audio System**: decoder.py, encoder.py, controls.py with 10 routing patterns
- **Panadapter**: Reference level-responsive waterfall colors matching real K4
- **VFO Controls**: Blue/green themed dual controls with Sub RX support
- **Configuration System**: config.py → server API → frontend utilities
- **Multi-Radio System**: radios/ directory with RadioConfig class, JSON storage, sidebar UI

### Complex Areas Requiring Special Attention
- **K4 Protocol**: Binary packet format with start/end markers
- **Real-time Audio**: AudioWorklet processing, Opus encoding/decoding
- **WebSocket Communication**: Handles binary audio and JSON control data
- **Panadapter Colors**: Dynamic color system responding to K4 reference level
- **Multi-Radio Management**: Dynamic configuration loading, connection switching, UI state sync

## Common Development Tasks

### Configuration Changes
**Always start with config.py:**
1. Add/modify value in appropriate config class
2. Expose via server.py API endpoint
3. Update frontend utilities to access new value
4. **Never add hardcoded fallbacks in JavaScript**

### Adding K4 Commands
Use the complete workflow above - never skip the research phase.

### Debugging Approaches
- **Frontend**: Browser console, WebSocket message inspection
- **Backend**: Python logs, packet analysis
- **Audio Issues**: Check browser permissions, HTTPS requirements
- **K4 Communication**: Verify CAT command format and responses

## Critical Gotchas & Considerations

### Audio System
- **HTTPS required** for microphone access in browsers
- **Audio frame size**: 480 samples per channel for RX (not 240)
- **PTT state**: Managed by frontend, backend responds to audio packets
- **Dual receiver**: Independent volume controls with proper routing

### K4 Integration
- **K4 handles averaging natively** - don't implement client-side averaging
- **Emergency RX command** sent on connection loss
- **Panadapter colors** respond to K4's display reference level in real-time
- **VFO volume controls** respect Sub RX enabled/disabled state

### Configuration System
- **Must flow**: config.py → server API → frontend utils
- **No shortcuts**: Don't bypass the configuration system
- **Fallbacks forbidden**: All values must come from config.py

### WebSocket Communication
- **Binary vs JSON**: Audio data is binary, control data is JSON
- **Connection handling**: Proper reconnection and error handling
- **Command tracking**: AI mode detection for unsolicited responses

## Current Architecture Goals

### Multi-K4 Support Vision
- **Sidebar system**: Future interface for multiple radio connections
- **Per-radio configuration**: Each K4 instance with separate config file
- **Dynamic connection management**: Add/remove K4s at runtime
- **Modular design**: Components ready for multi-radio architecture

### Immediate Goals
- **Single source of truth**: Complete config.py centralization
- **Code cleanliness**: Remove dead code, update comments
- **Best practices**: Consistent patterns throughout codebase
- **K4 integration first**: Never build UI without complete K4 command support

### Future Architecture
The web app will become a framework for handling data and presenting it in the UI. Each K4 server will have its own configuration file. Users will be able to:
- Add/remove K4 radios via sidebar interface
- Each connection will use its own config file
- Dynamic loading of radio-specific defaults and credentials
- Seamless switching between multiple K4 instances

## Development Philosophy

**Always remember:**
1. **K4 integration comes first** - UI follows K4 capabilities
2. **Configuration flows from config.py** - no exceptions
3. **Bidirectional sync is mandatory** - K4 and UI must stay synchronized
4. **Code serves a purpose** - every line must be justified
5. **Use existing patterns** - don't reinvent solutions
6. **Clean as you go** - remove dead code, update comments
7. **Test thoroughly** - especially WebSocket and audio functionality

This documentation ensures consistent development patterns and maintains the architectural integrity needed for the future multi-K4 vision.