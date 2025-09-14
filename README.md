# K4 Web Controller

A modern web-based remote control interface for Elecraft K4 transceivers, featuring real-time audio streaming, panadapter visualization with K4-matching waterfall colors, and comprehensive CAT control.

## Features

- **Real-time Audio Streaming**: Bidirectional audio with K4 radio using WebRTC and Opus encoding
- **Panadapter Display**: High-fidelity spectrum analyzer and waterfall display with K4-matching color palette
- **VFO Controls**: Dual VFO frequency control with blue/green themed interface
- **CAT Commands**: Complete K4 protocol support (219+ commands) with bidirectional synchronization
- **Multi-Radio Support**: Manage multiple K4 radios with persistent configurations
- **Responsive Design**: Modern web interface optimized for desktop and tablet use

## System Requirements

### Hardware Requirements
- **Elecraft K4 Transceiver** with network interface enabled
- **Computer** capable of running Python 3.9+ (Windows, macOS, or Linux)
- **Network Connection** to K4 radio (Ethernet or WiFi)
- **Audio Hardware** (built-in microphone/speakers or external audio interface)

### Software Requirements
- **Python 3.9 or higher** (Python 3.12+ recommended)
- **Modern Web Browser** with WebRTC support:
  - Chrome 85+ (recommended)
  - Firefox 78+
  - Safari 14+
  - Edge 85+
- **Network Access** to K4 radio on port 9205
- **HTTPS Support** for microphone access (certificates included)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/k4_web_app.git
cd k4_web_app
```

### 2. Set Up Python Environment

#### Using Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Your K4 Radio

#### K4 Network Setup
1. **Enable Network Interface** on your K4:
   - Menu → CONFIG → Network
   - Set IP address, subnet mask, gateway
   - Enable "Network Control"
   - Note the IP address (e.g., 192.168.1.10)

2. **Set Network Password** (if using password authentication):
   - Menu → CONFIG → Network → Password
   - Default is usually "tester"

### 4. Generate SSL Certificates (Required)

The application requires HTTPS for microphone access. SSL certificates are included in the project, but you can generate fresh ones if needed:

**Option 1: Use existing certificates (recommended)**
```bash
# The project already includes working SSL certificates
# No action needed - they're in certs/cert.pem and certs/key.pem
```

**Option 2: Generate fresh certificates (optional)**
```bash
# Create the certificate directory or use the one that is in the git clone
mkdir -p certs

# Generate new self-signed SSL certificate (valid for 1 year)
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"
```

**Required files for HTTPS:**
- `certs/cert.pem` (certificate file)
- `certs/key.pem` (private key file)

The application will automatically detect these files and enable HTTPS.

### 5. Run the Application

```bash
python3 server.py
```

The server will start and display:
```
⚙️ K4 Configuration module loaded
   Audio: 48000Hz → 12000Hz
   Frame size: 480 samples/channel
   K4: 192.168.1.10:9205
🚀 K4 Web Controller starting on https://localhost:8000
📻 Created default radio configuration
📡 Connecting to K4 at 192.168.1.10:9205...
✅ Connected to K4 successfully
```

### 6. Access the Web Interface and Configure Your Radio

Open your web browser and navigate to:
- **https://localhost:8000** (with SSL certificates)
- **http://localhost:8000** (fallback without SSL)

**Important**: Use HTTPS for full functionality including microphone access for transmit audio.

#### Configure Your Radio Through the Web Interface

The application automatically creates a default radio configuration, but you'll need to update it with your K4's details:

1. **Click the gear icon** (⚙️) in the top-right corner to open the Settings sidebar
2. **In the Radio Management section**, you'll see the default radio listed
3. **Click "Edit"** on the default radio to configure it:
   - **Name**: Give your radio a friendly name (e.g., "K4 Main Station")
   - **IP Address**: Enter your K4's IP address (e.g., 192.168.1.10)
   - **Port**: Leave as 9205 (standard K4 port)
   - **Password**: Enter your K4's network password (default: "tester")
   - **Description**: Optional description
4. **Click "Save"** to save the configuration
5. **The application will automatically reconnect** to your K4 with the new settings

**Adding Multiple Radios**: Use the "Add Radio" button to configure additional K4 radios. You can switch between radios instantly using the radio list in the sidebar.

## Detailed Setup Instructions

### Network Configuration

#### K4 Radio Network Setup
1. **Access K4 Menu System**:
   - Press `MENU` on K4
   - Navigate to `CONFIG` → `Network`

2. **Configure Network Settings**:
   - **IP Address**: Set static IP (e.g., 192.168.1.10)
   - **Subnet Mask**: Usually 255.255.255.0
   - **Gateway**: Your router's IP (e.g., 192.168.1.1)
   - **DNS**: Your router's IP or 8.8.8.8

3. **Enable Network Control**:
   - Set "Network Control" to `ON`
   - Set "Network Password" (default: "tester")

4. **Save Configuration**:
   - Press `STORE` to save settings
   - Restart K4 if prompted

#### Firewall Configuration

**Windows:**
```powershell
# Allow Python through Windows Firewall
netsh advfirewall firewall add rule name="K4 Web Controller" dir=in action=allow program="python.exe"
```

**macOS:**
```bash
# macOS will prompt for firewall permission when first running
# Grant permission in System Preferences → Security & Privacy → Firewall
```

**Linux:**
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 8000
sudo ufw allow out 9205

# iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 9205 -j ACCEPT
```

