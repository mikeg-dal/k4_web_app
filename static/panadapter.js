/**
 * K4 Web Control - Panadapter Module (PERFORMANCE OPTIMIZED)
 * 
 * Handles spectrum display, waterfall, and frequency information
 * Updated to sync with Python configuration values
 * 
 * PERFORMANCE FIXES:
 * - Efficient canvas resizing without full reinitialization
 * - Debounced window resize events (100ms)
 * - Throttled divider dragging rendering (~60fps)
 * - Prevents audio/WebSocket disruption during UI interactions
 */

// Configuration values - will be loaded from configuration system
const PanadapterConfig = {
  // STEP 4: These will be replaced by configuration values when available
  DEFAULT_CENTER_FREQ: 14086500,  // Hz - fallback only
  DEFAULT_SPAN: 50000,            // Hz (50 kHz) - fallback only  
  DEFAULT_REF_LEVEL: -110,        // dBm - fallback only
  DEFAULT_SCALE: 47,              // dB scale - fallback only
  DEFAULT_NOISE_FLOOR: -120,      // dBm - fallback only
  MAX_WATERFALL_LINES: 200,       // fallback only
  WATERFALL_HISTORY_SIZE: 50      // fallback only
};

// Global variables
let panadapterCanvases = {};
let panadapterState = {
  centerFrequency: 0,  // WAIT FOR K4: Start as 0 until connected
  span: 50000,         // SAFE DEFAULT: Use 50kHz to prevent 0 span corruption
  referenceLevel: 0,   // WAIT FOR K4: Will be set by K4 response, don't use defaults
  scaleLevel: PanadapterConfig.DEFAULT_SCALE,  // Will be updated by configuration
  spectrumData: [],
  mouseInBounds: false,
  cursorX: -1,
  noiseFloor: PanadapterConfig.DEFAULT_NOISE_FLOOR  // Will be updated by configuration
};

// STEP 4: Configuration loading for panadapter  
function loadPanadapterConfiguration() {
  // Wait for configuration to be available
  if (typeof K4PanadapterUtils !== 'undefined') {
    console.log(`📊 Panadapter.js: Loading configuration-based defaults`);
    
    // Update configuration object with live values
    PanadapterConfig.DEFAULT_CENTER_FREQ = K4PanadapterUtils.getCenterFreq();
    PanadapterConfig.DEFAULT_SPAN = K4PanadapterUtils.getSpan();
    PanadapterConfig.DEFAULT_REF_LEVEL = K4PanadapterUtils.getRefLevel();
    PanadapterConfig.DEFAULT_SCALE = K4PanadapterUtils.getScale();
    PanadapterConfig.DEFAULT_NOISE_FLOOR = K4PanadapterUtils.getNoiseFloor();
    PanadapterConfig.MAX_WATERFALL_LINES = K4PanadapterUtils.getWaterfallLines();
    
    // Update current state to use configuration values
    panadapterState.scaleLevel = PanadapterConfig.DEFAULT_SCALE;
    panadapterState.noiseFloor = PanadapterConfig.DEFAULT_NOISE_FLOOR;
    
    // Update global variables that use these defaults
    maxWaterfallLines = PanadapterConfig.MAX_WATERFALL_LINES;
    waterfallHeight = K4PanadapterUtils.getWaterfallHeight();
    
    console.log(`📊 Panadapter.js: Configuration applied - Scale: ${PanadapterConfig.DEFAULT_SCALE}dB, Noise Floor: ${PanadapterConfig.DEFAULT_NOISE_FLOOR}dBm`);
    console.log(`✅ Panadapter.js: Step 4 complete - Using configuration defaults`);
  } else {
    console.log(`⚠️ Panadapter.js: K4PanadapterUtils not available yet, using fallback defaults`);
  }
}

// Load configuration when K4Config becomes available
window.addEventListener('k4ConfigLoaded', (event) => {
  console.log(`🔧 Panadapter.js: Configuration system loaded, updating panadapter defaults`);
  loadPanadapterConfiguration();
});

// Also try to load configuration immediately (in case config is already loaded)
setTimeout(() => {
  if (window.K4Config && window.K4Config.loaded) {
    console.log(`🔧 Panadapter.js: Configuration already available, loading defaults`);
    loadPanadapterConfiguration();
  }
}, 50);

let panadapterStats = {
  packetsReceived: 0,
  artifactsFiltered: 0,
  fps: 0,
  frameCount: 0,
  lastFrameTime: 0
};

// Waterfall variables
let waterfallData = [];
let waterfallHeight = 200;
let maxWaterfallLines = PanadapterConfig.MAX_WATERFALL_LINES;

// Averaging variables
let spectrumAveragingFactor = 4;  // Default to 4 (from config)
let waterfallAveragingFactor = 2; // Default to 2 (from config)
let averagedSpectrumData = [];    // Holds averaged spectrum data
let averagedWaterfallData = [];   // Holds averaged waterfall data
let spectrumHistory = [];         // Holds recent spectrum data for averaging
let waterfallHistory = [];        // Holds recent waterfall data for averaging

// Resizable divider variables
let isDraggingDivider = false;
let dragStartY = 0;
let originalWaterfallHeight = 0;

// Performance optimization variables
let resizeDebounceTimer = null;
let lastRenderTime = 0;
let isActivelyRendering = false;
let pendingResize = false;

// Debug variables
let spectrumPacketCount = 0;
let lastSpectrumData = null;
let debugMode = false;

