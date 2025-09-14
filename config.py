"""
K4 Web Control - Centralized Configuration Module

This module contains all configuration constants and settings used throughout
the K4 Web Control application to ensure consistency and prevent conflicts.
"""

class AudioConfig:
    """Audio-related configuration constants"""
    
    # Sample rates
    INPUT_SAMPLE_RATE = 48000   # From browser AudioWorklet
    OUTPUT_SAMPLE_RATE = 12000  # To K4 radio
    DECIMATION_FACTOR = INPUT_SAMPLE_RATE // OUTPUT_SAMPLE_RATE  # 4:1
    
    # Frame sizes (TX and RX are different!)
    K4_TX_FRAME_SIZE = 240      # TX frame size (samples per channel - K4 optimized)
    K4_RX_FRAME_SIZE = 480      # RX frame size (decoder working - don't change)
    WORKLET_FRAME_SIZE = 960    # Samples at 48kHz (20ms of audio)
    
    # Legacy compatibility (use RX frame size to keep decoder working)
    K4_FRAME_SIZE = K4_RX_FRAME_SIZE
    OPUS_FRAME_SIZE = K4_FRAME_SIZE * 2  # Total samples for Opus (stereo)
    
    # Opus encoder settings
    OPUS_BITRATE = 64000        # 64 kbps - valid Opus bitrate (was 384000 - invalid)
    OPUS_COMPLEXITY = 10        # Maximum quality
    OPUS_VBR = True            # Variable bitrate enabled
    
    # K4 protocol settings
    DEFAULT_MODE = 3            # EM3 Opus Float
    PACKET_INTERVAL_MS = 20     # 20ms per packet
    
    # Audio processing defaults
    DEFAULT_MAIN_VOLUME = 1.0   # VFO A volume
    DEFAULT_SUB_VOLUME = 1.0    # VFO B volume
    DEFAULT_SUB_ENABLED = False # Sub receiver off by default
    DEFAULT_AUDIO_ROUTING = 'a.b'  # Main left, Sub right
    
    # PTT settings
    DEFAULT_MIC_GAIN = 0.1      # 10% default (matches HTML)
    PTT_TIMEOUT_SECONDS = 10    # Safety timeout for PTT
    
    # K4 radio protocol constants
    K4_ATTENUATION_FACTOR = 4   # Divide by 4 for proper K4 levels (reduced for more mic gain)
    K4_INPUT_CHANNELS = 2       # K4 requires stereo input
    
    # Audio data type conversion constants
    PCM_16BIT_MAX = 32767          # 2^15 - 1 (max signed 16-bit value)
    PCM_32BIT_SCALE = 2147483648.0 # 2^31 (32-bit to float conversion divisor)


class K4Config:
    """K4 radio connection configuration"""
    
    # Connection settings
    DEFAULT_HOST = "192.168.1.10"
    DEFAULT_PORT = 9205
    DEFAULT_PASSWORD = "tester"
    
    # Protocol markers
    START_MARKER = b'\xFE\xFD\xFC\xFB'
    END_MARKER = b'\xFB\xFC\xFD\xFE'
    
    # Command settings
    KEEPALIVE_INTERVAL = 2      # Seconds between PING commands
    CONNECTION_TIMEOUT = 10     # Seconds before dropping idle clients
    
    # Initial commands sent on connection
    INIT_COMMANDS = [
        "RDY;",      # Ready command - triggers comprehensive state dump
        "K41;",      # Request K4 to respond in advanced mode
        "EM3;",      # Set to Opus Float mode (EM3) for TX audio
        "AI4;",      # Enable Auto Information mode 4 - CRITICAL for real-time updates
        "ER1;",      # Request long format error messages
        # Add back key queries to ensure we get current state
        "FA;",       # Request VFO A frequency
        "FB;",       # Request VFO B frequency
        "MD;",       # Request VFO A mode
        "MD$;",      # Request VFO B mode
        "NB;",       # Request VFO A Noise Blanker state
        "NB$;",      # Request VFO B Noise Blanker state
        "NR;",       # Request VFO A Noise Reduction state
        "NR$;",      # Request VFO B Noise Reduction state
        "SB;",       # Request Sub Receiver state
        "FP;",       # Request filter path - CRITICAL for filter buttons
        "FP$;",      # Request sub receiver filter path
        "BW;",       # Request VFO A bandwidth
        "BW$;",      # Request VFO B bandwidth
        "#REF;",     # Request panadapter reference level - CRITICAL for waterfall
        "#SPN50000;", # Request panadapter span (50 kHz)
    ]



