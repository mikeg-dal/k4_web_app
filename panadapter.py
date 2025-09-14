"""
K4 Panadapter Module - Clean Version
Processes spectrum data from the K4 radio and provides spectrum/waterfall display data.

CLEANED VERSION: Using centralized debug_helper and config
"""

import struct
import time
import json
from typing import Dict, List, Optional, Tuple

# Import centralized configuration
from config import pan_config, audio_config

# Import debug helper for controlled debugging
from debug_helper import debug_print, is_debug_enabled

class K4Panadapter:
    """
    K4 Panadapter processor with accurate decompression and realistic dB values.
    
    Features:
    - Accurate decompression formula for proper dB representation
    - Variable reference level (configurable, not hardcoded)
    - Proper signal level mapping  
    - Broad spectrum monitoring support
    """
    
    def __init__(self):
        # INITIALIZATION FIX: Don't use defaults - wait for K4 to tell us actual values
        self.center_frequency = 0  # Will be set by first K4 packet
        self.span = 50000          # Default to 50 kHz to prevent 0 span issues
        self.reference_level = 0   # Will be set by #REF response (display reference level)
        self.hardware_ref_level = 0  # Hardware reference level from #HREF (for debugging)  
        self.noise_floor = pan_config.DEFAULT_NOISE_FLOOR  # OK to default
        self.scale_setting = pan_config.DEFAULT_SCALE      # OK to default
        
        # VFO frequencies - will be set by FA/FB responses
        self.vfo_a_frequency = 0
        self.vfo_b_frequency = 0
        
        # Filter state - IS/BW values from K4
        self.filter_state = {
            'A': {'is_value': 0, 'bw_value': 0, 'mode': 'hilo', 'pitch': 50},  # Default 500Hz pitch
            'B': {'is_value': 0, 'bw_value': 0, 'mode': 'hilo', 'pitch': 50}   # Default 500Hz pitch
        }
        
        # Waterfall data storage
        self.waterfall_data = []
        self.max_waterfall_lines = pan_config.MAX_WATERFALL_LINES
        
        # Performance tracking
        self.pan_fps = 0
        self.last_pan_time = time.time()
        
        debug_print("PANADAPTER", "🖥️ K4 Panadapter initialized with accurate decompression")
    
    def update_span_from_cat(self, span_hz: int) -> None:
        """
        Update span setting from CAT command.
        Only triggers boundary updates when span actually changes.
        
        Args:
            span_hz: Span in Hz from #SPN command (e.g., 50000 for 50 kHz)
        """
        # Validate span value to prevent corruption
        if span_hz <= 0:
            debug_print("CRITICAL", f"❌ Invalid span value: {span_hz} Hz - ignoring")
            return
        
        # Check if span actually changed
        old_span = self.span
        self.span = span_hz  # Already in Hz
        
        # INITIALIZATION FIX: Treat any update from 0 or significantly different value as a change
        # This handles both initialization (0 → valid span) and user changes
        span_changed = (old_span != span_hz) or (old_span == 0)
        
        debug_print("PANADAPTER", f"📏 Span from CAT: {span_hz} Hz = {self.span/1000:.1f} kHz (old: {old_span/1000:.1f} kHz, changed: {span_changed})")
        
        # SIMPLE APPROACH: No immediate boundary updates for span commands
        # Let boundary updates happen when spectrum data actually changes with new bin counts
        debug_print("CRITICAL", f"📏 Span updated to {span_hz/1000:.1f} kHz - boundary updates will happen when spectrum data changes")
    
    def update_display_boundaries(self) -> Dict:
        """
        DYNAMIC BOUNDARY CALCULATION: Calculate current display boundaries
        using current center frequency and span, regardless of source.
        
        Returns current frequency boundaries for immediate frontend update.
        """
        if self.center_frequency == 0 or self.span == 0:
            # Not enough data yet
            return {}
        
        # Calculate display boundaries using current span (what user requested)
        display_start_freq = self.center_frequency - (self.span / 2)
        display_end_freq = self.center_frequency + (self.span / 2)
        
        # Get expected K4 sample rate for this span (using discovered boundaries)
        span_khz = self.span / 1000
        if span_khz <= 19:
            expected_sample_rate = 24  # Tier 1
        elif span_khz <= 36:
            expected_sample_rate = 48  # Tier 2
        elif span_khz <= 82:
            expected_sample_rate = 96  # Tier 3
        elif span_khz <= 172:
            expected_sample_rate = 192  # Tier 4
        else:
            expected_sample_rate = 384  # Tier 5
        
        boundaries = {
            'center_frequency': self.center_frequency,
            'span': self.span,
            'actual_start_freq': display_start_freq,
            'actual_end_freq': display_end_freq,
            'expected_sample_rate': expected_sample_rate,
            'timestamp': time.time()
        }
        
        debug_print("CRITICAL", f"🎯 DYNAMIC BOUNDARIES UPDATED:")
        debug_print("CRITICAL", f"   Center: {self.center_frequency/1e6:.6f} MHz")
        debug_print("CRITICAL", f"   Span: {self.span/1000:.1f} kHz")
        debug_print("CRITICAL", f"   Range: {display_start_freq/1e6:.6f} - {display_end_freq/1e6:.6f} MHz")
        debug_print("CRITICAL", f"   Expected K4 tier: {expected_sample_rate} kHz sample rate")
        
        # Store the latest boundaries for other modules to access
        self.latest_boundaries = boundaries
        
        return boundaries
    
    def get_latest_boundaries(self) -> Dict:
        """Get the latest calculated boundaries for immediate WebSocket updates"""
        return getattr(self, 'latest_boundaries', {})
    
    def _notify_boundary_update(self, boundaries: Dict):
        """
        Store boundary update for retrieval by packet handler.
        This is a simple approach that avoids circular imports.
        """
        # Store the boundary update with a flag for packet handler to check
        self.pending_boundary_update = boundaries
        debug_print("CRITICAL", f"🎯 Boundary update pending for WebSocket clients")
    
    def get_pending_boundary_update(self) -> Optional[Dict]:
        """
        Get and clear any pending boundary update for WebSocket transmission.
        Returns None if no update is pending.
        """
        if hasattr(self, 'pending_boundary_update'):
            update = self.pending_boundary_update
            delattr(self, 'pending_boundary_update')
            return update
        return None
    
    def process_pan_packet(self, payload: bytes) -> Optional[Dict]:
        """
        Process a PAN packet from the K4 and return spectrum data.
        Accurate dB decompression for spectrum data.
        """
        try:
            if len(payload) < 8:
                debug_print("CRITICAL", "❌ PAN payload too short")
                return None
            
            # Parse according to K4-Remote Protocol Rev. A1
            # The payload structure is:
            # Byte 0: TYPE (should be 2 for PAN)
            # Byte 1: VER (version)
            # Byte 2: SEQ (sequence)
            # Byte 3+: PAN specific data
            
            pkt_type = payload[0]   # TYPE (should be 2)
            version = payload[1]    # VER  
            sequence = payload[2]   # SEQ
            
            # Reduced logging: only every 50th packet
            if sequence % 50 == 0:
                debug_print("CRITICAL", f"📋 PAN Packet #{sequence}: TYPE={pkt_type}, VER={version}")
            
            if pkt_type != 2:
                debug_print("CRITICAL", f"❌ Wrong packet type: {pkt_type}, expected 2 (PAN)")
                return None
            
            # Now parse PAN-specific data starting from byte 3
            pan_data_offset = 3
            if len(payload) < pan_data_offset + 24:
                debug_print("CRITICAL", f"❌ PAN payload too short: {len(payload)} bytes (need {pan_data_offset + 24}+)")
                return None
            
            try:
                # Parse PAN data according to K4-Remote Protocol Rev. A1
                # Starting from offset 3 (after general header)
                pan_type = payload[pan_data_offset + 0]           # Byte 0: Type (PAN payload type)
                rx_receiver = payload[pan_data_offset + 1]        # Byte 1: RX Receiver (0 or 1)
                pan_data_length = struct.unpack('<H', payload[pan_data_offset + 2:pan_data_offset + 4])[0]  # Byte 2-3: PAN Data Length (16-bit unsigned, little-endian)
                # Byte 4-7: Reserved
                center_frequency = struct.unpack('<q', payload[pan_data_offset + 8:pan_data_offset + 16])[0]  # Byte 8-15: Center Frequency (signed 64-bit, little-endian)
                sample_rate = struct.unpack('<i', payload[pan_data_offset + 16:pan_data_offset + 20])[0]      # Byte 16-19: Sample Rate (signed 32-bit, little-endian)
                noise_floor = struct.unpack('<i', payload[pan_data_offset + 20:pan_data_offset + 24])[0]      # Byte 20-23: Noise Floor (signed 32-bit, little-endian)
                
                # Debug logging disabled - frequency mapping fixed
                
                # FILTER: Only process Main PAN (RX Receiver = 0), ignore Sub PAN (RX Receiver = 1)
                if rx_receiver != 0:
                    # Only log Sub PAN skipping every 100th time to reduce spam
                    if sequence % 100 == 0:
                        debug_print("CRITICAL", f"⏭️ SKIPPING Sub PAN (RX Receiver = {rx_receiver})")
                    return None
                
                # Only log Main PAN processing every 2000th time
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"✅ Processing Main PAN (RX Receiver = 0)")
                
                # Use the panadapter DISPLAY reference level (from #REF commands) for waterfall colors
                # This is what the user adjusts on the K4 for viewing preference
                # Keep the noise floor calculation for debugging but don't use it for display
                calculated_ref = (noise_floor / 10.0) if noise_floor != 0 else 0
                ref_value = self.reference_level  # Always use the display reference level
                
                # Only log reference level usage every 2000th time
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"🔧 Reference levels: Calculated={calculated_ref} dBm, Display={ref_value} dBm (using Display)")
                
            except Exception as e:
                debug_print("CRITICAL", f"❌ K4 protocol parsing failed: {e}")
                debug_print("CRITICAL", f"🔍 Raw packet analysis:")
                
                # Show raw bytes for debugging
                if len(payload) >= 32:
                    for i in range(0, min(32, len(payload)), 4):
                        chunk = payload[i:i+4]
                        values = [f"{b:02x}" for b in chunk]
                        debug_print("CRITICAL", f"   Offset {i:2d}: {' '.join(values)} | {list(chunk)}")
                
                return None
            
            # Extract compressed spectrum data from correct offset (after PAN header)
            spectrum_data_offset = pan_data_offset + 24  # General header (3) + PAN header (24) = 27
            spectrum_payload = payload[spectrum_data_offset:spectrum_data_offset + pan_data_length] if len(payload) >= spectrum_data_offset + pan_data_length else payload[spectrum_data_offset:]
            
            # Reduced packet logging - only every 50th packet
            if sequence % 50 == 0:
                debug_print("PANADAPTER", f"📡 K4 PACKET: TYPE={pkt_type}, SEQ={sequence}, center={center_frequency/1e6:.3f}MHz, {len(spectrum_payload)} bytes")
            # Show raw packet bytes for first few packets only
            if sequence < 3:
                raw_sample = list(payload[:32]) if len(payload) >= 32 else list(payload)
                debug_print("CRITICAL", f"   - raw packet sample: {raw_sample}")
            
            # Accurate decompression with proper signal handling
            # Reduced decompression logging
            if sequence % 100 == 0:
                debug_print("PANADAPTER", f"🔧 Decompressing {len(spectrum_payload)} bytes")
            decompressed_spectrum = self._decompress_spectrum(spectrum_payload, sequence)
            
            if not decompressed_spectrum:
                debug_print("CRITICAL", f"❌ Failed to decompress spectrum data - got empty result")
                debug_print("CRITICAL", f"   - spectrum_payload length: {len(spectrum_payload)}")
                debug_print("CRITICAL", f"   - pan_data_length: {pan_data_length}")
                return None
            
            # Only log decompression success every 2000th time
            if sequence % 2000 == 0:
                debug_print("CRITICAL", f"✅ Successfully decompressed {len(decompressed_spectrum)} spectrum bins")
            
            # Update internal state
            old_center = self.center_frequency
            self.center_frequency = center_frequency
            
            # Add to waterfall history
            self.waterfall_data.append({
                'data': decompressed_spectrum.copy(),
                'timestamp': time.time()
            })
            
            # Limit waterfall history
            if len(self.waterfall_data) > self.max_waterfall_lines:
                self.waterfall_data.pop(0)
            
            # CORRECTED: Use K4's actual span data for accurate frequency mapping
            k4_actual_span = sample_rate * 1000 if sample_rate > 0 else self.span
            
            # SIMPLIFIED UPDATE: Only update boundaries on center frequency changes
            # Span-related boundary updates will be handled through other mechanisms
            if old_center != center_frequency and old_center != 0:
                boundaries = self.update_display_boundaries()
                if boundaries:
                    self._notify_boundary_update(boundaries)
                    debug_print("CRITICAL", f"🎯 Center frequency changed from {old_center/1e6:.6f} to {center_frequency/1e6:.6f} MHz - boundaries updated")
            
            # SELECTIVE BIN PROCESSING: Extract only bins representing the requested span
            # Problem: K4 often sends more data than requested (e.g., 80kHz when you ask for 50kHz)
            # Solution: Extract center bins that represent exactly your requested span
        
            
            # Only log every 2000th packet to reduce performance impact
            if sequence % 2000 == 0:
                debug_print("CRITICAL", f"🔧 K4 DATA: Requested {self.span/1000:.1f}kHz, K4 sends {k4_actual_span/1000:.1f}kHz, {len(decompressed_spectrum)} bins")
            
            # Apply selective bin processing when K4 sends more data than requested
            if k4_actual_span > self.span and len(decompressed_spectrum) > 100 and self.span > 0 and k4_actual_span > 0:
                # K4 sent more data than requested - extract center bins for requested span
                total_bins = len(decompressed_spectrum)
                
                # Calculate how many bins represent the requested span exactly
                # Example: Want 50kHz from 80kHz with 800 bins → need (50/80)*800 = 500 bins
                requested_bins = int((self.span / k4_actual_span) * total_bins)
                requested_bins = max(50, min(requested_bins, total_bins))  # Safety bounds
                
                # Extract center bins that represent exactly the requested frequency span
                center_start = (total_bins - requested_bins) // 2
                center_end = center_start + requested_bins
                selective_spectrum = decompressed_spectrum[center_start:center_end]
                
                # Use the selectively processed data
                decompressed_spectrum = selective_spectrum
                effective_span = self.span  # Now maps exactly to requested span
                
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"🎯 SELECTIVE BIN PROCESSING:")
                    debug_print("CRITICAL", f"   K4 sent: {k4_actual_span/1000:.1f} kHz ({total_bins} bins)")
                    debug_print("CRITICAL", f"   Extracted: {effective_span/1000:.1f} kHz ({len(decompressed_spectrum)} bins)")
                    debug_print("CRITICAL", f"   Resolution: {effective_span/len(decompressed_spectrum):.1f} Hz/bin")
                    debug_print("CRITICAL", f"   Center bins: {center_start} to {center_end}")
            else:
                # Use all available data (K4 span matches request or close enough)
                effective_span = k4_actual_span
                
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"🎯 USING FULL K4 DATA:")
                    debug_print("CRITICAL", f"   K4 span: {k4_actual_span/1000:.1f} kHz matches request")
            
            # FREQUENCY MAPPING: Calculate boundaries using effective span
            final_bins = len(decompressed_spectrum)
            
            if final_bins > 0:
                # Calculate frequency boundaries using effective span (after selective processing)
                display_start_freq = center_frequency - (effective_span / 2)
                display_end_freq = center_frequency + (effective_span / 2)
                final_effective_span = effective_span
                
                # Only log span calculation every 2000th time
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"🔧 FINAL FREQUENCY MAPPING:")
                    debug_print("CRITICAL", f"   Display span: {final_effective_span/1000:.1f} kHz ({final_bins} bins)")
                    debug_print("CRITICAL", f"   Hz/bin: {final_effective_span/final_bins:.2f}")
                    debug_print("CRITICAL", f"   Display range: {display_start_freq/1e6:.6f} - {display_end_freq/1e6:.6f} MHz")
            else:
                final_effective_span = k4_actual_span
                if sequence % 2000 == 0:
                    debug_print("CRITICAL", f"🔧 FALLBACK: Using K4 actual span {k4_actual_span/1000:.1f} kHz")
            
            # Create spectrum data packet for frontend - CORRECTED WITH ACTUAL FREQUENCY BOUNDARIES
            spectrum_packet = {
                'type': 'spectrum_data',
                'center_frequency': center_frequency,
                'span': final_effective_span,  # K4's actual effective span after trimming
                'sample_rate': sample_rate,
                'noise_floor': self.noise_floor,
                'reference_level': ref_value if ref_value != 0 else self.reference_level,
                'spectrum_data': decompressed_spectrum,  # Trimmed spectrum data
                'receiver_id': f'Main_RX{rx_receiver}',
                'timestamp': time.time(),
                'bins': len(decompressed_spectrum),
                'waterfall_data': self.waterfall_data[-pan_config.WATERFALL_HISTORY_SIZE:] if len(self.waterfall_data) > pan_config.WATERFALL_HISTORY_SIZE else self.waterfall_data,
                'source': 'PAN',
                # CORRECTED: Include precise frequency boundaries from selective processing
                'actual_start_freq': display_start_freq if final_bins > 0 else center_frequency - (final_effective_span / 2),
                'actual_end_freq': display_end_freq if final_bins > 0 else center_frequency + (final_effective_span / 2),
                'k4_actual_span': k4_actual_span,  # Original K4 span before trimming
                'requested_span': self.span  # What user originally requested
            }
            
            # Reduced success logging - only every 200th packet
            if sequence % 200 == 0:
                debug_print("PANADAPTER", f"✅ PAN #{sequence}: {center_frequency/1e6:.3f} MHz, {len(decompressed_spectrum)} bins, range: {min(decompressed_spectrum):.1f} to {max(decompressed_spectrum):.1f} dB")
            
            return spectrum_packet
            
        except Exception as e:
            debug_print("CRITICAL", f"❌ Error processing PAN packet: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _decompress_spectrum(self, compressed_data: bytes, sequence: int = 0) -> List[float]:
        """
        Accurate decompression based on K4-Remote Protocol Rev. A1.
        
        Official decompression formula:
        int min = -160;
        for(i=0; i < count; i++) {
            v = ( values[i] + min ) * 10;
        }
        """
        if not compressed_data:
            return []
            
        try:
            # Initialize spectrum_data first
            spectrum_data = []
            
            # K4 DECOMPRESSION FORMULA - Protocol appears to have error
            # Protocol says: v = (values[i] + (-160)) * 10
            # But user data shows reasonable dB values (-145 to -98) without * 10
            # Keeping current working formula for now
            min_val = -160  # From protocol: int min = -160;
            
            for i, byte_val in enumerate(compressed_data):
                # Using simplified formula that produces realistic dB values
                display_db = byte_val + min_val  # -160 + 15 = -145 dB (realistic)
                
                spectrum_data.append(float(display_db))
                
                # Minimal logging - only for first packet
                if i < 3 and len(spectrum_data) <= 3:
                    debug_print("PANADAPTER", f"🔧 Decompression[{i}]: byte={byte_val} → {display_db} dB")
            
            # Minimal completion logging - only every 2000th packet
            if spectrum_data and len(spectrum_data) > 0:
                # Only log spectrum analysis every 2000th time
                if not hasattr(self, '_last_log_sequence') or (sequence - self._last_log_sequence) >= 2000:
                    debug_print("CRITICAL", f"📊 Spectrum range: {min(spectrum_data):.1f} to {max(spectrum_data):.1f} dB")
                    unique_levels = len(set([round(x) for x in spectrum_data]))
                    debug_print("CRITICAL", f"📊 Unique dB levels: {unique_levels} (diversity check)")
                    self._last_log_sequence = sequence
                
                # PERFORMANCE OPTIMIZATION: Skip detailed edge analysis - now that trimming is working
                debug_print("SPECTRUM", f"✅ PROCESSED: Using {len(spectrum_data)} bins from selective processing")
            
            return spectrum_data
            
        except Exception as e:
            debug_print("CRITICAL", f"❌ Error in K4 official decompression: {e}")
            return []
    
    def process_mini_pan_packet(self, payload: bytes) -> Optional[Dict]:
        """
        Process MINI-PAN packet - DISABLED for broad spectrum monitoring.
        """
        debug_print("PANADAPTER", f"📉 MINI-PAN packet received but SKIPPED for broad spectrum monitoring")
        return None  # Skip MINI-PAN processing
    
    def set_reference_level(self, level: int):
        """Set reference level (this should work now)"""
        self.reference_level = max(-200, min(60, level))
        debug_print("PANADAPTER", f"📏 Reference level set to: {self.reference_level} dBm")
    
    def set_span(self, span_hz: int):
        """Set panadapter span"""
        self.span = max(6000, min(368000, span_hz))
        debug_print("PANADAPTER", f"↔️ Span set: {self.span/1000:.0f} kHz")
    
    def set_scale_setting(self, scale: int):
        """Set scale setting"""
        self.scale_setting = max(10, min(150, scale))
        debug_print("PANADAPTER", f"📏 Scale setting updated: {self.scale_setting}")
    
    def update_vfo_frequency(self, vfo: str, frequency: int):
        """Update VFO frequency for cursor display"""
        if vfo.upper() == 'A':
            self.vfo_a_frequency = frequency
            debug_print("PANADAPTER", f"📻 VFO A updated: {frequency/1e6:.6f} MHz")
        elif vfo.upper() == 'B':
            self.vfo_b_frequency = frequency
            debug_print("PANADAPTER", f"📻 VFO B updated: {frequency/1e6:.6f} MHz")
    
    def update_filter_is(self, vfo: str, is_value: int):
        """Update filter IS value (center pitch) for VFO"""
        vfo_key = vfo.upper()
        if vfo_key in self.filter_state:
            old_value = self.filter_state[vfo_key]['is_value']
            self.filter_state[vfo_key]['is_value'] = is_value
            
            # Detect mode change based on values
            self._detect_filter_mode(vfo_key)
            
            # Flag for WebSocket update
            self.filter_state[vfo_key]['needs_update'] = True
            
            debug_print("PANADAPTER", f"📻 VFO {vfo_key} IS: {old_value} → {is_value} (mode: {self.filter_state[vfo_key]['mode']})")
    
    def update_filter_bw(self, vfo: str, bw_value: int):
        """Update filter BW value (bandwidth) for VFO"""
        vfo_key = vfo.upper()
        if vfo_key in self.filter_state:
            old_value = self.filter_state[vfo_key]['bw_value']
            self.filter_state[vfo_key]['bw_value'] = bw_value
            
            # Detect mode change based on values
            self._detect_filter_mode(vfo_key)
            
            # Flag for WebSocket update
            self.filter_state[vfo_key]['needs_update'] = True
            
            debug_print("PANADAPTER", f"📻 VFO {vfo_key} BW: {old_value} → {bw_value} (mode: {self.filter_state[vfo_key]['mode']})")
    
    def update_filter_preset(self, vfo: str, preset_number: int):
        """Update filter preset number for VFO"""
        vfo_key = vfo.upper()
        if vfo_key in self.filter_state:
            old_preset = self.filter_state[vfo_key].get('current', 1)
            self.filter_state[vfo_key]['current'] = preset_number
            
            # Flag for WebSocket update
            self.filter_state[vfo_key]['needs_update'] = True
            
            debug_print("PANADAPTER", f"📻 VFO {vfo_key} Filter Preset: {old_preset} → {preset_number}")
    
    def update_cw_pitch(self, vfo: str, pitch_value: int):
        """Update CW pitch value for VFO"""
        vfo_key = vfo.upper()
        if vfo_key in self.filter_state:
            old_pitch = self.filter_state[vfo_key].get('pitch', 50)
            self.filter_state[vfo_key]['pitch'] = pitch_value
            
            # Flag for WebSocket update
            self.filter_state[vfo_key]['needs_update'] = True
            
            debug_print("PANADAPTER", f"📻 VFO {vfo_key} CW Pitch: {old_pitch} → {pitch_value} ({pitch_value * 10}Hz)")
    
    def get_pending_filter_updates(self) -> Dict:
        """Get filter updates that need to be sent to UI and clear flags"""
        updates = {}
        for vfo in ['A', 'B']:
            if self.filter_state[vfo].get('needs_update', False):
                ui_values = self.get_filter_ui_values(vfo)
                if ui_values:  # Only add if we got valid data
                    updates[vfo] = ui_values
                else:
                    debug_print("CRITICAL", f"❌ get_filter_ui_values returned empty for VFO {vfo}")
                self.filter_state[vfo]['needs_update'] = False
        return updates
    
    def _detect_filter_mode(self, vfo: str):
        """Set filter mode to BW/SHFT only"""
        state = self.filter_state[vfo]
        
        if state['mode'] != 'bwshft':
            debug_print("PANADAPTER", f"📻 VFO {vfo} mode set to: BW/SHFT only")
            state['mode'] = 'bwshft'
    
    def get_panadapter_state(self) -> Dict:
        """Get current panadapter state for UI synchronization"""
        return {
            'center_frequency': self.center_frequency,
            'span': self.span,
            'reference_level': self.reference_level,
            'noise_floor': self.noise_floor,
            'scale_setting': self.scale_setting,
            'vfo_a_frequency': self.vfo_a_frequency,
            'vfo_b_frequency': self.vfo_b_frequency,
            'pan_fps': self.pan_fps,
            'waterfall_lines': len(self.waterfall_data),
            'filter_state': self.filter_state
        }
    
    def get_filter_ui_values(self, vfo: str) -> Dict:
        """Convert K4 IS/BW values to UI values based on detected mode"""
        vfo_key = vfo.upper()
        if vfo_key not in self.filter_state:
            return {}
        
        state = self.filter_state[vfo_key]
        bw_value = state['bw_value']
        is_value = state['is_value']
        mode = state['mode']
        
        if bw_value == 0 or is_value == 0:
            # No data yet, return defaults
            return {
                'current': state.get('current', 1),
                'bw': 3.00, 'shft': 1.50,
                'k4_is': 150, 'k4_bw': 300,
                'pitch': state.get('pitch', 50)
            }
        
        # BW/SHFT interpretation only
        return {
            'current': state.get('current', 1),
            'bw': round((bw_value * 10) / 1000, 2),
            'shft': round((is_value * 10) / 1000, 2),
            'k4_is': is_value,
            'k4_bw': bw_value,
            'pitch': state.get('pitch', 50)
        }


# Global panadapter instance
_panadapter_instance = None

def get_panadapter() -> K4Panadapter:
    """Get or create the global panadapter instance"""
    global _panadapter_instance
    if _panadapter_instance is None:
        _panadapter_instance = K4Panadapter()
    return _panadapter_instance

def handle_panadapter_command(command: str) -> bool:
    """Handle panadapter-related K4 commands and update state."""
    if not command:
        return False
    
    panadapter = get_panadapter()
    
    try:
        if command.startswith('#SPN'):
            # Span command - parse and update span
            span_str = command[4:-1] if command.endswith(';') else command[4:]
            debug_print("CRITICAL", f"📏 SPAN command received: '{command}' → span_str='{span_str}'")
            
            if span_str.isdigit():
                # Span value received - update and check for changes
                span_hz = int(span_str)
                panadapter.update_span_from_cat(span_hz)
                debug_print("CRITICAL", f"📏 SPAN command processed: {command} → {span_hz} Hz ({span_hz/1000:.1f} kHz)")
                return True
            elif span_str == '':
                # Query command - no action needed
                debug_print("CRITICAL", f"📏 SPAN query processed: {command}")
                return True
            else:
                debug_print("CRITICAL", f"❌ SPAN command parse error: '{span_str}' is not a valid number")
                return False
        elif command.startswith('#HREF'):
            # Hardware reference level command - store separately but don't use for display
            ref_str = command[5:-1] if command.endswith(';') else command[5:]
            # Remove $ character if present (K4 protocol variation)
            ref_str = ref_str.replace('$', '')
            ref_level = int(ref_str)
            panadapter.hardware_ref_level = ref_level
            debug_print("PANADAPTER", f"📏 Hardware reference level: {ref_level} dBm (not used for display)")
            return True
        elif command.startswith('#REF'):
            # Panadapter DISPLAY reference level command - this is what users adjust for viewing
            ref_str = command[4:-1] if command.endswith(';') else command[4:]
            # Remove $ character if present (K4 protocol variation)
            ref_str = ref_str.replace('$', '')
            ref_level = int(ref_str)
            panadapter.set_reference_level(ref_level)
            debug_print("PANADAPTER", f"📏 Display reference level set to: {ref_level} dBm (used for waterfall colors)")
            return True
        elif command.startswith('#SCL'):
            # Scale setting
            scale_str = command[4:-1] if command.endswith(';') else command[4:]
            scale = int(scale_str)
            panadapter.set_scale_setting(scale)
            return True
        elif command.startswith('FI'):
            freq_str = command[2:-1] if command.endswith(';') else command[2:]
            frequency = int(freq_str)
            panadapter.center_frequency = frequency
            return True
        elif command.startswith('FA'):
            freq_str = command[2:-1] if command.endswith(';') else command[2:]
            frequency = int(freq_str)
            panadapter.update_vfo_frequency('A', frequency)
            return True
        elif command.startswith('FB'):
            freq_str = command[2:-1] if command.endswith(';') else command[2:]
            frequency = int(freq_str)
            panadapter.update_vfo_frequency('B', frequency)
            return True
        elif command.startswith('IS'):
            # IF Center Pitch command (filter center frequency)
            is_str = command[2:-1] if command.endswith(';') else command[2:]
            if '$' in command:
                # Sub receiver command IS$
                vfo = 'B'
                is_str = is_str.replace('$', '')
            else:
                # Main receiver command IS
                vfo = 'A'
            
            if is_str.isdigit():
                is_value = int(is_str)
                panadapter.update_filter_is(vfo, is_value)
                debug_print("PANADAPTER", f"📻 IS command: VFO {vfo} center pitch = {is_value} (x10Hz)")
                return True
            elif is_str == '':
                # Query command - no action needed here
                return True
        elif command.startswith('BW'):
            # Bandwidth command (filter bandwidth)
            bw_str = command[2:-1] if command.endswith(';') else command[2:]
            if '$' in command:
                # Sub receiver command BW$
                vfo = 'B'
                bw_str = bw_str.replace('$', '')
            else:
                # Main receiver command BW
                vfo = 'A'
            
            if bw_str.isdigit():
                bw_value = int(bw_str)
                panadapter.update_filter_bw(vfo, bw_value)
                debug_print("PANADAPTER", f"📻 BW command: VFO {vfo} bandwidth = {bw_value} (x10Hz)")
                return True
            elif bw_str == '':
                # Query command - no action needed here
                return True
        elif command.startswith('FP'):
            # Filter preset command (filter number selection)
            fp_str = command[2:-1] if command.endswith(';') else command[2:]
            if '$' in command:
                # Sub receiver command FP$
                vfo = 'B'
                fp_str = fp_str.replace('$', '')
            else:
                # Main receiver command FP
                vfo = 'A'
            
            if fp_str.isdigit():
                preset_number = int(fp_str)
                panadapter.update_filter_preset(vfo, preset_number)
                debug_print("PANADAPTER", f"📻 FP command: VFO {vfo} filter preset = {preset_number}")
                return True
            elif fp_str == '':
                # Query command - no action needed here
                return True
        elif command.startswith('CW'):
            # CW Pitch command (CW Pitch) SET/RESP format: CWnn; where nn is sidetone pitch x10 Hz (25-95)
            cw_str = command[2:-1] if command.endswith(';') else command[2:]
            if '$' in command:
                # Sub receiver command CW$
                vfo = 'B'
                cw_str = cw_str.replace('$', '')
            else:
                # Main receiver command CW
                vfo = 'A'
            
            if cw_str.isdigit():
                pitch_value = int(cw_str)
                # Validate pitch range (25-95 according to K4 protocol)
                if 25 <= pitch_value <= 95:
                    panadapter.update_cw_pitch(vfo, pitch_value)
                    debug_print("PANADAPTER", f"📻 CW command: VFO {vfo} pitch = {pitch_value} ({pitch_value * 10}Hz)")
                    return True
                else:
                    debug_print("CRITICAL", f"❌ CW pitch value out of range: {pitch_value} (valid: 25-95)")
                    return False
            elif cw_str == '':
                # Query command - no action needed here
                return True
    except (ValueError, IndexError) as e:
        debug_print("CRITICAL", f"❌ Error parsing panadapter command '{command}': {e}")
    
    return False

# Module initialization
debug_print("GENERAL", "🖥️ K4 Panadapter module loaded with accurate decompression")
debug_print("GENERAL", "📊 Features:")
debug_print("GENERAL", "   - Accurate decompression formula for realistic dB values")
debug_print("GENERAL", "   - Variable reference level (configurable)")
debug_print("GENERAL", "   - Better signal level mapping")
debug_print("GENERAL", "   - MINI-PAN processing disabled for broad spectrum")
debug_print("GENERAL", "   - Reference level commands actually work now")