/**
 * Update configuration from server
 */
function updatePanadapterConfig(config) {
  if (config) {
    Object.assign(PanadapterConfig, config);
    maxWaterfallLines = PanadapterConfig.MAX_WATERFALL_LINES;
    
    // Update defaults from server config
    // Set K4 averaging value (use spectrum averaging from config as default)
    const k4AvgValue = config.DEFAULT_SPECTRUM_AVERAGING || 4;
    const k4Slider = document.getElementById('k4AveragingSlider');
    const k4Value = document.getElementById('k4AveragingValue');
    if (k4Slider) k4Slider.value = k4AvgValue;
    if (k4Value) k4Value.textContent = k4AvgValue;
    
    // Disable local averaging since K4 handles it now
    spectrumAveragingFactor = 0;
    waterfallAveragingFactor = 0;
    
    console.log(`✅ K4 averaging set to: ${k4AvgValue}`);
    
    // Query K4 for current averaging value first, then set if needed
    if (typeof send === 'function') {
      send(`#AVG;`); // Query current averaging
      // Set our default value after a brief delay to allow query response
      setTimeout(() => {
        if (typeof send === 'function') {
          send(`#AVG${k4AvgValue};`);
        }
      }, 100);
    }
    
    if (config.DEFAULT_WATERFALL_HEIGHT !== undefined) {
      waterfallHeight = config.DEFAULT_WATERFALL_HEIGHT;
    }
    
  }
}

/**
 * Update K4 averaging factor from UI control - replaces both spectrum and waterfall
 */
function updateK4Averaging(value) {
  const avgValue = parseInt(value);
  document.getElementById('k4AveragingValue').textContent = value;
  
  // Send #AVG command to K4 (range 1-20)
  if (typeof send === 'function') {
    send(`#AVG${avgValue};`);
  }
  
  // Disable all local averaging since K4 handles it now
  spectrumAveragingFactor = 0;
  waterfallAveragingFactor = 0;
  spectrumHistory = [];
  waterfallHistory = [];
  averagedSpectrumData = [];
  averagedWaterfallData = [];
}

// Legacy functions for compatibility (now just call the K4 function)
function updateSpectrumAveraging(value) {
  updateK4Averaging(value);
}

function updateWaterfallAveraging(value) {
  updateK4Averaging(value);
}

/**
 * Apply averaging to spectrum data - DISABLED: K4 handles averaging
 */
function applySpectrumAveraging(newSpectrumData) {
  // K4 handles averaging now - return original data unchanged
  return [...newSpectrumData];
}

/**
 * Apply averaging to waterfall data - DISABLED: K4 handles averaging
 */
function applyWaterfallAveraging(newWaterfallData) {
  // K4 handles averaging now - return original data unchanged
  return [...newWaterfallData];
}

/**
 * Calculate center frequency from K4 PAN packet data
 * PAN center frequency is independent from VFO frequency
 */

/**
 * Get center frequency (legacy function for compatibility)
 * @deprecated Use getFrequencyRange().center instead
 */
function calculateCenterFrequency() {
  return getFrequencyRange().center;
}

/**
 * Efficiently resize panadapter canvases without full reinitialization
 * PERFORMANCE FIX: Prevents audio/WebSocket disruption during resize
 */
function resizePanadapterCanvases() {
  const container = document.getElementById('panadapterContainer');
  if (!container || !panadapterCanvases.spectrum) {
    console.warn("⚠️ Cannot resize - container or canvases not available");
    return;
  }

  // PERFORMANCE FIX: Don't resize during active spectrum rendering
  if (isActivelyRendering) {
    pendingResize = true;
    return;
  }

  const rect = container.getBoundingClientRect();
  const width = rect.width - 4;
  const height = rect.height - 4;
  

  // Only update canvas dimensions - no event handler changes
  Object.values(panadapterCanvases).forEach(canvas => {
    if (canvas) {
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
    }
  });

  // Preserve waterfall height ratio or use current absolute value
  const heightRatio = waterfallHeight / (container.clientHeight || 400);
  waterfallHeight = Math.floor(height * Math.min(0.6, Math.max(0.2, heightRatio)));
  
  // Re-render with new dimensions (no data processing restart)
  renderPanadapter();
  
}

/**
 * Initialize panadapter canvases and setup (ONLY CALLED ONCE)
 */
function initializePanadapter() {
  
  const container = document.getElementById('panadapterContainer');
  if (!container) {
    console.error("❌ Panadapter container not found!");
    return;
  }

  panadapterCanvases = {
    spectrum: document.getElementById('spectrumCanvas'),
    overlay: document.getElementById('overlayCanvas'),
    interaction: document.getElementById('interactionCanvas')
  };

  // Check if all canvases exist
  const missingCanvases = Object.entries(panadapterCanvases).filter(([, canvas]) => !canvas);
  if (missingCanvases.length > 0) {
    console.error("❌ Missing canvases:", missingCanvases.map(([name]) => name));
    return;
  }

  // Initial sizing
  resizePanadapterCanvases();
  
  // Setup event handlers (ONLY ONCE)
  setupPanadapterEvents();
  startPanadapterAnimation();
  
  // Initialize VFO A frequency based on packet data
  
}

/**
 * Setup mouse events for panadapter interaction
 */
