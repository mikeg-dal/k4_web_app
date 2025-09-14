/**
 * K4 Web Control - Main Application Logic
 * 
 * Handles WebSocket communication, audio processing, and UI controls
 * Removed Math.tanh() distortion from fallback processing
 */

// Global variables
let ws = null;
let audioCtx = null;
let audioQueue = [];
let nextStartTime = 0;
let volumeGain = null;
let audioProcessingEnabled = true;
let targetBufferSize = 3;
let lastAudioTime = 0;

// PTT and microphone variables
let microphoneStream = null;
let microphonePermissionGranted = false;
let isTransmitting = false;
let microphoneSource = null;
let pttNode = null;
// STEP 1: Replace hardcoded mic gain with configuration system
let micGain = 0.1; // Default fallback - will be overridden by config

// Configuration system integration - ACTIVE
let configLoadedSuccessfully = false;
let backendConfigAvailable = false;

// Listen for configuration loaded event and apply settings
window.addEventListener('k4ConfigLoaded', (event) => {
    const { error, fallback } = event.detail;
    configLoadedSuccessfully = !error;
    backendConfigAvailable = !fallback;
    
    console.log(`🔧 App.js: Configuration system ${configLoadedSuccessfully ? 'loaded' : 'failed'}`);
    console.log(`📡 App.js: Backend config ${backendConfigAvailable ? 'available' : 'unavailable (using fallback)'}`);
    
    if (configLoadedSuccessfully) {
        // STEP 1: Apply mic gain from configuration
        const previousMicGain = micGain;
        micGain = getConfigValue('audio.mic_gain', 0.1);
        
        console.log(`🎤 App.js: Mic gain updated: ${previousMicGain} → ${micGain}`);
        
        // Update PTT processor if it's already initialized
        if (pttNode && pttNode.port) {
            pttNode.port.postMessage({
                type: 'setMicGain',
                value: micGain
            });
            console.log(`🎤 App.js: PTT processor mic gain updated to ${micGain}`);
        }
        
        // Update mic gain slider to reflect configuration value
        const micSlider = document.getElementById('micGainSlider');
        if (micSlider) {
            const sliderValue = Math.round(micGain * 100);
            micSlider.value = sliderValue;
            
            const micValue = document.getElementById('micGainValue');
            if (micValue) {
                micValue.textContent = sliderValue;
            }
            
            console.log(`🎤 App.js: Mic gain slider updated to ${sliderValue}%`);
        }
        
        // STEP 2: Apply volume defaults from configuration
        const volumeDefaults = K4VolumeUtils.getDefaults();
        console.log(`🔊 App.js: Applying volume defaults from configuration:`);
        console.log(`   - Main: ${volumeDefaults.main}%`);
        console.log(`   - Sub: ${volumeDefaults.sub}%`);
        console.log(`   - Master: ${volumeDefaults.master}%`);
        
        // Update volume sliders to reflect configuration defaults
        const mainVolumeSlider = document.getElementById('mainVolumeSlider');
        const subVolumeSlider = document.getElementById('subVolumeSlider');
        const masterVolumeSlider = document.getElementById('volumeSlider');
        const sidebarVolumeSlider = document.getElementById('sidebarVolumeSlider');
        
        if (mainVolumeSlider) {
            mainVolumeSlider.value = volumeDefaults.main;
            const mainValue = document.getElementById('mainVolumeValue');
            if (mainValue) mainValue.textContent = volumeDefaults.main + '%';
        }
        
        if (subVolumeSlider) {
            subVolumeSlider.value = volumeDefaults.sub;
            const subValue = document.getElementById('subVolumeValue');
            if (subValue) subValue.textContent = volumeDefaults.sub + '%';
        }
        
        if (masterVolumeSlider) {
            masterVolumeSlider.value = volumeDefaults.master;
            const masterValue = document.getElementById('volumeValue');
            if (masterValue) masterValue.textContent = volumeDefaults.master + '%';
        }
        
        if (sidebarVolumeSlider) {
            sidebarVolumeSlider.value = volumeDefaults.master;
            const sidebarValue = document.getElementById('sidebarVolumeValue');
            if (sidebarValue) sidebarValue.textContent = volumeDefaults.master + '%';
        }
        
        // Update VFO volume sliders to configuration defaults
        const vfoAVolumeSlider = document.getElementById('vfoAVolumeSlider');
        const vfoBVolumeSlider = document.getElementById('vfoBVolumeSlider');
        
        if (vfoAVolumeSlider) {
            vfoAVolumeSlider.value = volumeDefaults.main;
            const vfoAValue = document.getElementById('vfoAVolumeValue');
            if (vfoAValue) vfoAValue.textContent = volumeDefaults.main;
        }
        
        if (vfoBVolumeSlider) {
            vfoBVolumeSlider.value = volumeDefaults.sub;
            const vfoBValue = document.getElementById('vfoBVolumeValue');
            if (vfoBValue) vfoBValue.textContent = volumeDefaults.sub;
        }
        
        // DEMO: Show volume calculation comparison
        const testUserVolume = 50;
        const configCalculated = K4VolumeUtils.calculateMainVolume(testUserVolume);
        const hardcodedCalculated = (testUserVolume / 100) * 2.0; // Existing hardcoded formula
        
        console.log(`📊 App.js: Volume calculation demo (50% input):`);
        console.log(`   - Config system: ${configCalculated.toFixed(3)}`);
        console.log(`   - Hardcoded: ${hardcodedCalculated.toFixed(3)}`);
        
        console.log(`✅ App.js: Step 2 complete - Volume system now uses configuration`);
        
        // STEP 3: Demonstrate network configuration loading
        const k4Host = K4NetworkUtils.getK4Host();
        const k4Port = K4NetworkUtils.getK4Port();
        const webPort = K4NetworkUtils.getWebPort();
        
        console.log(`🌐 App.js: Network configuration loaded:`);
        console.log(`   - K4 Radio: ${k4Host}:${k4Port}`);
        console.log(`   - Web Server: ${window.location.hostname}:${webPort}`);
        console.log(`   - WebSocket: ${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`);
        
        console.log(`✅ App.js: Step 3 complete - Network settings available from configuration`);
        
        // STEP 4: Demonstrate panadapter configuration loading
        if (typeof K4PanadapterUtils !== 'undefined') {
            const centerFreq = K4PanadapterUtils.getCenterFreq();
            const span = K4PanadapterUtils.getSpan();
            const refLevel = K4PanadapterUtils.getRefLevel();
            const scale = K4PanadapterUtils.getScale();
            const waterfallHeight = K4PanadapterUtils.getWaterfallHeight();
            
            console.log(`📊 App.js: Panadapter configuration loaded:`);
            console.log(`   - Center Freq: ${(centerFreq / 1000000).toFixed(3)} MHz`);
            console.log(`   - Span: ${(span / 1000).toFixed(0)} kHz`);
            console.log(`   - Reference Level: ${refLevel} dBm`);
            console.log(`   - Scale: ${scale} dB`);
            console.log(`   - Waterfall Height: ${waterfallHeight}px`);
            
            console.log(`✅ App.js: Step 4 complete - Panadapter defaults available from configuration`);
        } else {
            console.log(`⚠️ App.js: K4PanadapterUtils not available yet - will be ready when panadapter loads`);
        }
        
        // STEP 5: Demonstrate mode mapping configuration loading
        if (typeof K4ModeUtils !== 'undefined') {
            const modeMap = K4ModeUtils.getCATModeMap();
            const supportedModes = K4ModeUtils.getSupportedModes();
            const usbDisplayName = K4ModeUtils.getModeDisplayName('2');
            const reverseMap = K4ModeUtils.getReverseModeMap();
            
            console.log(`📻 App.js: Mode mapping configuration loaded:`);
            console.log(`   - Total modes: ${Object.keys(modeMap).length}`);
            console.log(`   - Supported modes: ${supportedModes.join(', ')}`);
            console.log(`   - Mode code '2' displays as: ${usbDisplayName}`);
            console.log(`   - Reverse mapping test - 'USB' = code ${reverseMap['USB']}`);
            
            console.log(`✅ App.js: Step 5 complete - Mode mappings available from configuration`);
        } else {
            console.log(`⚠️ App.js: K4ModeUtils not available yet - will be ready after config loads`);
        }
    }
});

