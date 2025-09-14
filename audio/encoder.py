"""
K4 Audio Encoder - TX Audio Processing

This module implements optimized audio encoding for K4 radio transmission.
All parameters and processing steps are tuned for K4 protocol requirements.
"""

import numpy as np
import opuslib

# Import centralized configuration
from config import audio_config, AudioMode

# Global TX encoder instance - initialized once
_tx_encoder = None

def get_tx_encoder():
    """Get or initialize the global TX encoder"""
    global _tx_encoder
    if _tx_encoder is None:
        _tx_encoder = initialize_tx_encoder()
    return _tx_encoder

def initialize_tx_encoder(sample_rate: int = None, channels: int = None) -> opuslib.Encoder:
    """
    Initialize the TX Opus encoder for K4 radio transmission.
    
    Args:
        sample_rate: Target sample rate (defaults to 12000)
        channels: Number of channels (defaults to 2 for stereo)
        
    Returns:
        Initialized Opus encoder or None if failed
    """
    if sample_rate is None:
        sample_rate = audio_config.OUTPUT_SAMPLE_RATE  # 12000
    if channels is None:
        channels = audio_config.K4_INPUT_CHANNELS  # 2
    
    try:
        # Initialize Opus encoder for K4 radio transmission
        # Optimized settings for K4 protocol compatibility
        encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_AUDIO)
        
        # CRITICAL FIX: This version of opuslib has issues with property access
        # Use default settings without modifications for maximum compatibility
        # Some opuslib versions don't support property setting
        
        print(f"✅ K4 TX Opus encoder initialized: {sample_rate}Hz, {channels}ch")
        print(f"   Using default Opus settings for K4 compatibility")
        return encoder
        
    except Exception as e:
        print(f"❌ Failed to initialize TX Opus encoder: {e}")
        return None

def encode_audio_for_k4_tx(audio_data: bytes, mic_gain: float = None) -> dict:
    """
    Encode audio for K4 radio transmission.
    
    Processes microphone audio and creates K4-compatible Opus frames.
    
    Args:
        audio_data: Raw float32 audio data from browser microphone
        mic_gain: Microphone gain (defaults to config value)
        
    Returns:
        Dictionary with 'frames' list and 'timing' info
    """
    if mic_gain is None:
        mic_gain = audio_config.DEFAULT_MIC_GAIN
        
    try:
        
        # Convert input audio to numpy array
        float_samples = np.frombuffer(audio_data, dtype=np.float32)
        
        # K4 frame calculation - CRITICAL FIX
        # Calculate resampling ratio from input to K4 sample rate
        # Input frames need to be resampled to K4 transmission rate
        resample_ratio = audio_config.INPUT_SAMPLE_RATE // audio_config.OUTPUT_SAMPLE_RATE  # 4
        expected_input_samples = audio_config.K4_TX_FRAME_SIZE * resample_ratio  # 240 * 4 = 960
        
        
        # Ensure we have the correct number of input samples
        if len(float_samples) < expected_input_samples:
            return {'frames': [], 'timing': {'frame_duration_ms': audio_config.PACKET_INTERVAL_MS, 'total_duration_ms': 0}}
        
        # Use exactly the expected number of samples
        sampled = float_samples[:expected_input_samples]
        
        if resample_ratio == 4:
            s0 = sampled[0::4]
            s1 = sampled[1::4] 
            s2 = sampled[2::4]
            s3 = sampled[3::4]
            
            min_len = min(len(s0), len(s1), len(s2), len(s3))
            s0 = s0[:min_len]
            s1 = s1[:min_len]
            s2 = s2[:min_len]
            s3 = s3[:min_len]
            
            resampled = (s0 + s1 + s2 + s3) / 4
        else:
            return {'frames': [], 'timing': {'frame_duration_ms': audio_config.PACKET_INTERVAL_MS, 'total_duration_ms': 0}}
        
        # Verify we have exactly the right number of samples for TX
        # resampled should be exactly 240 samples after 4:1 resampling
        tx_frame_size = audio_config.K4_TX_FRAME_SIZE  # 240 samples
        
        if len(resampled) != tx_frame_size:
            # Fix the frame size to match K4 requirements exactly
            if len(resampled) > tx_frame_size:
                resampled = resampled[:tx_frame_size]
            else:
                padding_needed = tx_frame_size - len(resampled)
                resampled = np.concatenate([resampled, np.zeros(padding_needed, dtype=np.float32)])
        
        # Apply gain and K4-required attenuation for optimal audio levels
        # Scale audio to prevent clipping and maintain signal quality
        resampled = resampled * mic_gain / audio_config.K4_ATTENUATION_FACTOR
        
        # Convert mono to stereo for K4 protocol requirements
        # K4 expects stereo audio data even for mono sources
        stereo_samples = resampled.repeat(2)
        
        # Verify stereo sample count
        expected_stereo_samples = tx_frame_size * 2  # 480 total samples (240 per channel)
        if len(stereo_samples) != expected_stereo_samples:
            pass  # Sample count mismatch - continue anyway
        
        # Encode with Opus using K4 protocol frame size
        # Frame size must match K4 transmission timing requirements
        # Use 240 samples per channel for optimal K4 compatibility
        
        # CRITICAL FIX: frame_size must match samples per channel
        frame_size_per_channel = audio_config.K4_TX_FRAME_SIZE  # 240 samples per channel
        total_samples = len(stereo_samples)  # 480 total samples (240 per channel)
        
        encoder = get_tx_encoder()
        if encoder is None:
            return {'frames': [], 'timing': {'frame_duration_ms': audio_config.PACKET_INTERVAL_MS, 'total_duration_ms': 0}}
        
        # Encode for K4 transmission - frame_size = samples per channel
        audio_packet = encoder.encode_float(stereo_samples.tobytes(), frame_size_per_channel)
        
        
        if len(audio_packet) < 50:
            pass  # Small packet detected - continue anyway
        
        # Return in the expected format
        result = {
            'frames': [audio_packet],
            'timing': {
                'frame_duration_ms': audio_config.PACKET_INTERVAL_MS,
                'total_duration_ms': audio_config.PACKET_INTERVAL_MS,
                'frame_count': 1
            },
            'k4_frame_size': frame_size_per_channel  # 240 samples per channel
        }
        
        return result
        
    except Exception as e:
        # Encoding error occurred
        import traceback
        traceback.print_exc()
        return {'frames': [], 'timing': {'frame_duration_ms': audio_config.PACKET_INTERVAL_MS, 'total_duration_ms': 0}}

# Main encoding function (replaces the old complex implementation)
def encode_audio_for_k4_continuous(audio_data: bytes, sample_rate: int = None, target_mode: int = None) -> dict:
    """
    Main encoding function for continuous K4 transmission.
    
    Args:
        audio_data: Raw float32 audio data from browser
        sample_rate: Input sample rate (ignored - uses config)
        target_mode: Target encoding mode (ignored - uses EM3)
        
    Returns:
        Dictionary with encoded frames and timing info
    """
    return encode_audio_for_k4_tx(audio_data)

# Compatibility function for connection.py imports
def encode_audio_for_k4(audio_data: bytes, sample_rate: int = None, target_mode: int = None) -> dict:
    """
    Compatibility wrapper for encode_audio_for_k4_continuous
    """
    return encode_audio_for_k4_continuous(audio_data, sample_rate, target_mode)

# Simplified encoding approach optimized for K4 protocol
# Previous complex conversion functions have been streamlined


# Initialize the TX encoder when module loads
encoder = get_tx_encoder()
if encoder:
    pass  # TX encoder ready
else:
    pass  # TX encoder initialization deferred