function setupPanadapterEvents() {
  const canvas = panadapterCanvases.interaction;
  if (!canvas) return;
  
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const height = canvas.height;
    const spectrumHeight = height - waterfallHeight;
    
    // Check if we're near the divider line for resizing
    const dividerY = spectrumHeight;
    const isNearDivider = Math.abs(mouseY - dividerY) <= 5;
    
    if (isDraggingDivider) {
      // Calculate new waterfall height
      const deltaY = mouseY - dragStartY;
      const newWaterfallHeight = Math.max(50, Math.min(height - 100, originalWaterfallHeight - deltaY));
      
      // PERFORMANCE FIX: Only render if height actually changed by significant amount
      if (Math.abs(newWaterfallHeight - waterfallHeight) > 2) {
        waterfallHeight = newWaterfallHeight;
        
        // Throttle rendering during rapid dragging to prevent jitter
        const now = performance.now();
        if (now - lastRenderTime > 16 && !isActivelyRendering) { // ~60fps limit + respect active rendering
          renderPanadapter();
          lastRenderTime = now;
        }
      }
      
      canvas.style.cursor = 'ns-resize';
    } else if (isNearDivider) {
      // Show resize cursor when near divider
      canvas.style.cursor = 'ns-resize';
    } else {
      // Normal cursor and frequency tracking
      canvas.style.cursor = 'crosshair';
      panadapterState.cursorX = mouseX;
      
      
      panadapterState.mouseInBounds = true;
    }
  });

  canvas.addEventListener('mouseleave', () => {
    panadapterState.mouseInBounds = false;
    panadapterState.cursorX = -1;
    canvas.style.cursor = 'default';
  });

  canvas.addEventListener('mousedown', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseY = e.clientY - rect.top;
    const height = canvas.height;
    const spectrumHeight = height - waterfallHeight;
    const dividerY = spectrumHeight;
    
    // Check if clicking on divider line
    if (Math.abs(mouseY - dividerY) <= 5) {
      isDraggingDivider = true;
      dragStartY = mouseY;
      originalWaterfallHeight = waterfallHeight;
      canvas.style.cursor = 'ns-resize';
      e.preventDefault(); // Prevent text selection
    }
  });

  canvas.addEventListener('mouseup', (e) => {
    if (isDraggingDivider) {
      isDraggingDivider = false;
      canvas.style.cursor = 'crosshair';
    }
  });

  window.addEventListener('resize', () => {
    // PERFORMANCE FIX: Debounce window resize to prevent excessive calls
    if (resizeDebounceTimer) {
      clearTimeout(resizeDebounceTimer);
    }
    resizeDebounceTimer = setTimeout(() => {
      resizePanadapterCanvases();
      resizeDebounceTimer = null;
    }, 100); // 100ms debounce
  });
  
}

/**
 * Get the current frequency range for display mapping
 * Uses actual K4 frequency boundaries for perfect alignment
 */
function getFrequencyRange() {
  const centerFreq = panadapterState.centerFrequency;
  const numBins = panadapterState.spectrumData.length;
  
  // Use actual start/end frequencies from K4 if available
  if (panadapterState.actualStartFreq && panadapterState.actualEndFreq) {
    const actualStart = panadapterState.actualStartFreq;
    const actualEnd = panadapterState.actualEndFreq;
    const actualSpan = actualEnd - actualStart;
    
    return {
      start: actualStart,
      end: actualEnd,
      center: centerFreq,
      span: actualSpan,
      numBins: numBins,
      hzPerBin: numBins > 0 ? actualSpan / numBins : 0
    };
  }
  
  // Fallback to calculated span
  const span = panadapterState.actualSpan || panadapterState.span;
  return {
    start: centerFreq - (span / 2),
    end: centerFreq + (span / 2),
    center: centerFreq,
    span: span,
    numBins: numBins,
    hzPerBin: numBins > 0 ? span / numBins : 0
  };
}

/**
 * Convert X coordinate to frequency using corrected frequency mapping
 * CORRECTED: Uses consistent frequency range calculation for perfect K4 alignment
 */
function viewXToFrequency(x) {
  const width = panadapterCanvases.spectrum.width;
  const freqRange = getFrequencyRange();
  
  // CORRECTED: Use freqRange span instead of panadapterState.span for consistency
  const totalDisplaySpan = freqRange.end - freqRange.start;
  const hzPerPixel = totalDisplaySpan / width;
  
  // Direct frequency mapping from pixel position using actual K4 boundaries
  return Math.round(freqRange.start + (x * hzPerPixel));
}

/**
 * Convert frequency to X coordinate using corrected frequency mapping
 * CORRECTED: Uses consistent frequency range calculation for perfect K4 alignment
 */
function frequencyToViewX(frequency) {
  const width = panadapterCanvases.spectrum.width;
  const freqRange = getFrequencyRange();
  
  // CORRECTED: Use freqRange span instead of panadapterState.span for consistency
  const totalDisplaySpan = freqRange.end - freqRange.start;
  const pixelsPerHz = width / totalDisplaySpan;
  
  // Direct pixel mapping from frequency using actual K4 boundaries
  return (frequency - freqRange.start) * pixelsPerHz;
}

/**
 * Start event-driven rendering (no continuous animation loop)
 */
function startPanadapterAnimation() {
  // Initialize FPS tracking without continuous animation
  panadapterStats.lastFrameTime = performance.now();
  
  // Only render when explicitly requested (when new data arrives)
  
  // Initial render - even if no data yet
  renderPanadapter();
  
  // Emergency: Force a render once after 10 seconds if no data (only once, not spamming)
  setTimeout(() => {
    if (spectrumPacketCount === 0) {
      renderPanadapter();
    }
  }, 10000);
}