// DOM element cache for performance
const domCache = {
  connectBtn: null,
  disconnectBtn: null,
  micPermissionPanel: null,
  currentMode: null,
  audioContext: null,
  audioLatency: null,
  audioStatus: null,
  mainVolumeSlider: null,
  subVolumeSlider: null,
  masterVolumeSlider: null,
  
  // Initialize cache - call after DOM is loaded
  init() {
    this.connectBtn = document.getElementById("connectBtn");
    this.disconnectBtn = document.getElementById("disconnectBtn");
    this.micPermissionPanel = document.getElementById("micPermissionPanel");
    this.currentMode = document.getElementById('currentMode');
    this.audioContext = document.getElementById("audioContext");
    this.audioLatency = document.getElementById("audioLatency");
    this.audioStatus = document.getElementById("audioStatus");
    this.mainVolumeSlider = document.getElementById('mainVolumeSlider');
    this.subVolumeSlider = document.getElementById('subVolumeSlider');
    this.masterVolumeSlider = document.getElementById('masterVolumeSlider');
  }
};

// Initialize mic gain properly on page load
window.addEventListener('DOMContentLoaded', () => {
  // Initialize DOM cache for performance
  domCache.init();
  
  // Make sure the mic gain value matches the slider on startup
  const micSlider = document.getElementById('micGainSlider');
  if (micSlider) {
    micGain = parseInt(micSlider.value) / 100.0;
  }
});

// Dual receiver variables
let subReceiverEnabled = false;
let currentAudioRouting = 'a.b';

/**
 * WebSocket Connection Management
 */