### Audio Configuration

#### Browser Audio Permissions
1. **Navigate to the web interface** (must use HTTPS)
2. **Grant microphone permission** when prompted
3. **Test audio** using the VFO controls and PTT button

#### Audio Troubleshooting
- **No microphone access**: Ensure you're using HTTPS (https://localhost:8000)
- **Poor audio quality**: Check K4 MIC GAIN and web interface MIC GAIN settings
- **Audio dropouts**: Verify network stability between computer and K4
- **No receive audio**: Check K4 volume settings and web interface volume controls

### Advanced Configuration

#### Multi-Radio Setup
The application supports multiple K4 radios through the web interface:

1. **Add additional radios**:
   - Open the Settings sidebar (gear icon ⚙️)
   - Click "Add Radio" in the Radio Management section
   - Fill in the radio details (name, IP address, password)
   - Click "Save" to add the radio

2. **Switch between radios**:
   - Select any radio from the list in the sidebar
   - The application will automatically disconnect from the current radio and connect to the selected one
   - Connection status is shown in real-time

3. **Manage radios**:
   - **Edit**: Update radio settings (name, IP, password, etc.)
   - **Delete**: Remove radios you no longer need (cannot delete the only radio)
   - **Enable/Disable**: Temporarily disable radios without deleting them

#### Custom Port Configuration
To run on a different port, modify `config.py`:

```python
class WebConfig:
    DEFAULT_PORT = 8080  # Change from 8000 to 8080
```

#### Audio Settings Optimization
Fine-tune audio settings in `config.py`:

```python
class AudioConfig:
    # Adjust for your specific setup
    DEFAULT_MIC_GAIN = 0.15        # Increase for more microphone gain
    OPUS_BITRATE = 64000           # Audio quality (32000-128000)
    DEFAULT_MASTER_VOLUME = 1.5    # Overall volume level
```

## Troubleshooting

### Connection Issues

#### "Connection Refused" Error
```
Error: Connection refused to 192.168.1.10:9205
```
**Solutions:**
- Verify K4 IP address in `config.py`
- Ensure K4 "Network Control" is enabled
- Check network connectivity: `ping 192.168.1.10`
- Verify K4 is on same network subnet
- Check firewall settings on both computer and network

#### "Authentication Failed" Error
```
Error: Authentication failed - incorrect password
```
**Solutions:**
- Verify password in `config.py` matches K4 network password
- Default K4 password is usually "tester"
- Check K4 Menu → CONFIG → Network → Password

#### "Timeout" Errors
```
Error: Connection timeout to K4
```
**Solutions:**
- Check network stability and latency
- Ensure K4 is powered on and responsive
- Verify no other applications are connected to K4
- Restart K4 network interface

### Audio Issues

#### No Microphone Access
```
Error: Microphone access denied
```
**Solutions:**
- **Must use HTTPS**: Navigate to https://localhost:8000
- Grant microphone permission in browser
- Check browser security settings
- Verify SSL certificates are present in `certs/` directory