/**
 * Main rendering function with rendering conflict prevention
 */
function renderPanadapter() {
  // PERFORMANCE FIX: Prevent rendering conflicts during active spectrum processing
  if (isActivelyRendering) {
    // Skip logging to reduce console spam
    return;
  }
  
  isActivelyRendering = true;
  
  try {
    renderSpectrum();
    renderWaterfall();
    renderOverlay();
    
    
    // Check if resize was pending during rendering
    if (pendingResize) {
      pendingResize = false;
      setTimeout(() => {
        if (!isActivelyRendering) {
          resizePanadapterCanvases();
        }
      }, 10);
    }
    
  } catch (error) {
    console.error("❌ Error in renderPanadapter():", error);
    console.error("   - panadapterCanvases:", panadapterCanvases);
    console.error("   - waterfallHeight:", waterfallHeight);
    console.error("   - panadapterState.spectrumData length:", panadapterState.spectrumData?.length);
  } finally {
    isActivelyRendering = false;
  }
}

/**
 * Render spectrum data (top portion)
 */
function renderSpectrum() {
  const canvas = panadapterCanvases.spectrum;
  if (!canvas) {
    console.error("❌ SPECTRUM: No canvas found!");
    return;
  }
  
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const spectrumHeight = height - waterfallHeight;


  // Clear only the spectrum portion
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, width, spectrumHeight);

  if (panadapterState.spectrumData.length === 0) {
    ctx.fillStyle = '#ff6b6b';
    ctx.font = '14px monospace';
    ctx.fillText('No spectrum data received', 10, 30);
    return;
  }

  // Apply averaging to spectrum data
  const spectrumDataToRender = applySpectrumAveraging(panadapterState.spectrumData);
  

  

  ctx.beginPath();
  ctx.strokeStyle = '#ffeb3b';
  ctx.fillStyle = 'rgba(255, 235, 59, 0.25)';
  ctx.lineWidth = 1;

  // Start path from bottom of spectrum area
  ctx.moveTo(0, spectrumHeight);

  // SMOOTH SPECTRUM LINE: Use proper path-based rendering with edge fixes
  const bins = spectrumDataToRender.length;
  
  // Create grey gradient for spectrum fill
  const gradient = ctx.createLinearGradient(0, 0, 0, spectrumHeight);
  gradient.addColorStop(0, 'rgba(200, 200, 200, 0.8)');  // Lighter grey at top
  gradient.addColorStop(1, 'rgba(100, 100, 100, 0.3)');  // Darker grey at bottom
  
  ctx.fillStyle = gradient;
  ctx.lineWidth = 1.5;
  
  ctx.beginPath();
  
  for (let i = 0; i < bins; i++) {
    // Map each bin to its pixel position ensuring complete coverage
    const x = (i * width) / bins;
    
    const dbValue = spectrumDataToRender[i];
    
    // Handle K4's actual dB range to make spectrum visible
    // Your data: -148 to -150 dB, we need to scale this properly for display
    
    // Use absolute dB values, not relative to reference level
    // Map -155 dB (noise floor) to bottom, -50 dB (strong signal) to top
    const minDisplayDb = -155;
    
    // Clamp and normalize: -155dB=0%, -50dB=100%
    const normalizedValue = Math.max(0, Math.min(1, (dbValue - minDisplayDb) / 105));
    const y = spectrumHeight - (normalizedValue * spectrumHeight);

    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
    
  }

  // Complete the filled area path to ensure edge coverage
  if (bins > 0) {
    // EDGE FIX: Extend spectrum line to full width to eliminate edge artifacts
    const lastBinX = ((bins - 1) * width) / bins;
    
    // Use same scaling as in the loop
    const minDisplayDb = -155;
    const lastDbValue = spectrumDataToRender[bins - 1];
    const lastNormalizedValue = Math.max(0, Math.min(1, (lastDbValue - minDisplayDb) / 105));
    const lastBinY = spectrumHeight - (lastNormalizedValue * spectrumHeight);
    
    // Ensure line extends all the way to right edge
    if (lastBinX < width) {
      ctx.lineTo(width, lastBinY);
    }
    
    // Line to bottom right corner
    ctx.lineTo(width, spectrumHeight);
    // Line to bottom left corner
    ctx.lineTo(0, spectrumHeight);
    // Close the path
    ctx.closePath();
    
    // Fill the spectrum with gradient
    ctx.fill();
    
    // Draw white outline along the top of the spectrum trace
    ctx.strokeStyle = '#ffffff';  // White outline
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    // Redraw just the top line for the white outline
    for (let i = 0; i < bins; i++) {
      const x = (i * width) / bins;
      const dbValue = spectrumDataToRender[i];
      const minDisplayDb = -155;
      const normalizedValue = Math.max(0, Math.min(1, (dbValue - minDisplayDb) / 105));
      const y = spectrumHeight - (normalizedValue * spectrumHeight);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    // Extend to right edge if needed
    if (bins > 0) {
      const lastBinX = ((bins - 1) * width) / bins;
      const minDisplayDb = -155;
      const lastDbValue = spectrumDataToRender[bins - 1];
      const lastNormalizedValue = Math.max(0, Math.min(1, (lastDbValue - minDisplayDb) / 105));
      const lastBinY = spectrumHeight - (lastNormalizedValue * spectrumHeight);
      
      if (lastBinX < width) {
        ctx.lineTo(width, lastBinY);
      }
    }
    
    ctx.stroke();
  }

}