function connect() {
  console.log("🔌 Attempting to connect...");
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(protocol + "//" + location.host + "/ws");
  window.ws = ws; // Make WebSocket globally accessible
  ws.binaryType = "arraybuffer";

  ws.onopen = async () => {
    console.log("✅ WebSocket connected");
    
    if (domCache.connectBtn) domCache.connectBtn.style.display = "none";
    if (domCache.disconnectBtn) domCache.disconnectBtn.style.display = "block";
    
    // Notify radio manager of successful connection
    if (window.radioManager && window.radioManager.getActiveRadio()) {
      const activeRadioId = window.radioManager.getActiveRadioId();
      // Update the radio's last connected timestamp in backend
      await updateRadioLastConnected(activeRadioId);
      // Update the radio manager UI
      updateRadioManagerConnectionStatus('connected');
    }
    
    if (!microphonePermissionGranted) {
      document.getElementById("micPermissionPanel").style.display = "block";
    }

    if (typeof initializePanadapter === 'function') {
      initializePanadapter();
    }

    setTimeout(() => {
      document.getElementById('currentMode').innerHTML = 
        '<span style="color: var(--accent-green);">EM3 (Opus 32-bit) - OPTIMAL</span>';
      
      // STARTUP FIX: Query K4's current settings instead of forcing our own
      send('#SPN;');         // Query current span (don't force 50kHz)
      send('#REF;');         // Query current panadapter display reference level (user's cosmetic preference)
      send('#FI;');          // Query current center frequency
      
      // Query current filter settings for both VFOs
      send('FP;');           // Query VFO A filter preset number
      send('FP$;');          // Query VFO B filter preset number
      send('BW;');           // Query VFO A bandwidth
      send('BW$;');          // Query VFO B bandwidth  
      send('IS;');           // Query VFO A center pitch
      send('IS$;');          // Query VFO B center pitch
    }, 1000);
    
    try {
      // CRITICAL FIX: AudioContext sample rate must match microphone input
      // Use configured input sample rate to prevent AudioWorklet issues
      const inputSampleRate = getConfigValue('audio.input_sample_rate', 48000);
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: inputSampleRate,
        latencyHint: "interactive"
      });
      
      volumeGain = audioCtx.createGain();
      // STEP 2: Use configuration-based initial master volume
      const initialMasterVolume = configLoadedSuccessfully ? 
          K4VolumeUtils.calculateMasterVolume(K4VolumeUtils.getDefaults().master) : 
          1.5; // Fallback to hardcoded
      volumeGain.gain.value = initialMasterVolume;
      volumeGain.connect(audioCtx.destination);
      
      console.log(`🔊 Audio context initialized with master volume: ${initialMasterVolume.toFixed(2)}`);
      
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }
      
      document.getElementById("audioContext").textContent = 
        `Audio Context: ${audioCtx.state} @ ${audioCtx.sampleRate}Hz`;
      
      processAudioQueue();

      
    } catch (error) {
      console.error("Audio context error:", error);
    }
  };

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      const currentTime = performance.now();
      const float32 = new Float32Array(event.data);
      
      if (float32.length > 0) {
        audioQueue.push(float32);
        
        const latency = currentTime - lastAudioTime;
        if (domCache.audioLatency) domCache.audioLatency.textContent = `Latency: ${latency.toFixed(0)}ms`;
        lastAudioTime = currentTime;
        
        while (audioQueue.length > targetBufferSize * 2) {
          audioQueue.shift();
        }
        
        if (domCache.audioStatus) domCache.audioStatus.textContent = "Audio Queue: " + audioQueue.length;
      }
    } else {
      const msg = JSON.parse(event.data);
      if (msg.type === "cat") {
        updateCAT(msg.text, msg.updates);
      } else if (msg.type === "spectrum_data") {
        if (typeof handleSpectrumData === 'function') {
          handleSpectrumData(msg);
        }
      } else if (msg.type === "boundary_update") {
        // DYNAMIC BOUNDARY UPDATE: Immediately update frequency boundaries
        if (typeof handleBoundaryUpdate === 'function') {
          handleBoundaryUpdate(msg);
        }
      } else if (msg.type === "audio_mode_changed") {
        document.getElementById('currentMode').innerHTML = 
          '<span style="color: var(--accent-green);">' + msg.name + '</span>';
        console.log('✅ Audio mode confirmed:', msg.name);
      } else if (msg.type === "audio_settings") {
        const settings = msg.settings;
        // STEP 2: Convert from backend internal scale to frontend 0-100% scale using configuration
        const internalMax = configLoadedSuccessfully ? 
            getConfigValue('audio.volume.internal_max', 200) : 200;
        const internalScale = internalMax / 100; // Convert internal max to scale factor (e.g., 200/100 = 2.0)
        
        // Only update main volume if user is not actively adjusting it
        if (!isUserAdjustingMainVolume) {
          const mainVolumePercent = Math.round((settings.main_volume / internalScale) * 100);
          document.getElementById('mainVolumeSlider').value = mainVolumePercent;
          document.getElementById('mainVolumeValue').textContent = mainVolumePercent + '%';
        }
        
        // Only update sub volume if user is not actively adjusting it
        if (!isUserAdjustingSubVolume) {
          const subVolumePercent = Math.round((settings.sub_volume / internalScale) * 100);
          document.getElementById('subVolumeSlider').value = subVolumePercent;
          document.getElementById('subVolumeValue').textContent = subVolumePercent + '%';
        }
        document.getElementById('audioRoutingSelect').value = settings.audio_routing;
        
        subReceiverEnabled = settings.sub_enabled;
        currentAudioRouting = settings.audio_routing;
        updateRoutingDisplay();
      } else if (msg.type === "filter_update") {
        // Update VFO filter state from K4 responses
        if (typeof vfoControlNew !== 'undefined' && vfoControlNew && msg.vfo && msg.filter_data) {
          vfoControlNew.updateFromK4Filter(msg.vfo, msg.filter_data);
        }
      }
    }
  };

  ws.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
  };

  ws.onclose = () => {
    console.warn("⚠️ WebSocket closed");
    ws = null;
    window.ws = null; // Clear global reference
    isTransmitting = false;
    if (domCache.connectBtn) domCache.connectBtn.style.display = "block";
    if (domCache.disconnectBtn) domCache.disconnectBtn.style.display = "none";
    
    // Notify radio manager of disconnection
    updateRadioManagerConnectionStatus('disconnected');
    document.getElementById("pttButton").classList.remove("transmitting");
    document.getElementById("pttStatus").textContent = "Disconnected";
    document.getElementById("micStats").textContent = "Mic: Not active";
    document.getElementById("dualRxStatus").textContent = "Dual RX: Disconnected";
    document.getElementById("currentMode").textContent = "Disconnected";
    if (audioCtx) {
      audioCtx.close();
      audioCtx = null;
    }
  };
}

function disconnect() {
  if (isTransmitting) {
    stopPTT();
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("DISCONNECT");
        ws.close();
        console.log("🔌 Disconnected by user");
      }
    }, 100);
  } else {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send("DISCONNECT");
      ws.close();
      console.log("🔌 Disconnected by user");
    }
  }
}

function send(cmd) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    // Validate command is not empty before sending
    if (!cmd || (typeof cmd === 'string' && cmd.trim() === '')) {
      console.error("❌ Attempted to send empty WebSocket message:", JSON.stringify(cmd));
      return;
    }
    ws.send(cmd);
  }
}