class PanadapterConfig:
    """Panadapter display configuration"""
    
    # Display settings
    DEFAULT_CENTER_FREQ = 14086500  # Hz
    DEFAULT_SPAN = 50000           # Hz (50 kHz)
    DEFAULT_REF_LEVEL = -110        # dBm (good default for K4)
    DEFAULT_SCALE = 70             # dB scale (good default for K4)
    DEFAULT_NOISE_FLOOR = -120     # dBm
    
    # Waterfall settings
    MAX_WATERFALL_LINES = 200
    WATERFALL_HISTORY_SIZE = 50   # Lines to send to frontend
    DEFAULT_WATERFALL_HEIGHT = 237  # Default waterfall display height in pixels
    
    # User preference defaults for averaging
    DEFAULT_SPECTRUM_AVERAGING = 4   # Default spectrum averaging factor
    DEFAULT_WATERFALL_AVERAGING = 2  # Default waterfall averaging factor
    
    # Decompression settings
    DB_MIN = -150.0               # Minimum dB value
    DB_MAX = -20.0                # Maximum dB value
    DB_RANGE = 130.0              # Total dB range
    
    # Waterfall color thresholds (dBm) - K4-matching palette
    WATERFALL_PINK_THRESHOLD = -185    # Pink/Salmon background (weakest)
    WATERFALL_ORANGE_THRESHOLD = -180  # Orange/Tangerine transition  
    WATERFALL_GREEN_THRESHOLD = -160   # Lime Green background
    WATERFALL_BLUE_THRESHOLD = -145    # Greenish Blue transition
    WATERFALL_ROYAL_THRESHOLD = -130   # Royal Blue background  
    WATERFALL_BLACK_THRESHOLD = -120   # Black background (strongest)


class WebConfig:
    """Web interface configuration"""
    
    # Server settings
    DEFAULT_PORT = 8000
    STATIC_DIR = "static"
    
    # VFO frequency limits (Hz)
    VFO_FREQ_MIN = 1000000    # 1 MHz minimum
    VFO_FREQ_MAX = 30000000   # 30 MHz maximum
    
    # WebSocket settings
    WS_MAX_ERRORS = 10            # Maximum consecutive errors before disconnect
    
    # Audio buffering
    DEFAULT_BUFFER_SIZE = 3       # Target buffer size for smooth playback
    DEFAULT_MASTER_VOLUME = 1.5   # 150% default volume (internal scale 0-300)
    
    # Volume control settings (user-facing 0-100 scale)
    VOLUME_USER_MIN = 0           # User minimum volume (0%)
    VOLUME_USER_MAX = 100         # User maximum volume (100%)
    VOLUME_INTERNAL_MIN = 0       # Internal minimum volume
    VOLUME_INTERNAL_MAX = 200     # Internal maximum volume (for main/sub)
    VOLUME_MASTER_INTERNAL_MAX = 300  # Internal maximum for master volume
    
    # Default user volume settings (0-100 scale)
    DEFAULT_USER_MAIN_VOLUME = 10     # 10% = 50 internal
    DEFAULT_USER_SUB_VOLUME = 10      # 10% = 50 internal  
    DEFAULT_USER_MASTER_VOLUME = 10   # 10% = 30 internal (matches main/sub)
    
    # CORS configuration
    CORS_ALLOWED_ORIGINS = [
        "https://localhost:8000",
        "http://localhost:8000",
        "https://127.0.0.1:8000", 
        "http://127.0.0.1:8000"
    ]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOWED_METHODS = ["GET", "POST"]
    CORS_ALLOWED_HEADERS = ["*"]


# Packet type constants (from K4 protocol)
class PacketType:
    CAT = 0
    AUDIO = 1
    PAN = 2
    MINI_PAN = 3


# Audio encoding modes (from K4 protocol)
class AudioMode:
    EM0_RAW_32 = 0    # Raw 32-bit
    EM1_RAW_16 = 1    # Raw 16-bit
    EM2_OPUS_16 = 2   # Opus 16-bit
    EM3_OPUS_FLOAT = 3  # Opus 32-bit float (default)
    
    @staticmethod
    def get_name(mode):
        names = {
            0: 'EM0 (Raw 32-bit)',
            1: 'EM1 (Raw 16-bit)',
            2: 'EM2 (Opus 16-bit)',
            3: 'EM3 (Opus Float)'
        }
        return names.get(mode, f'Unknown ({mode})')


# CAT command mode mapping
CAT_MODE_MAP = {
    '1': 'LSB',
    '2': 'USB',
    '3': 'CW',
    '4': 'FM',
    '5': 'AM',
    '6': 'DATA',
    '7': 'CW-R',
    '9': 'DATA-R'
}


# Global instance for easy access
audio_config = AudioConfig()
k4_config = K4Config()
pan_config = PanadapterConfig()
web_config = WebConfig()

print("⚙️ K4 Configuration module loaded")
print(f"   Audio: {audio_config.INPUT_SAMPLE_RATE}Hz → {audio_config.OUTPUT_SAMPLE_RATE}Hz")
print(f"   Frame size: {audio_config.K4_FRAME_SIZE} samples/channel")
print(f"   K4: {k4_config.DEFAULT_HOST}:{k4_config.DEFAULT_PORT}")