/**
 * Render waterfall (bottom portion)
 */
function renderWaterfall() {
  const canvas = panadapterCanvases.spectrum;
  if (!canvas || panadapterState.spectrumData.length === 0) return;
  
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const spectrumHeight = height - waterfallHeight;
  const waterfallStartY = spectrumHeight;

  // Clear waterfall area
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, waterfallStartY, width, waterfallHeight);

  if (waterfallData.length === 0) return;

  // Render waterfall lines (newest at top, oldest at bottom)
  const lineHeight = waterfallHeight / Math.max(waterfallData.length, maxWaterfallLines);
  
  for (let lineIdx = 0; lineIdx < waterfallData.length; lineIdx++) {
    const waterfallLine = waterfallData[lineIdx];
    
    // Proper waterfall flow top-to-bottom
    // With unshift() data management:
    // waterfallData[0] = newest → top of display  
    // waterfallData[length-1] = oldest → bottom of display
    // lineIdx directly maps to Y position (newest at top)
    const yPosition = waterfallStartY + lineIdx * lineHeight;
    
    renderWaterfallLine(ctx, waterfallLine.data, yPosition, lineHeight, width);
  }

}

/**
 * Render a single waterfall line with research-based color mapping
 */
function renderWaterfallLine(ctx, spectrumData, yPosition, lineHeight, width) {
  // PERFORMANCE OPTIMIZATION: Use ImageData for faster pixel manipulation
  const imageData = ctx.createImageData(width, Math.ceil(lineHeight));
  const imageDataArray = imageData.data;
  
  for (let i = 0; i < spectrumData.length; i++) {
    const dbValue = spectrumData[i];
    
    // K4-style dynamic range matching real radio behavior
    // The K4 reference level determines the "center" of the visible range
    const adjustedDb = dbValue - panadapterState.referenceLevel;
    
    // K4 uses approximately 60-70 dB dynamic range with reference level as the midpoint
    // Signals 30dB below reference = black, signals 30dB above reference = bright colors
    const minRelativeDb = -35;  // Signals 35dB below reference = pure black (like K4 at -100)
    const maxRelativeDb = +25;  // Signals 25dB above reference = bright yellow/red
    const normalizedDb = Math.max(0, Math.min(1, (adjustedDb - minRelativeDb) / (maxRelativeDb - minRelativeDb)));
    
    
    // Calculate pixel range for this bin
    const xStart = Math.floor((i * width) / spectrumData.length);
    const xEnd = Math.floor(((i + 1) * width) / spectrumData.length);
    
    
    // Create color based on signal strength - REALISTIC RADIO PALETTE
    let r, g, b;
    
    // K4 BACKGROUND COLOR based on reference level and signal strength
    // Background changes based on reference level: Pink→Orange→Green→Blue→Black
    // Signals have their own color palette on top of this background
    
    // Step 1: Determine background color based on reference level
    let bgR, bgG, bgB;
    const refLevel = panadapterState.referenceLevel;
    
    // Get waterfall thresholds from configuration
    const thresholds = (typeof K4PanadapterUtils !== 'undefined' && K4PanadapterUtils.getWaterfallThresholds) ? 
        K4PanadapterUtils.getWaterfallThresholds() : 
        { pink: -185, orange: -180, green: -160, blue: -145, royal: -130, black: -120 }; // Fallback
    
    if (refLevel <= thresholds.orange) {
      // Pink/Salmon background
      bgR = 180; bgG = 120; bgB = 140; 
    } else if (refLevel <= thresholds.green) {
      // Orange/Tangerine background  
      const t = (refLevel - thresholds.orange) / (thresholds.green - thresholds.orange);
      bgR = Math.floor(180 + t * 75); bgG = Math.floor(120 + t * 60); bgB = Math.floor(140 - t * 100);
    } else if (refLevel <= thresholds.blue) {
      // Lime green background
      const t = (refLevel - thresholds.green) / (thresholds.blue - thresholds.green);
      bgR = Math.floor(255 - t * 155); bgG = Math.floor(180 + t * 75); bgB = Math.floor(40 + t * 60);
    } else if (refLevel <= thresholds.royal) {
      // Greenish blue background
      const t = (refLevel - thresholds.blue) / (thresholds.royal - thresholds.blue);  
      bgR = Math.floor(100 - t * 100); bgG = Math.floor(255 - t * 155); bgB = Math.floor(100 + t * 100);
    } else if (refLevel <= thresholds.black) {
      // Royal blue background
      const t = (refLevel - thresholds.royal) / (thresholds.black - thresholds.royal);
      bgR = 0; bgG = Math.floor(100 - t * 100); bgB = Math.floor(200 + t * 55);
    } else {
      // Black background
      bgR = 0; bgG = 0; bgB = 0;
    }
    
    // Step 2: Apply signal enhancement on top of background
    if (normalizedDb < 0.1) {
      // Pure background color (no signal)
      r = bgR; g = bgG; b = bgB;
    } else if (normalizedDb < 0.4) {
      // Weak signal: Slightly brighter background
      const t = (normalizedDb - 0.1) / 0.3;
      r = Math.floor(bgR + t * (255 - bgR) * 0.2);
      g = Math.floor(bgG + t * (255 - bgG) * 0.2); 
      b = Math.floor(bgB + t * (255 - bgB) * 0.3);
    } else if (normalizedDb < 0.7) {
      // Medium signal: Royal blue  
      const t = (normalizedDb - 0.4) / 0.3;
      r = Math.floor(bgR * (1-t)); g = Math.floor(bgG * (1-t) + t * 64); b = Math.floor(bgB * (1-t) + t * 200);
    } else {
      // Strong signal: Bright blue-white
      const t = (normalizedDb - 0.7) / 0.3;
      r = Math.floor(t * 150); g = Math.floor(64 + t * 191); b = Math.floor(200 + t * 55);
    }
    
    // PERFORMANCE OPTIMIZATION: Fill pixels in ImageData for this bin
    for (let x = xStart; x < xEnd; x++) {
      for (let y = 0; y < Math.ceil(lineHeight); y++) {
        const pixelIndex = (y * width + x) * 4;
        if (pixelIndex < imageDataArray.length - 3) {
          imageDataArray[pixelIndex] = r;     // Red
          imageDataArray[pixelIndex + 1] = g; // Green  
          imageDataArray[pixelIndex + 2] = b; // Blue
          imageDataArray[pixelIndex + 3] = 255; // Alpha
        }
      }
    }
  }
  
  // Draw the entire line at once using ImageData
  ctx.putImageData(imageData, 0, Math.floor(yPosition));
}