/**
 * Audio Processing
 */
function processAudioQueue() {
  if (!audioCtx || audioCtx.state !== "running") {
    if (audioCtx) {
      requestAnimationFrame(processAudioQueue);
    }
    return;
  }

  if (audioQueue.length >= targetBufferSize) {
    const float32 = audioQueue.shift();
    
    try {
      const frames = float32.length / 2;
      // RX audio uses configured output sample rate
      const outputSampleRate = getConfigValue('audio.output_sample_rate', 12000);
      const buffer = audioCtx.createBuffer(2, frames, outputSampleRate);
      const left = buffer.getChannelData(0);
      const right = buffer.getChannelData(1);

      for (let i = 0; i < frames; i++) {
        let leftSample = float32[i * 2];
        let rightSample = float32[i * 2 + 1];
        
        
        
        left[i] = leftSample;
        right[i] = rightSample;
      }

      const source = audioCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(volumeGain);

      const startTime = Math.max(audioCtx.currentTime, nextStartTime);
      source.start(startTime);
      
      nextStartTime = startTime + buffer.duration;
      
    } catch (error) {
      console.error("Audio playback error:", error);
    }
  }
  
  requestAnimationFrame(processAudioQueue);
}

/**
 * CAT Command Processing
 */
function updateCAT(text, updates = {}) {
  // console.log(`📡 CAT Update: ${text}`);
  
  // Handle #AVG response
  if (text.startsWith('#AVG') && text.length > 4) {
    const avgValueStr = text.slice(4, -1); // Remove #AVG and ;
    const avgValue = parseInt(avgValueStr);
    if (!isNaN(avgValue) && avgValue >= 1 && avgValue <= 20) {
      if (typeof handleAveragingResponse === 'function') {
        handleAveragingResponse(avgValue);
      }
    }
  }
  
  // Handle parsed updates from backend
  if (updates.pan_span) {
    
    // Update the span dropdown to match K4's setting
    const spanSelect = document.getElementById('spanSelect');
    if (spanSelect) {
      const spanKHz = updates.pan_span / 1000;
      spanSelect.value = spanKHz;
      console.log(`🎯 UI Updated: Span dropdown set to ${spanKHz} kHz`);
    }
    
    // Update panadapter state if available
    if (window.panadapterState) {
      window.panadapterState.span = updates.pan_span;
    }
    
    // Force UI refresh
    if (typeof renderPanadapter === 'function') {
      renderPanadapter();
    }
  }
  
  const cmds = text.split(';');
  for (let cmd of cmds) {
    if (cmd.startsWith("FA")) {
      const freq = parseInt(cmd.slice(2));
      
      // Update UI element for VFO A frequency
      const faElement = document.getElementById('fa');
      if (faElement) {
        faElement.textContent = formatFrequency(freq);
        faElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { faElement.style.color = ''; }, 1000);
      }
      
      // PANADAPTER INTEGRATION: Update VFO A frequency 
      
      if (window.panadapterState) {
        window.panadapterState.vfoA = freq;
      }
    } else if (cmd.startsWith("FB")) {
      const freq = parseInt(cmd.slice(2));
      
      // Update UI element for VFO B frequency
      const fbElement = document.getElementById('fb');
      if (fbElement) {
        fbElement.textContent = formatFrequency(freq);
        fbElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { fbElement.style.color = ''; }, 1000);
      }
      
      // PANADAPTER INTEGRATION: Update VFO B frequency
      if (typeof updateVfoBFrequency === 'function') {
        updateVfoBFrequency(freq);
      }
      
      if (window.panadapterState) {
        window.panadapterState.vfoB = freq;
      }
    } else if (cmd.startsWith("MD$")) {
      // VFO B mode (sub receiver)
      const modeCode = cmd.slice(3);
      const modeName = K4ModeUtils.getModeDisplayName(modeCode);
      
      // Update UI element for VFO B mode only
      const modeBElement = document.getElementById('modeb');
      if (modeBElement) {
        modeBElement.textContent = modeName;
        modeBElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { modeBElement.style.color = ''; }, 1000);
      }
    } else if (cmd.startsWith("MD")) {
      // VFO A mode (main receiver)
      const modeCode = cmd.slice(2);
      const modeName = K4ModeUtils.getModeDisplayName(modeCode);
      
      // Update UI element for VFO A mode only
      const modeAElement = document.getElementById('modea');
      if (modeAElement) {
        modeAElement.textContent = modeName;
        modeAElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { modeAElement.style.color = ''; }, 1000);
      }
    } else if (cmd.startsWith("AG$")) {
      // Sub AF gain
      const gain = parseInt(cmd.slice(3));
      
      // Update UI element for Sub AF gain (VFO B)
      const agSubElement = document.getElementById('afb');
      if (agSubElement) {
        agSubElement.textContent = gain;
        agSubElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { agSubElement.style.color = ''; }, 1000);
      }
    } else if (cmd.startsWith("AG")) {
      // Main AF gain (VFO A)
      const gain = parseInt(cmd.slice(2));
      
      // Update UI element for Main AF gain (VFO A)
      const agMainElement = document.getElementById('afa');
      if (agMainElement) {
        agMainElement.textContent = gain;
        agMainElement.style.color = '#4CAF50'; // Green to indicate update
        setTimeout(() => { agMainElement.style.color = ''; }, 1000);
      }
    } else if (cmd.startsWith("SB")) {
      // Sub receiver state (SB0 = off, SB1 = on)
      const state = cmd.slice(2);
      if (state === '0' || state === '1') {
        const enabled = (state === '1');
        
        // Update SubRX state and UI
        subReceiverEnabled = enabled;
        const button = document.getElementById('subRxToggle');
        if (button) {
          button.textContent = enabled ? 'Sub RX: ON' : 'Sub RX: OFF';
          button.style.backgroundColor = enabled ? '#4CAF50' : '#f44336';
          button.style.color = '#ffffff';
        }
        
        // Update audio routing display
        updateRoutingDisplay();
      }
    }
  }
}

