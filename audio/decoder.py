"""
K4 Audio RX Decoder Module

This module handles decoding of incoming audio from the K4 radio.
Supports multiple encoding modes (EM0-EM3) with custom K4-specific Opus processing.

CRITICAL: This code is moved exactly as-is from the working audio.py to preserve
all K4-specific modifications that make RX audio work correctly.
"""

import struct
import opuslib
import numpy as np

# Import centralized configuration
from config import audio_config, AudioMode

# Decoder for stereo float audio at 12 kHz
# IMPORTANT: Keep this exact configuration - it works with K4's audio stream
decoder = opuslib.Decoder(audio_config.OUTPUT_SAMPLE_RATE, 2)

def decode_opus_float(payload: bytes) -> bytes:
    """
    Decodes an AUDIO payload from the K4 with various encoding modes.
    Returns raw float32 PCM bytes interleaved as stereo (L/R), normalized to [-1.0, +1.0].
    
    CRITICAL: This function is moved exactly as-is from the working audio.py.
    Do not modify the K4-specific processing logic that makes RX audio work.
    """
    try:
        if len(payload) < 8:
            print("❌ Audio payload too short")  # ERROR_LOG: Keep critical errors
            return b""

        type_byte = payload[0]
        version = payload[1]
        seq = payload[2]

        if type_byte != 1:
            print(f"❌ Unexpected audio packet type: {type_byte}")  # ERROR_LOG: Keep type errors
            return b""

        mode = payload[3]
        
        frame_size = struct.unpack("<H", payload[4:6])[0]
        sample_rate = payload[6] if len(payload) > 6 else 0
        audio_data = payload[7:]

        if mode == AudioMode.EM0_RAW_32:  # EM0 - Raw 32-bit
            # 32-bit signed integers, stereo
            if len(audio_data) % 8 != 0:
                print("❌ Invalid 32-bit stereo data length")  # ERROR_LOG: Keep format errors
                return b""
            
            samples = len(audio_data) // 8
            raw_samples = struct.unpack(f"<{samples * 2}i", audio_data)
            
            # Convert to float32 and normalize
            float_samples = [s / audio_config.PCM_32BIT_SCALE for s in raw_samples]
            
        elif mode == AudioMode.EM1_RAW_16:  # EM1 - Raw 16-bit  
            
            # 16-bit signed integers, stereo
            if len(audio_data) % 4 != 0:
                print("❌ Invalid 16-bit stereo data length")  # ERROR_LOG: Keep format errors
                return b""
                
            samples = len(audio_data) // 4
            raw_samples = struct.unpack(f"<{samples * 2}h", audio_data)
            
            
            # Convert to float32 and normalize
            float_samples = [s / audio_config.PCM_16BIT_MAX for s in raw_samples]
            
            
        elif mode == AudioMode.EM2_OPUS_16:  # EM2 - Opus 16-bit
            
            try:
                # OPUS frame_size interpretation
                # K4 sends frame_size as "samples per channel" but OPUS decode expects total output samples
                # So for stereo: total_samples = frame_size * 2
                opus_frame_size = frame_size * 2  # Convert to total samples for OPUS
                
                pcm_samples = decoder.decode(audio_data, opus_frame_size)
                
                # Convert numpy array to list if needed, then to float32 and normalize
                if isinstance(pcm_samples, np.ndarray):
                    float_samples = (pcm_samples / audio_config.PCM_16BIT_MAX).tolist()
                else:
                    float_samples = [s / audio_config.PCM_16BIT_MAX for s in pcm_samples]
                
                
            except Exception as e:
                print(f"❌ Opus decode failed: {e}")  # ERROR_LOG: Keep decode errors
                return b""
                
        elif mode == AudioMode.EM3_OPUS_FLOAT:  # EM3 - Opus 32-bit float
            
            try:
                
                # 1. Use frame_size directly 
                # 2. Decode OPUS 
                # 3. Separate main/sub receiver audio (even/odd samples)
                # 4. Apply individual amplification 
                # 5. Mix according to audio routing settings
                
                # Decode OPUS for K4 radio reception
                pcm = decoder.decode_float(audio_data, frame_size)
                
                # Convert to numpy array
                stereo = np.frombuffer(pcm, dtype=np.float32)
                
                # K4 audio separation:
                # Even samples = main receiver (VFO A), Odd samples = sub receiver (VFO B)
                main_audio = stereo[0::2]  # even samples = VFO A / Main RX
                sub_audio = stereo[1::2]   # odd samples = VFO B / Sub RX
                
                # Apply individual receiver amplification
                # Default volumes (can be controlled from web interface)
                main_volume = getattr(decode_opus_float, 'main_volume', audio_config.DEFAULT_MAIN_VOLUME)
                sub_volume = getattr(decode_opus_float, 'sub_volume', audio_config.DEFAULT_SUB_VOLUME)
                sub_enabled = getattr(decode_opus_float, 'sub_enabled', audio_config.DEFAULT_SUB_ENABLED)
                audio_routing = getattr(decode_opus_float, 'audio_routing', audio_config.DEFAULT_AUDIO_ROUTING)
                
                main_audio = main_audio * main_volume * 32  # Apply VFO A volume + K4 gain
                sub_audio = sub_audio * sub_volume * 32     # Apply VFO B volume + K4 gain
                
                # K4 dual receiver audio routing logic
                # Possible routing settings:
                # 'a.b'   = main left, sub right (default stereo)
                # 'ab.ab' = mix both to both channels (mono mix)
                # 'a.-a'  = main left, main inverted right (binaural)
                # 'a.ab'  = main left, mix right
                # 'ab.b'  = mix left, sub right  
                # 'ab.a'  = mix left, main right
                # 'b.ab'  = sub left, mix right
                # 'b.b'   = sub both channels
                # 'b.a'   = sub left, main right (swapped stereo)
                # 'a.a'   = main both channels
                
                # If sub receiver is off, use main audio for both
                if not sub_enabled:
                    sub_audio = main_audio
                
                # Parse audio routing setting
                left_sel, right_sel = audio_routing.split('.')
                
                # Left channel selection
                if left_sel == 'a':
                    left_channel = main_audio
                elif left_sel == 'b':
                    left_channel = sub_audio
                elif left_sel == 'ab':
                    left_channel = (main_audio + sub_audio) / 2
                else:
                    left_channel = main_audio  # default
                
                # Right channel selection  
                if right_sel == 'b':
                    right_channel = sub_audio
                elif right_sel == 'a':
                    right_channel = main_audio
                elif right_sel == 'ab':
                    right_channel = (main_audio + sub_audio) / 2
                elif right_sel == '-a':
                    right_channel = -main_audio  # inverted main (binaural effect)
                else:
                    right_channel = sub_audio  # default
                
                # Calculate expected samples for our pipeline
                expected_frames = frame_size  # 480 frames
                
                # Handle resampling if needed for K4 audio
                actual_frames = len(left_channel)
                if actual_frames != expected_frames:
                    if actual_frames > expected_frames:
                        # Downsample by decimation
                        ratio = actual_frames // expected_frames
                        left_channel = left_channel[::ratio]
                        right_channel = right_channel[::ratio]
                    elif actual_frames < expected_frames:
                        # Upsample by repetition for K4 compatibility
                        ratio = expected_frames // actual_frames
                        left_channel = np.repeat(left_channel, ratio)
                        right_channel = np.repeat(right_channel, ratio)
                
                # Ensure exact sample count
                left_channel = left_channel[:expected_frames]
                right_channel = right_channel[:expected_frames]
                
                # Pad if needed
                if len(left_channel) < expected_frames:
                    padding = expected_frames - len(left_channel)
                    left_channel = np.concatenate([left_channel, np.zeros(padding)])
                    right_channel = np.concatenate([right_channel, np.zeros(padding)])
                
                # Interleave stereo samples for K4 output
                stereo_output = np.empty((len(left_channel) + len(right_channel),), dtype=np.float32)
                stereo_output[0::2] = left_channel   # even indices = left
                stereo_output[1::2] = right_channel  # odd indices = right
                
                float_samples = stereo_output.tolist()
                
                
            except Exception as e:
                print(f"❌ Opus float decode failed: {e}")  # ERROR_LOG: Keep decode errors
                return b""
                
        else:
            print(f"❌ Unsupported audio mode: {mode}")  # ERROR_LOG: Keep unsupported mode errors
            return b""

        # Validate we got samples
        if not float_samples:
            print("❌ No samples decoded")  # ERROR_LOG: Keep empty decode errors
            return b""

        # Apply normalization carefully
        max_amp = max(abs(s) for s in float_samples) if float_samples else 1.0
        if max_amp > 1.0:
            float_samples = [s / max_amp for s in float_samples]
        elif max_amp < 0.001:
            pass

        # Ensure we have even number of samples for stereo
        if len(float_samples) % 2 != 0:
            print(f"⚠️ Odd number of samples ({len(float_samples)}), padding with zero")
            float_samples.append(0.0)

        # Convert to bytes
        try:
            float_bytes = struct.pack(f"<{len(float_samples)}f", *float_samples)
        except struct.error as e:
            print(f"❌ Error packing float samples: {e}")  # ERROR_LOG: Keep packing errors
            return b""


        return float_bytes

    except Exception as e:
        print(f"❌ Audio decode error: {e}")  # ERROR_LOG: Keep general decode errors
        import traceback
        traceback.print_exc()
        return b""


# Initialize default settings for decode_opus_float function attributes
# CRITICAL: These must match the original audio.py settings exactly
decode_opus_float.main_volume = audio_config.DEFAULT_MAIN_VOLUME
decode_opus_float.sub_volume = audio_config.DEFAULT_SUB_VOLUME
decode_opus_float.sub_enabled = audio_config.DEFAULT_SUB_ENABLED
decode_opus_float.audio_routing = audio_config.DEFAULT_AUDIO_ROUTING

print("🎧 RX Audio decoder initialized")