/**
 * K4 Web Controller - Safe Configuration Loading System
 * 
 * This module provides safe configuration loading without breaking existing functionality.
 * It loads configuration from the backend API and provides it to other modules,
 * while maintaining full backward compatibility with hardcoded values.
 */

// Global configuration state
window.K4Config = {
    loaded: false,
    data: null,
    fallbackActive: false,
    version: '1.0.0'
};

/**
 * Safely load configuration from the backend API
 * This function will NOT break existing functionality - it only adds new capabilities
 */
async function loadK4Configuration() {
    console.log('🔧 K4 Config Loader: Starting safe configuration load...');
    
    try {
        const startTime = performance.now();
        const response = await fetch('/api/config/all');
        
        if (!response.ok) {
            throw new Error(`Config API returned ${response.status}: ${response.statusText}`);
        }
        
        const config = await response.json();
        const loadTime = Math.round(performance.now() - startTime);
        
        // Validate configuration structure
        if (!config.audio || !config.network || !config.panadapter) {
            throw new Error('Invalid configuration structure received');
        }
        
        // Store configuration globally
        window.K4Config.data = config;
        window.K4Config.loaded = true;
        window.K4Config.fallbackActive = !!config.fallback;
        
        console.log(`✅ K4 Config Loader: Configuration loaded successfully in ${loadTime}ms`);
        console.log(`📊 Config version: ${config.version || 'unknown'}`);
        console.log(`🎤 Mic gain: ${config.audio.mic_gain}`);
        console.log(`🌐 K4 host: ${config.network.k4_host}:${config.network.k4_port}`);
        console.log(`📻 Panadapter: ${config.panadapter.center_freq}Hz ±${config.panadapter.span/2}Hz`);
        
        // Emit configuration loaded event for other modules to listen to
        const configEvent = new CustomEvent('k4ConfigLoaded', {
            detail: { config: config, loadTime: loadTime }
        });
        window.dispatchEvent(configEvent);
        
        return config;
        
    } catch (error) {
        console.warn('⚠️ K4 Config Loader: Failed to load configuration from API:', error.message);
        console.log('🔄 K4 Config Loader: Using safe fallback configuration');
        
        // Safe fallback configuration that matches existing hardcoded values
        const fallbackConfig = {
            audio: {
                mic_gain: 0.1,
                input_sample_rate: 48000,
                output_sample_rate: 12000,
                frame_size: 480,
                volume: {
                    user_min: 0,
                    user_max: 100,
                    internal_max: 200,
                    master_internal_max: 300,
                    default_main: 10,
                    default_sub: 10,
                    default_master: 75
                }
            },
            network: {
                k4_host: "192.168.1.10",
                k4_port: 9205,
                web_port: 8000
            },
            vfo: {
                freq_min: 1000000,
                freq_max: 30000000
            },
            panadapter: {
                center_freq: 14086500,
                span: 50000,
                ref_level: -110,
                scale: 70,
                waterfall_lines: 200,
                waterfall_thresholds: {
                    pink: -185,
                    orange: -180,
                    green: -160,
                    blue: -145,
                    royal: -130,
                    black: -120
                }
            },
            modes: {
                cat_mode_map: {
                    '1': 'LSB',
                    '2': 'USB',
                    '3': 'CW', 
                    '4': 'FM',
                    '5': 'AM',
                    '6': 'DATA',
                    '7': 'CW-R',
                    '9': 'DATA-R'
                }
            },
            fallback: true,
            version: 'fallback-1.0.0'
        };
        
        window.K4Config.data = fallbackConfig;
        window.K4Config.loaded = true;
        window.K4Config.fallbackActive = true;
        
        // Still emit the event so other modules can handle fallback gracefully
        const configEvent = new CustomEvent('k4ConfigLoaded', {
            detail: { config: fallbackConfig, error: error.message, fallback: true }
        });
        window.dispatchEvent(configEvent);
        
        return fallbackConfig;
    }
}

/**
 * Get configuration value safely with fallback
 * This function will never break - it always returns a sensible default
 */
function getConfigValue(path, defaultValue) {
    if (!window.K4Config.loaded || !window.K4Config.data) {
        console.warn(`⚠️ K4 Config: Configuration not loaded, using default for ${path}`);
        return defaultValue;
    }
    
    const pathParts = path.split('.');
    let current = window.K4Config.data;
    
    for (const part of pathParts) {
        if (current && typeof current === 'object' && part in current) {
            current = current[part];
        } else {
            console.warn(`⚠️ K4 Config: Path ${path} not found, using default:`, defaultValue);
            return defaultValue;
        }
    }
    
    return current;
}

/**
 * Volume calculation utilities using dynamic configuration
 * These functions are safe to use and will fall back to existing behavior
 */