// Helper function to format frequency display
function formatFrequency(freq) {
  if (!freq) return '--';
  
  const freqStr = freq.toString().padStart(8, '0');
  const mhz = freqStr.slice(0, -6) || '0';
  const khz = freqStr.slice(-6, -3);
  const hz = freqStr.slice(-3);
  
  return `${parseInt(mhz)}.${khz}.${hz}`;
}

/**
 * Audio Control Functions with Debouncing
 */

// Debounce timers for smoother slider performance
let mainVolumeTimer = null;
let subVolumeTimer = null;
let masterVolumeTimer = null;
let bufferSizeTimer = null;
let micGainTimer = null;

// Flags to prevent feedback during user interaction
let isUserAdjustingMainVolume = false;
let isUserAdjustingSubVolume = false;

function updateMainVolume(value) {
  // Mark that user is actively adjusting this control
  isUserAdjustingMainVolume = true;
  
  // Update UI immediately for responsive feel
  document.getElementById("mainVolumeValue").textContent = value + "%";
  
  // Sync with VFO A volume slider
  syncVFOVolumeFromMain('A', value);
  
  // Debounce WebSocket messages to prevent flooding
  if (mainVolumeTimer) clearTimeout(mainVolumeTimer);
  mainVolumeTimer = setTimeout(() => {
    // STEP 2: Use configuration-based volume scaling for Main Volume
    const volume = configLoadedSuccessfully ? 
        K4VolumeUtils.calculateMainVolume(value) : 
        (value / 100) * 2.0; // Fallback to hardcoded
    sendAudioControl('set_main_volume', volume);
    
    // Clear user adjustment flag after a brief delay
    setTimeout(() => { isUserAdjustingMainVolume = false; }, 100);
  }, 50); // 50ms debounce
}

function updateSubVolume(value) {
  // Mark that user is actively adjusting this control
  isUserAdjustingSubVolume = true;
  
  // Update UI immediately for responsive feel
  document.getElementById("subVolumeValue").textContent = value + "%";
  
  // Sync with VFO B volume slider
  syncVFOVolumeFromMain('B', value);
  
  // Debounce WebSocket messages to prevent flooding
  if (subVolumeTimer) clearTimeout(subVolumeTimer);
  subVolumeTimer = setTimeout(() => {
    // STEP 2: Use configuration-based volume scaling for Sub Volume
    const volume = configLoadedSuccessfully ? 
        K4VolumeUtils.calculateSubVolume(value) : 
        (value / 100) * 2.0; // Fallback to hardcoded
    sendAudioControl('set_sub_volume', volume);
    
    // Clear user adjustment flag after a brief delay
    setTimeout(() => { isUserAdjustingSubVolume = false; }, 100);
  }, 50); // 50ms debounce
}

function updateAudioRouting(routing) {
  currentAudioRouting = routing;
  sendAudioControl('set_audio_routing', routing);
  updateRoutingDisplay();
}

function updateRoutingDisplay() {
  const routingDisplay = document.getElementById('routingStatusDisplay');
  const routingDescriptions = {
    'a.b': 'Main → Left, Sub → Right',
    'ab.ab': 'Mix → Both Channels',
    'a.-a': 'Main → Left, Main Inverted → Right',
    'a.ab': 'Main → Left, Mix → Right',
    'ab.b': 'Mix → Left, Sub → Right',
    'ab.a': 'Mix → Left, Main → Right',
    'b.ab': 'Sub → Left, Mix → Right',
    'b.b': 'Sub → Both Channels',
    'b.a': 'Sub → Left, Main → Right',
    'a.a': 'Main → Both Channels'
  };
  
  if (subReceiverEnabled) {
    routingDisplay.textContent = routingDescriptions[currentAudioRouting] || 'Unknown';
  } else {
    routingDisplay.textContent = 'Main → Both Channels (Sub Off)';
  }
}

function toggleSubReceiver() {
    subReceiverEnabled = !subReceiverEnabled;
    const button = document.getElementById('subRxToggle');
    
    if (subReceiverEnabled) {
        button.classList.remove('off');
        button.classList.add('on');
        button.textContent = 'ON';
    } else {
        button.classList.remove('on');
        button.classList.add('off');
        button.textContent = 'OFF';
    }
    
    // Send the state to the backend
    sendAudioControl('set_sub_enabled', subReceiverEnabled);
    
    // Update display
    document.getElementById('audioStatusDisplay').textContent = 
        subReceiverEnabled ? 'Dual Receiver' : 'Main Only';
    document.getElementById('dualRxStatus').textContent = 
        'Dual RX: ' + (subReceiverEnabled ? 'Active' : 'Main Only');
    
    // Sync with VFO Sub RX button
    syncVFOSubRXFromMain(subReceiverEnabled);
    
    updateRoutingDisplay();
}

function sendAudioControl(action, value) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'audio_control',
      action: action,
      value: value
    }));
  }
}

function updateVolume(value) {
  // Update UI immediately for responsive feel
  document.getElementById("volumeValue").textContent = value + "%";
  
  // Debounce audio processing to prevent performance issues
  if (masterVolumeTimer) clearTimeout(masterVolumeTimer);
  masterVolumeTimer = setTimeout(() => {
    // STEP 2: Use configuration-based volume scaling for Master Volume
    const volume = configLoadedSuccessfully ? 
        K4VolumeUtils.calculateMasterVolume(value) : 
        (value / 100) * 3.0; // Fallback to hardcoded
    if (volumeGain) {
      volumeGain.gain.value = volume;
    }
  }, 20); // 20ms debounce for audio processing (faster for local audio)
}