/**
 * Render overlay (grid, cursors, etc.)
 */
function renderOverlay() {
  const canvas = panadapterCanvases.overlay;
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const spectrumHeight = height - waterfallHeight;

  ctx.clearRect(0, 0, width, height);

  // Grid lines for spectrum area only
  ctx.strokeStyle = 'rgba(74, 158, 255, 0.3)';
  ctx.lineWidth = 0.5;
  ctx.setLineDash([1, 2]);

  // Get current frequency range
  const freqRange = getFrequencyRange();

  // Frequency grid (vertical lines)
  const frequencyStep = panadapterState.span < 50000 ? 10000 : 25000;
  const startFreq = Math.floor(freqRange.start / frequencyStep) * frequencyStep;

  for (let freq = startFreq; freq <= freqRange.end; freq += frequencyStep) {
    const x = frequencyToViewX(freq);
    if (x >= 0 && x <= width) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height); // Full height for frequency lines
      ctx.stroke();
    }
  }

  // dB grid (horizontal lines in spectrum area only)
  for (let db = 0; db < 60; db += 10) {
    const y = (db / 60) * spectrumHeight;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Separator line between spectrum and waterfall (resizable)
  ctx.strokeStyle = isDraggingDivider ? 'rgba(74, 158, 255, 1.0)' : 'rgba(255, 255, 255, 0.7)';
  ctx.lineWidth = isDraggingDivider ? 3 : 2;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(0, spectrumHeight);
  ctx.lineTo(width, spectrumHeight);
  ctx.stroke();
  
  // Add resize indicator in the center of divider
  if (isDraggingDivider) {
    ctx.fillStyle = 'rgba(74, 158, 255, 0.8)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('⟷ DRAG TO RESIZE ⟷', width/2, spectrumHeight - 5);
    ctx.textAlign = 'left'; // Reset text alignment
  }



  // Reference level label
  ctx.fillStyle = '#ffffff';
  ctx.font = '12px monospace';
  ctx.fillText(panadapterState.referenceLevel + "dBm", 5, spectrumHeight - 10);
  
  
  // Waterfall label
  ctx.textAlign = 'left';
  ctx.fillStyle = '#ffffff';
  ctx.fillText('Waterfall', 5, spectrumHeight + 20);
}


/**
 * Handle incoming spectrum data - MAIN FUNCTION
 * Event-driven rendering for optimal performance
 */
// Global variables for frame rate limiting
let panadapterLastRenderTime = 0;
const TARGET_FPS = 30; // Limit to 30 FPS to reduce GPU usage
const FRAME_INTERVAL = 1000 / TARGET_FPS; // ~33ms between frames

function handleBoundaryUpdate(data) {
  /**
   * SIMPLIFIED BOUNDARY UPDATE: Just update center frequency and span
   * All frequency calculations will derive from these two values
   */
  
  // UPDATE ONLY BASIC STATE: center frequency and span
  panadapterState.centerFrequency = data.center_frequency;
  panadapterState.span = data.span;
  panadapterState.actualSpan = data.span;  // Store actual span for accurate frequency mapping
  
  // Update overlay immediately to show new frequency labels
  if (panadapterCanvases.overlay) {
    renderOverlay();
  }
  
}