const K4VolumeUtils = {
    /**
     * Calculate main volume (VFO A) using configuration
     */
    calculateMainVolume(userValue) {
        const internalMax = getConfigValue('audio.volume.internal_max', 200);
        return (userValue / 100) * (internalMax / 100); // Scale to 0-2.0 range
    },
    
    /**
     * Calculate sub volume (VFO B) using configuration  
     */
    calculateSubVolume(userValue) {
        const internalMax = getConfigValue('audio.volume.internal_max', 200);
        return (userValue / 100) * (internalMax / 100); // Scale to 0-2.0 range
    },
    
    /**
     * Calculate master volume using configuration
     */
    calculateMasterVolume(userValue) {
        const masterMax = getConfigValue('audio.volume.master_internal_max', 300);
        return (userValue / 100) * (masterMax / 100); // Scale to 0-3.0 range
    },
    
    /**
     * Get default volume values
     */
    getDefaults() {
        return {
            main: getConfigValue('audio.volume.default_main', 10),
            sub: getConfigValue('audio.volume.default_sub', 10),
            master: getConfigValue('audio.volume.default_master', 75),
            micGain: getConfigValue('audio.mic_gain', 0.1)
        };
    }
};

/**
 * Network configuration utilities
 */
const K4NetworkUtils = {
    getK4Host() {
        return getConfigValue('network.k4_host', '192.168.1.10');
    },
    
    getK4Port() {
        return getConfigValue('network.k4_port', 9205);
    },
    
    getWebPort() {
        return getConfigValue('network.web_port', 8000);
    }
};

/**
 * Panadapter configuration utilities
 */
const K4PanadapterUtils = {
    getCenterFreq() {
        return getConfigValue('panadapter.center_freq', 14086500);
    },
    
    getSpan() {
        return getConfigValue('panadapter.span', 50000);
    },
    
    getRefLevel() {
        return getConfigValue('panadapter.ref_level', -110);
    },
    
    getScale() {
        return getConfigValue('panadapter.scale', 70);
    },
    
    getNoiseFloor() {
        return getConfigValue('panadapter.noise_floor', -120);
    },
    
    getWaterfallHeight() {
        return getConfigValue('panadapter.waterfall_height', 237);
    },
    
    getWaterfallLines() {
        return getConfigValue('panadapter.waterfall_lines', 200);
    },
    
    getWaterfallThresholds() {
        return getConfigValue('panadapter.waterfall_thresholds', {
            pink: -185,
            orange: -180,
            green: -160,
            blue: -145,
            royal: -130,
            black: -120
        });
    }
};

/**
 * VFO configuration utilities
 */
const K4VFOUtils = {
    getFreqMin() {
        return getConfigValue('vfo.freq_min', 1000000);
    },
    
    getFreqMax() {
        return getConfigValue('vfo.freq_max', 30000000);
    },
    
    /**
     * Constrain frequency to valid VFO range
     * @param {number} frequency - Frequency in Hz
     * @returns {number} Constrained frequency
     */
    constrainFrequency(frequency) {
        const min = this.getFreqMin();
        const max = this.getFreqMax();
        return Math.max(min, Math.min(max, frequency));
    }
};

/**
 * Mode mapping utilities using dynamic configuration
 * These functions provide safe access to K4 mode mappings
 */
const K4ModeUtils = {
    /**
     * Get CAT mode mapping from configuration
     * @returns {object} Mode code to name mapping
     */
    getCATModeMap() {
        return getConfigValue('modes.cat_mode_map', {
            '1': 'LSB',
            '2': 'USB', 
            '3': 'CW',
            '4': 'FM',
            '5': 'AM',
            '6': 'DATA',
            '7': 'CW-R',
            '9': 'DATA-R'
        });
    },
    
    /**
     * Convert mode code to display name
     * @param {string} modeCode - Numeric mode code from K4
     * @returns {string} Human-readable mode name
     */
    getModeDisplayName(modeCode) {
        const modeMap = this.getCATModeMap();
        return modeMap[modeCode] || `Mode ${modeCode}`;
    },
    
    /**
     * Get reverse mapping (mode name to code)
     * @returns {object} Mode name to code mapping
     */
    getReverseModeMap() {
        const modeMap = this.getCATModeMap();
        const reverseMap = {};
        for (const [code, name] of Object.entries(modeMap)) {
            reverseMap[name] = code;
        }
        return reverseMap;
    },
    
    /**
     * Get list of all supported mode names
     * @returns {string[]} Array of mode names
     */
    getSupportedModes() {
        const modeMap = this.getCATModeMap();
        return Object.values(modeMap);
    }
};

// Export utilities globally for easy access
window.K4VolumeUtils = K4VolumeUtils;
window.K4NetworkUtils = K4NetworkUtils;
window.K4PanadapterUtils = K4PanadapterUtils;
window.K4VFOUtils = K4VFOUtils;
window.K4ModeUtils = K4ModeUtils;
window.getConfigValue = getConfigValue;

// Auto-load configuration when this script loads
// This is safe and non-breaking because it only adds capabilities
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Small delay to ensure other scripts are loaded
        setTimeout(loadK4Configuration, 100);
    });
} else {
    // Document already loaded
    setTimeout(loadK4Configuration, 100);
}

console.log('📦 K4 Config Loader: Module loaded and ready');