function updateBufferSize(value) {
  // Update UI immediately for responsive feel
  document.getElementById("bufferValue").textContent = value;
  
  // Debounce the actual buffer size update
  if (bufferSizeTimer) clearTimeout(bufferSizeTimer);
  bufferSizeTimer = setTimeout(() => {
    targetBufferSize = parseInt(value);
  }, 100); // 100ms debounce for buffer size
}

function updateMicGain(value) {
  // Update UI immediately for responsive feel
  document.getElementById("micGainValue").textContent = value + "%";
  
  // Debounce mic gain updates to prevent AudioWorklet message flooding
  if (micGainTimer) clearTimeout(micGainTimer);
  micGainTimer = setTimeout(() => {
    micGain = value / 100.0;
    
    if (pttNode && pttNode.port) {
      pttNode.port.postMessage({
        type: 'setMicGain',
        value: micGain
      });
    }
  }, 50); // 50ms debounce for mic gain
}

// VFO Volume Control Integration
function updateVFOVolume(vfo, volume) {
  // Handle VFO volume controls properly when Sub RX is enabled
  
  if (!subReceiverEnabled) {
    // When Sub RX is disabled, VFO A controls main volume, VFO B is ignored
    if (vfo === 'A') {
      const mainSlider = document.getElementById('mainVolumeSlider');
      if (mainSlider) {
        mainSlider.value = volume;
        updateMainVolume(volume);
      }
    }
    // VFO B volume is ignored when Sub RX is disabled
    return;
  }
  
  // When Sub RX is enabled, both VFOs should control their respective channels
  if (vfo === 'A') {
    // VFO A controls main receiver volume
    const mainSlider = document.getElementById('mainVolumeSlider');
    if (mainSlider) {
      mainSlider.value = volume;
      updateMainVolume(volume);
    }
  } else if (vfo === 'B') {
    // VFO B controls sub receiver volume
    const subSlider = document.getElementById('subVolumeSlider');
    if (subSlider) {
      subSlider.value = volume;
      updateSubVolume(volume);
    }
  }
  
  // Log for debugging
  console.log(`🔊 VFO ${vfo} volume set to ${volume}% (Sub RX: ${subReceiverEnabled ? 'ON' : 'OFF'}, Routing: ${currentAudioRouting})`);
}

// Synchronize VFO volume sliders with main audio controls
function syncVFOVolumeFromMain(vfo, volume) {
  // Prevent circular updates during VFO slider changes
  if ((vfo === 'A' && isUserAdjustingMainVolume) || 
      (vfo === 'B' && isUserAdjustingSubVolume)) {
    return;
  }
  
  // Update VFO volume slider when main audio controls change
  if (window.vfoIntegrationNew && window.vfoIntegrationNew.vfoControl) {
    window.vfoIntegrationNew.vfoControl.vfoState[vfo].volume = volume;
    window.vfoIntegrationNew.vfoControl.updateVolumeDisplay(vfo);
  }
}

// VFO Sub RX Integration - called from VFO control when Sub button is pressed
function updateVFOSubRX() {
  // Toggle the existing sub receiver functionality
  toggleSubReceiver();
}

// Synchronize VFO Sub RX button with main Sub Receiver state
function syncVFOSubRXFromMain(enabled) {
  // Update VFO Sub RX button when main sub receiver state changes
  if (window.vfoIntegrationNew && window.vfoIntegrationNew.vfoControl) {
    window.vfoIntegrationNew.vfoControl.updateSubRX(enabled);
  }
}

// Test function to verify VFO audio integration
function testVFOAudioIntegration() {
  console.log('🧪 Testing VFO Audio Integration...');
  
  // Test volume sync
  if (typeof updateVFOVolume === 'function') {
    console.log('✅ updateVFOVolume function available');
  } else {
    console.log('❌ updateVFOVolume function not found');
  }
  
  // Test sub RX sync
  if (typeof updateVFOSubRX === 'function') {
    console.log('✅ updateVFOSubRX function available');
  } else {
    console.log('❌ updateVFOSubRX function not found');
  }
  
  // Check VFO integration
  if (window.vfoIntegrationNew) {
    console.log('✅ VFO Integration New instance available');
  } else {
    console.log('❌ VFO Integration New instance not found');
  }
  
  console.log('🏁 VFO Audio Integration test complete');
}

function toggleAudioProcessing() {
  audioProcessingEnabled = !audioProcessingEnabled;
  document.getElementById("processingStatus").textContent = 
    "Processing: " + (audioProcessingEnabled ? "ON" : "OFF");
}

/**
 * Microphone and PTT Functions
 */
async function requestMicrophonePermission() {
  const statusElement = document.getElementById("micPermissionStatus");
  const button = event.target;
  
  try {
    statusElement.textContent = "Requesting microphone access...";
    button.disabled = true;
    
    const inputSampleRate = getConfigValue('audio.input_sample_rate', 48000);
    microphoneStream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        sampleRate: inputSampleRate,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: false
      }
    });
    
    microphonePermissionGranted = true;
    
    document.getElementById("micPermissionPanel").style.display = "none";
    document.getElementById("pttButton").disabled = false;
    document.getElementById("pttStatus").textContent = "Ready - Hold to transmit";
    
    console.log("✅ Microphone permission granted");
    
    if (audioCtx) {
      setupMicrophoneProcessing();
    }
    
  } catch (error) {
    console.error("❌ Microphone permission denied:", error);
    statusElement.textContent = `Permission denied: ${error.message}`;
    document.getElementById("pttStatus").textContent = "Permission denied";
    button.disabled = false;
  }
}