function handleSpectrumData(data) {
  spectrumPacketCount++;
  lastSpectrumData = data;
  
  // PERFORMANCE OPTIMIZATION: Limit rendering to 30 FPS to reduce GPU usage
  const currentTimeNow = performance.now();
  if (currentTimeNow - panadapterLastRenderTime < FRAME_INTERVAL) {
    // Skip this frame to maintain 30 FPS limit
    return;
  }
  panadapterLastRenderTime = currentTimeNow;
  
  
  // Track FPS for event-driven rendering
  const currentTimeForStats = performance.now();
  panadapterStats.frameCount++;
  
  if (currentTimeForStats - panadapterStats.lastFrameTime >= 1000) {
    panadapterStats.fps = panadapterStats.frameCount;
    panadapterStats.frameCount = 0;
    panadapterStats.lastFrameTime = currentTimeForStats;
    
    // CRITICAL FIX: Update main stats display (was missing from event-driven model)
    updateSpectrumStats();
  }
  
  // Update panadapter state - SIMPLIFIED
  panadapterState.centerFrequency = data.center_frequency;
  panadapterState.span = data.span;
  panadapterState.actualSpan = data.span;  // Store actual span for accurate frequency mapping
  
  // CAPTURE ACTUAL K4 FREQUENCY BOUNDARIES for perfect alignment
  if (data.actual_start_freq && data.actual_end_freq) {
    panadapterState.actualStartFreq = data.actual_start_freq;
    panadapterState.actualEndFreq = data.actual_end_freq;
  } else {
    console.log(`❌ Missing actual frequency boundaries from backend`);
  }
  
  // Span data processed successfully
  
  // Round reference level to whole numbers like K4 display and only log significant changes
  const newRefLevel = Math.round(data.reference_level);
  const currentRefLevel = Math.round(panadapterState.referenceLevel);
  
  panadapterState.referenceLevel = newRefLevel;
  
  panadapterState.spectrumData = data.spectrum_data;
  
  
  
  
  panadapterStats.packetsReceived++;

  // Add to waterfall history (USING AVERAGED DATA)
  if (data.spectrum_data.length > 0) {
    // Apply averaging to waterfall data
    const waterfallDataToAdd = applyWaterfallAveraging(data.spectrum_data);
    
    // Add new data to front of array for proper waterfall flow
    // This way newest data is at index 0 (top) and oldest data flows down
    waterfallData.unshift({
      data: [...waterfallDataToAdd], // Use averaged data
      timestamp: Date.now() / 1000
    });
    
    
    // Limit waterfall history - remove from end (oldest data)
    if (waterfallData.length > maxWaterfallLines) {
      waterfallData.pop();
    }
  }

  
  // CRITICAL FIX: Update main stats display immediately (for responsive UI)
  // Don't wait for the 1-second FPS update cycle
  if (spectrumPacketCount % 5 === 0) {
    updateSpectrumStats();
  }
  
  // CRITICAL FIX: Event-driven rendering - only render when new data arrives
  // This prevents the continuous redrawing/restarting issue
  renderPanadapter();
}


/**
 * Update frequency displays
 */

/**
 * Update spectrum statistics
 */
function updateSpectrumStats() {
  const statsElem = document.getElementById('spectrumStats');
  if (statsElem) {
    const binCount = panadapterState.spectrumData.length;
    statsElem.textContent = "Bins: " + binCount + " | Rate: " + panadapterStats.fps + " fps | Waterfall: " + waterfallData.length + " lines";
  }
}

/**
 * Format frequency for display
 */
function formatFrequency(frequency) {
  if (!frequency) return '----.---.---';
  const mhz = Math.floor(frequency / 1000000);
  const khz = Math.floor((frequency % 1000000) / 1000);
  const hz = frequency % 1000;
  return mhz + "." + khz.toString().padStart(3, '0') + "." + hz.toString().padStart(3, '0');
}





/**
 * VFO and Filter Overlay State
 */
let vfoOverlayState = {
  vfoA: { 
    frequency: 0, 
    filter: { 
      current: 0, 
      mode: '', 
      hi: 0, 
      lo: 0, 
      bw: 0, 
      shft: 0 
    } 
  },
  vfoB: { 
    frequency: 0, 
    filter: { 
      current: 0, 
      mode: '', 
      hi: 0, 
      lo: 0, 
      bw: 0, 
      shft: 0 
    } 
  },
  subRXEnabled: false
};

/**
 * Update VFO overlay state from external sources
 */
function updateVFOOverlay(vfo, data) {
  if (vfoOverlayState[vfo]) {
    if (data.frequency !== undefined) {
      vfoOverlayState[vfo].frequency = data.frequency;
    }
    if (data.filter !== undefined) {
      vfoOverlayState[vfo].filter = { ...vfoOverlayState[vfo].filter, ...data.filter };
    }
    if (data.mode !== undefined) {
      vfoOverlayState[vfo].mode = data.mode;
    }
    if (data.subRXEnabled !== undefined) {
      vfoOverlayState.subRXEnabled = data.subRXEnabled;
    }
    
    // Trigger overlay re-render
    if (panadapterCanvases.overlay) {
      renderOverlay();
    }
  }
}

/**
 * Render VFO markers and filter passbands on overlay canvas
 */
function renderOverlay() {
  const canvas = panadapterCanvases.overlay;
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const spectrumHeight = height - waterfallHeight;
  
  // Clear overlay
  ctx.clearRect(0, 0, width, height);
  
  // Skip rendering if no valid frequency data
  if (!panadapterState.centerFrequency || !panadapterState.span) {
    return;
  }
  
  // Render VFO A (Blue)
  if (vfoOverlayState.vfoA.frequency > 0) {
    renderVFOMarker(ctx, 'A', vfoOverlayState.vfoA, width, spectrumHeight, 'rgba(74, 144, 226, 0.8)');
    renderFilterPassband(ctx, 'A', vfoOverlayState.vfoA, width, height, 'rgba(74, 144, 226, 0.3)');
  }
  
  // Render VFO B (Green)
  if (vfoOverlayState.vfoB.frequency > 0) {
    renderVFOMarker(ctx, 'B', vfoOverlayState.vfoB, width, spectrumHeight, 'rgba(102, 179, 102, 0.8)');
    renderFilterPassband(ctx, 'B', vfoOverlayState.vfoB, width, height, 'rgba(102, 179, 102, 0.3)');
  }
}

/**
 * Render a single VFO frequency marker
 */