#### Poor Audio Quality
**Solutions:**
- Adjust MIC GAIN in web interface
- Check K4 MIC GAIN settings
- Verify network bandwidth (recommend 1Mbps+)
- Use wired Ethernet connection if possible

#### Audio Dropouts
**Solutions:**
- Check network stability and jitter
- Reduce other network traffic
- Increase audio buffer size in browser
- Verify computer is not overloaded (check CPU usage)

### Web Interface Issues

#### Page Won't Load
**Solutions:**
- Check server is running: `python3 server.py`
- Verify port isn't blocked: `netstat -an | grep 8000`
- Try different browser
- Clear browser cache and cookies
- Check browser console for JavaScript errors

#### Controls Not Responding
**Solutions:**
- Check WebSocket connection in browser developer tools
- Verify K4 connection status
- Refresh page to re-establish WebSocket
- Check for JavaScript errors in browser console

### Performance Issues

#### High CPU Usage
**Solutions:**
- Reduce panadapter update rate
- Lower audio quality settings
- Close unnecessary browser tabs
- Check for background processes
- Consider dedicated computer for K4 control

#### Memory Leaks
**Solutions:**
- Refresh browser periodically during long sessions
- Monitor memory usage in browser developer tools
- Restart application if memory usage grows excessive
- Update to latest browser version

## System Architecture

### Application Structure
```
k4_web_app/
├── server.py              # FastAPI web server and WebSocket handler
├── config.py              # Centralized configuration management
├── connection.py          # K4 TCP connection and authentication
├── packet_handler.py      # K4 protocol packet processing
├── k4_commands.py         # Complete K4 CAT command implementation
├── panadapter.py          # Spectrum analyzer and waterfall processing
├── audio/                 # Audio processing modules
│   ├── decoder.py         # RX audio (Opus/PCM decoding)
│   ├── encoder.py         # TX audio (microphone processing)
│   ├── controls.py        # Audio routing and volume control
│   └── utils.py           # Audio debugging utilities
├── static/                # Frontend web interface
│   ├── index.html         # Main HTML template
│   ├── app.js             # Core JavaScript application logic
│   ├── config-loader.js   # Configuration management utilities
│   ├── panadapter.js      # Spectrum display and waterfall
│   ├── vfo-control.js     # VFO frequency controls
│   ├── sidebar.js         # Settings and radio management
│   └── styles.css         # Global CSS styles
└── radios/                # Multi-radio configuration system
    ├── radio_config.py    # Radio configuration management
    └── configs/           # Individual radio configuration files
```

### Communication Flow
1. **Web Browser** ↔ **FastAPI Server** (WebSocket + HTTPS)
2. **FastAPI Server** ↔ **K4 Radio** (TCP Port 9205)
3. **Audio Pipeline**: Browser → AudioWorklet → WebSocket → K4 Radio
4. **Control Pipeline**: Browser → WebSocket → CAT Commands → K4 Radio
5. **Panadapter Pipeline**: K4 Radio → Spectrum Data → WebSocket → Browser Canvas

### Protocol Details
- **K4 Protocol**: Binary packets with start/end markers (`\xFE\xFD\xFC\xFB...`)
- **Audio Encoding**: Opus 32-bit float at 12kHz sample rate
- **CAT Commands**: Kenwood-compatible text commands with K4 extensions
- **WebSocket**: JSON for control data, binary for audio data


## License

This project is open source. Please check the LICENSE file for specific terms.

## Support

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive setup and usage instructions in `CLAUDE.md`


### Known Limitations
- **Single K4 per instance**: Currently supports one K4 connection per server instance
- **Audio latency**: Typical 40-80ms latency for audio (acceptable for most use cases)
- **Browser compatibility**: Requires modern browser with WebRTC support
- **Network requirements**: Best performance with wired Ethernet connection

## Changelog

### Version 1.0.0
- Initial release with core K4 control functionality
- Real-time audio streaming with Opus encoding
- Panadapter display with K4-matching colors
- Complete CAT command support (219+ commands)
- Multi-radio configuration framework
- Modern responsive web interface

---

*K4 Web Controller - Remote control your Elecraft K4 from anywhere on your network.*