async function setupMicrophoneProcessing() {
  if (!microphoneStream || !audioCtx) return;
  
  try {
    console.log("🎤 Setting up AudioWorklet microphone processing");
    await audioCtx.audioWorklet.addModule('/static/ptt-processor.js');

    microphoneSource = audioCtx.createMediaStreamSource(microphoneStream);
    pttNode = new AudioWorkletNode(audioCtx, 'ptt-processor');

    // ✅ Send configuration-based mic gain to PTT processor
    if (pttNode && pttNode.port) {
        pttNode.port.postMessage({
            type: 'setMicGain',
            value: micGain  // Use configuration-loaded mic gain
        });
        console.log(`🎤 PTT processor initialized with mic gain: ${micGain}`);
    }

    // ✅ Send backend-configured WORKLET_FRAME_SIZE after node creation
    try {
      const response = await fetch("/config/audio");
      const config = await response.json();
      if (pttNode && pttNode.port) {
        pttNode.port.postMessage({
          type: 'setConfig',
          config: config
        });
      }
    } catch (err) {
      console.warn("⚠️ Failed to send WORKLET_FRAME_SIZE to AudioWorklet:", err);
    }

    pttNode.port.onmessage = function(event) {
      const { type, data, sampleCount, timestamp } = event.data;
      
      if (type === 'audioData' && isTransmitting && ws && ws.readyState === WebSocket.OPEN) {
        try {
          // Validate audio data is not empty before sending
          if (!data || data.byteLength === 0) {
            console.error("❌ AudioWorklet produced empty audio data, skipping send");
            return;
          }
          // Send binary audio data directly - server expects message["bytes"]
          ws.send(data);
          
          // Update UI with transmission stats
          const micStatsElement = document.getElementById("micStats");
          micStatsElement.innerHTML = 
            `<span style="color: var(--accent-green)">TX: ${data.byteLength}B @${sampleCount}smp</span>`;
            
        } catch (error) {
          console.error("❌ Failed to send AudioWorklet audio:", error);
          document.getElementById("micStats").innerHTML = 
            '<span style="color: var(--accent-red)">Mic: Send Error</span>';
        }
      }
    };
    
    pttNode.port.postMessage({
      type: 'setMicGain',
      value: micGain
    });
    
    microphoneSource.connect(pttNode);
    
    // Add a timeout to detect if AudioWorklet is actually working
    setTimeout(() => {
      if (isTransmitting && pttNode) {
        // Check if AudioWorklet has been active
        pttNode.port.postMessage({ type: 'checkStatus' });
      }
    }, 1000);
    
    document.getElementById("micStats").innerHTML = 
      '<span style="color: var(--accent-green)">Mic: Ready for AudioWorklet TX</span>';
    
    window.audioProcessingMode = 'AudioWorklet';
    
  } catch (error) {
    console.error("❌ Error setting up AudioWorklet:", error);
    document.getElementById("micStats").innerHTML = 
      '<span style="color: var(--accent-red)">Mic: AudioWorklet Error</span>';
    
    setupMicrophoneProcessingFallback();
  }
}

function setupMicrophoneProcessingFallback() {
  if (!microphoneStream || !audioCtx) return;
  
  try {
    microphoneSource = audioCtx.createMediaStreamSource(microphoneStream);
    
    const microphoneProcessor = audioCtx.createScriptProcessor(2048, 1, 1);
    
    microphoneProcessor.onaudioprocess = function(event) {
      if (isTransmitting && ws && ws.readyState === WebSocket.OPEN) {
        const inputBuffer = event.inputBuffer;
        const inputData = inputBuffer.getChannelData(0);
        
        const processedData = new Float32Array(inputData.length);
        let totalEnergy = 0;
        let peakLevel = 0;
        
        // SIMPLIFIED FALLBACK: Only apply gain - NO Math.tanh() distortion
        for (let i = 0; i < inputData.length; i++) {
          let sample = inputData[i];
          
          // Apply microphone gain ONLY
          sample *= micGain;
          
          // Basic clipping - NO additional distortion processing
          if (sample > 1.0) sample = 1.0;
          else if (sample < -1.0) sample = -1.0;
          
          processedData[i] = sample;
          
          totalEnergy += sample * sample;
          peakLevel = Math.max(peakLevel, Math.abs(sample));
        }
        
        try {
          // Validate processed audio data is not empty before sending
          if (!processedData.buffer || processedData.buffer.byteLength === 0) {
            console.error("❌ Processed audio data is empty, skipping send");
            return;
          }
          ws.send(processedData.buffer);
          
          const rms = Math.sqrt(totalEnergy / inputData.length);
          const rmsDb = rms > 0 ? (20 * Math.log10(rms)).toFixed(1) : '-∞';
          const peakDb = peakLevel > 0 ? (20 * Math.log10(peakLevel)).toFixed(1) : '-∞';
          
          let statsColor = 'var(--text-secondary)';
          if (rms > 0.1) statsColor = 'var(--accent-green)';
          if (rms > 0.3) statsColor = 'var(--accent-orange)';
          if (peakLevel > 0.8) statsColor = 'var(--accent-red)';
          
          const micStatsElement = document.getElementById("micStats");
          micStatsElement.innerHTML = 
            `<span style="color: ${statsColor}">TX: ${inputData.length}smp @${audioCtx.sampleRate}Hz | RMS:${rmsDb}dB Peak:${peakDb}dB</span>`;
            
        } catch (error) {
          console.error("❌ Failed to send TX audio:", error);
          document.getElementById("micStats").innerHTML = '<span style="color: var(--accent-red)">Mic: Send Error</span>';
        }
      } else {
        document.getElementById("micStats").innerHTML = '<span style="color: var(--text-secondary)">Mic: Ready</span>';
      }
    };
    
    microphoneSource.connect(microphoneProcessor);
    const dummyGain = audioCtx.createGain();
    dummyGain.gain.value = 0;
    microphoneProcessor.connect(dummyGain);
    dummyGain.connect(audioCtx.destination);
    
    document.getElementById("micStats").innerHTML = '<span style="color: var(--accent-green)">Mic: Ready for TX (Fallback)</span>';
    
    window.audioProcessingMode = 'Fallback';
    
  } catch (error) {
    console.error("❌ Error setting up fallback microphone processing:", error);
    document.getElementById("micStats").innerHTML = '<span style="color: var(--accent-red)">Mic: Setup Error</span>';
  }
}