function renderVFOMarker(ctx, vfo, vfoData, width, spectrumHeight, color) {
  const frequency = vfoData.frequency;
  const x = frequencyToViewX(frequency);
  
  // Check if frequency is within visible range
  if (x < 0 || x > width) return;
  
  // Draw vertical line
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(x, 0);
  ctx.lineTo(x, spectrumHeight);
  ctx.stroke();
  
  // Draw VFO label
  ctx.fillStyle = color;
  ctx.font = 'bold 12px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`VFO ${vfo}`, x, 15);
  
  // Draw frequency label
  ctx.font = '10px monospace';
  const freqMHz = (frequency / 1000000).toFixed(3);
  ctx.fillText(`${freqMHz}`, x, 30);
}

/**
 * Render filter passband overlay
 */
function renderFilterPassband(ctx, vfo, vfoData, width, height, color) {
  const centerFreq = vfoData.frequency;
  const filter = vfoData.filter;
  
  if (!filter) return;
  
  let lowFreq, highFreq;
  
  // Get CW pitch offset - PITCH affects filter placement in CW mode
  // PITCH value is sidetone pitch x10 Hz (25-95), so multiply by 10 to get actual Hz
  const pitchOffset_hz = filter.pitch ? (filter.pitch * 10) : 500; // Default to 500Hz if no pitch
  
  // Detect different operating modes for sideband-aware filter positioning
  const isCWMode = vfoData.mode && (vfoData.mode.toUpperCase() === 'CW' || vfoData.mode.toUpperCase() === 'CW-R');
  const isLSBMode = vfoData.mode && (
    vfoData.mode.toUpperCase() === 'LSB' || 
    vfoData.mode.toUpperCase() === 'DATA-R'
  );
  const isUSBMode = vfoData.mode && (
    vfoData.mode.toUpperCase() === 'USB' || 
    vfoData.mode.toUpperCase() === 'DATA'
  );
  
  // Calculate passband edges using BW/SHFT mode with sideband awareness
  // BW/SHFT mode: bw is bandwidth, shft is center of passband with sideband awareness
  const bandwidth_hz = filter.bw * 1000;
  const shift_hz = filter.shft * 1000;
  
  // Calculate passband center with sideband-aware positioning
  let passbandCenter;
  if (isLSBMode) {
    // LSB: Shift below carrier frequency (negative offset from VFO)
    passbandCenter = centerFreq - shift_hz;
  } else {
    // USB/CW/AM: Shift above carrier frequency (positive offset from VFO)
    passbandCenter = centerFreq + shift_hz;
  }
  
  // Apply CW pitch offset if in CW mode (regardless of sideband)
  if (isCWMode) {
    // In CW mode, the filter needs to be offset by the pitch frequency
    // to align with the actual received tone
    passbandCenter -= pitchOffset_hz;
  }
  
  lowFreq = passbandCenter - (bandwidth_hz / 2);   // Bottom = center - half-width
  highFreq = passbandCenter + (bandwidth_hz / 2);  // Top = center + half-width
  
  // Convert to pixel coordinates
  const lowX = frequencyToViewX(lowFreq);
  const highX = frequencyToViewX(highFreq);
  
  // Check if passband is within visible range
  if (highX < 0 || lowX > width) return;
  
  // Clamp to canvas bounds
  const startX = Math.max(0, lowX);
  const endX = Math.min(width, highX);
  const passbandWidth_px = endX - startX;
  
  if (passbandWidth_px <= 0) return;
  
  // Draw passband rectangle with VFO colors (blue for VFO A, green for VFO B)
  ctx.fillStyle = color;
  ctx.fillRect(startX, 0, passbandWidth_px, height);
  
  // Draw passband edges as dashed lines with VFO colors
  ctx.strokeStyle = color.replace('0.3', '0.8'); // More opaque for edges
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  
  if (lowX >= 0 && lowX <= width) {
    ctx.beginPath();
    ctx.moveTo(lowX, 0);
    ctx.lineTo(lowX, height);
    ctx.stroke();
  }
  
  if (highX >= 0 && highX <= width) {
    ctx.beginPath();
    ctx.moveTo(highX, 0);
    ctx.lineTo(highX, height);
    ctx.stroke();
  }
  
  // Reset dash pattern
  ctx.setLineDash([]);
}

/**
 * Handle #AVG command response from K4
 */
function handleAveragingResponse(avgValue) {
  const k4Slider = document.getElementById('k4AveragingSlider');
  const k4Value = document.getElementById('k4AveragingValue');
  
  if (k4Slider && k4Value) {
    k4Slider.value = avgValue;
    k4Value.textContent = avgValue;
    console.log(`✅ Updated averaging slider from K4: ${avgValue}`);
  }
}

// Export functions for global access
window.initializePanadapter = initializePanadapter;
window.resizePanadapterCanvases = resizePanadapterCanvases;
window.handleSpectrumData = handleSpectrumData;
window.updatePanadapterConfig = updatePanadapterConfig;
window.updateK4Averaging = updateK4Averaging;
window.updateSpectrumAveraging = updateSpectrumAveraging;
window.updateWaterfallAveraging = updateWaterfallAveraging;
window.handleAveragingResponse = handleAveragingResponse;
window.updateVFOOverlay = updateVFOOverlay;
window.renderOverlay = renderOverlay;

// Set panadapter state globally for other modules
window.panadapterState = panadapterState;
window.PanadapterConfig = PanadapterConfig;
window.vfoOverlayState = vfoOverlayState;