function startPTT(event) {
  if (event) event.preventDefault();
  if (!microphonePermissionGranted || isTransmitting || !ws || ws.readyState !== WebSocket.OPEN) return;
  
  isTransmitting = true;
  document.getElementById("pttButton").classList.add("transmitting");
  document.getElementById("pttStatus").textContent = "TRANSMITTING";
  
  // Tell AudioWorklet to start transmitting
  if (pttNode && pttNode.port) {
    // Ensure mic gain is synced before starting transmission
    pttNode.port.postMessage({
      type: 'setMicGain',
      value: micGain
    });
    pttNode.port.postMessage({
      type: 'startTransmit'
    });
  } else {
    console.error("❌ AudioWorklet not available for transmission");
    stopPTT();
    return;
  }
  
  // Update UI to show transmission status
  document.getElementById("micStats").innerHTML = 
    '<span style="color: var(--accent-green)">AudioWorklet TX Active</span>';
}

function stopPTT(event) {
  if (event) event.preventDefault();
  
  isTransmitting = false;
  document.getElementById("pttButton").classList.remove("transmitting");
  document.getElementById("pttStatus").textContent = microphonePermissionGranted ?
    "Ready - Hold to transmit" : "Microphone permission required";
  
  // Tell AudioWorklet to stop transmitting
  if (pttNode && pttNode.port) {
    pttNode.port.postMessage({
      type: 'stopTransmit'
    });
  }
  
  // Update UI to show ready status
  document.getElementById("micStats").innerHTML = 
    '<span style="color: var(--text-secondary)">Mic: Ready</span>';
}

/**
 * Keyboard Shortcuts
 */
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !e.repeat) {
    e.preventDefault();
    startPTT();
  }
});

document.addEventListener("keyup", (e) => {
  if (e.code === "Space") {
    e.preventDefault();
    stopPTT();
  }
});

/**
 * Browser Compatibility Check
 */
function checkMicrophoneSupport() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    console.warn("⚠️ getUserMedia not supported in this browser");
    document.getElementById("micPermissionPanel").innerHTML = 
      "<h2>Microphone Not Supported</h2><p>Your browser doesn't support microphone access. PTT functionality will not be available.</p>";
    return false;
  }
  
  if (!window.isSecureContext) {
    console.warn("⚠️ Microphone access requires HTTPS or localhost");
    document.getElementById("micPermissionPanel").innerHTML = 
      `<h2>HTTPS Required</h2>
       <p>Microphone access requires a secure connection (HTTPS) or localhost access.</p>
       <p><strong>Current URL:</strong> ${window.location.href}</p>
       <p><strong>Solutions:</strong></p>
       <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
         <li>Access via <code>http://localhost:${window.location.port}</code></li>
         <li>Access via <code>http://127.0.0.1:${window.location.port}</code></li>
         <li>Enable HTTPS on your server</li>
       </ul>`;
    return false;
  }
  
  return true;
}

/**
 * Initialization
 */
updateRoutingDisplay();

if (!checkMicrophoneSupport()) {
  document.getElementById("pttButton").disabled = true;
  document.getElementById("pttStatus").textContent = "Microphone not available";
}

/**
 * Radio Manager Integration Functions
 */

async function updateRadioLastConnected(radioId) {
  if (!radioId || !window.radioManager) return;
  
  try {
    // Update the radio's last connected timestamp via API
    await fetch(`/api/radios/${radioId}/activate`, {
      method: 'POST'
    });
    
    // Refresh radio manager to show updated timestamp
    if (window.radioManager.loadRadios) {
      await window.radioManager.loadRadios();
    }
    
    console.log(`✅ Updated last connected time for radio: ${radioId}`);
    
  } catch (error) {
    console.error('❌ Failed to update radio last connected:', error);
  }
}

function updateRadioManagerConnectionStatus(status) {
  // Update the connection status display in radio manager
  const statusElement = document.getElementById('radioConnectionStatus');
  const activeRadio = window.radioManager?.getActiveRadio();
  
  if (statusElement) {
    if (status === 'connected' && activeRadio) {
      statusElement.textContent = `Connected to ${activeRadio.name}`;
      statusElement.style.color = '#4CAF50'; // Green
    } else if (status === 'disconnected') {
      statusElement.textContent = 'Disconnected';
      statusElement.style.color = '#f44336'; // Red
    } else {
      statusElement.textContent = 'No active radio';
      statusElement.style.color = '#666666'; // Gray
    }
  }
  
  // Update the active radio display status
  const activeRadioElement = document.querySelector('#activeRadioDisplay .radio-details');
  if (activeRadioElement && activeRadio) {
    const lastConnected = window.radioManager?.formatLastConnected(activeRadio.last_connected) || 'Never';
    const currentStatus = status === 'connected' ? 'Connected' : 
                         status === 'disconnected' ? 'Disconnected' : 'Available';
    
    activeRadioElement.innerHTML = `
      ${activeRadio.host}:${activeRadio.port}<br>
      Status: ${currentStatus}<br>
      Last connected: ${lastConnected}
    `;
  }
}

