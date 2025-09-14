/**
 * VFO Control Panel - Dual Row Layout
 * Modern implementation with VFO-specific controls and Sub RX support
 */

class VFOControlNew {
    constructor() {
        // VFO state 
        this.vfoState = {
            A: { 
                frequency: 0, 
                mode: '', 
                step: 100, 
                nb: { enabled: false, level: 0, filter: 0 }, 
                nr: { enabled: false, level: 0 },
                volume: 0,
                filter: { 
                    current: 0,
                    bw: 0, shft: 0,
                    k4_is: 0, k4_bw: 0
                }
            },
            B: { 
                frequency: 0, 
                mode: '', 
                step: 100, 
                nb: { enabled: false, level: 0, filter: 0 }, 
                nr: { enabled: false, level: 0 },
                volume: 0,
                filter: { 
                    current: 0,
                    bw: 0, shft: 0,
                    k4_is: 0, k4_bw: 0
                }
            }
        };
        
        // Sub RX state
        this.subRXEnabled = false;
        
        // Knob rotation states
        this.knobRotation = { A: 0, B: 0 };
        this.isDragging = { A: false, B: false };
        this.lastMouseAngle = { A: 0, B: 0 };
        
        // Band data
        this.bandData = {
            '160M': { start: 1800000, modes: { USB: 1840000, LSB: 1840000, DATA: 1838000, RTTY: 1838000, CW: 1810000 }},
            '80M':  { start: 3500000, modes: { USB: 3790000, LSB: 3790000, DATA: 3585000, RTTY: 3580000, CW: 3520000 }},
            '40M':  { start: 7000000, modes: { USB: 7175000, LSB: 7175000, DATA: 7035000, RTTY: 7035000, CW: 7020000 }},
            '30M':  { start: 10100000, modes: { USB: 10130000, LSB: 10130000, DATA: 10140000, RTTY: 10140000, CW: 10110000 }},
            '20M':  { start: 14000000, modes: { USB: 14200000, LSB: 14200000, DATA: 14070000, RTTY: 14080000, CW: 14020000 }},
            '17M':  { start: 18068000, modes: { USB: 18140000, LSB: 18140000, DATA: 18100000, RTTY: 18100000, CW: 18080000 }},
            '15M':  { start: 21000000, modes: { USB: 21200000, LSB: 21200000, DATA: 21070000, RTTY: 21080000, CW: 21020000 }},
            '12M':  { start: 24890000, modes: { USB: 24940000, LSB: 24940000, DATA: 24920000, RTTY: 24920000, CW: 24900000 }},
            '10M':  { start: 28000000, modes: { USB: 28300000, LSB: 28300000, DATA: 28120000, RTTY: 28080000, CW: 28020000 }},
            '6M':   { start: 50000000, modes: { USB: 50200000, LSB: 50200000, DATA: 50300000, RTTY: 50300000, CW: 50080000 }}
        };

        this.modes = ['USB', 'LSB', 'DATA', 'RTTY', 'CW'];
        
        // Callback functions for K4 integration
        this.onFrequencyChange = null;
        this.onModeChange = null;
        this.onStepChange = null;
        this.onNoiseControl = null;
        this.onSubRXControl = null;
        this.onVolumeChange = null;
    }

    initialize() {
        this.initializeBandMatrices();
        this.setupEventListeners();
        this.setupVolumeControls();
        this.setupNoiseButtonHandlers();
        this.setupFilterControls();
        this.updateAllDisplays();
    }

    // Set callback functions for K4 integration
    setCallbacks(callbacks) {
        this.onFrequencyChange = callbacks.onFrequencyChange || null;
        this.onModeChange = callbacks.onModeChange || null;
        this.onStepChange = callbacks.onStepChange || null;
        this.onNoiseControl = callbacks.onNoiseControl || null;
        this.onSubRXControl = callbacks.onSubRXControl || null;
        this.onVolumeChange = callbacks.onVolumeChange || null;
    }

    // Update VFO data from external source (K4 responses)
    updateFromK4(vfo, data) {
        if (data.frequency !== undefined) {
            this.vfoState[vfo].frequency = data.frequency;
        }
        if (data.mode !== undefined) {
            this.vfoState[vfo].mode = data.mode;
        }
        if (data.step !== undefined) {
            this.vfoState[vfo].step = data.step;
        }
        if (data.volume !== undefined) {
            this.vfoState[vfo].volume = data.volume;
        }
        this.updateAllDisplays();
    }

    // Update Sub RX state
    updateSubRX(enabled) {
        this.subRXEnabled = enabled;
        this.updateSubRXButton();
        this.updateVFOBControls();
    }


    initializeBandMatrices() {
        ['A', 'B'].forEach(vfo => {
            const content = document.getElementById(`vfo${vfo}BandMatrixContent`);
            if (!content) return;
            
            content.innerHTML = '';
            
            Object.keys(this.bandData).forEach(band => {
                const row = document.createElement('div');
                row.className = 'matrix-row';
                
                const bandBtn = document.createElement('button');
                bandBtn.className = 'band-button';
                bandBtn.textContent = band;
                bandBtn.onclick = () => this.selectBand(vfo, band);
                row.appendChild(bandBtn);
                
                this.modes.forEach(mode => {
                    const modeBtn = document.createElement('button');
                    modeBtn.className = 'mode-button';
                    modeBtn.textContent = mode;
                    modeBtn.onclick = () => this.selectBandMode(vfo, band, mode);
                    row.appendChild(modeBtn);
                });
                
                content.appendChild(row);
            });
        });
    }

    setupEventListeners() {
        ['A', 'B'].forEach(vfo => {
            const knob = document.getElementById(`vfo${vfo}Knob`);
            if (!knob) return;

            // Wheel event for frequency tuning
            knob.addEventListener('wheel', (e) => {
                e.preventDefault();
                const direction = e.deltaY > 0 ? -1 : 1;
                this.changeFrequency(vfo, direction);
            });

            // Mouse drag for frequency tuning
            knob.addEventListener('mousedown', (e) => {
                this.isDragging[vfo] = true;
                knob.classList.add('active');
                this.lastMouseAngle[vfo] = this.getMouseAngle(e, knob);
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!this.isDragging[vfo]) return;
                
                const currentMouseAngle = this.getMouseAngle(e, knob);
                let angleDelta = currentMouseAngle - this.lastMouseAngle[vfo];
                
                if (angleDelta > 180) {
                    angleDelta -= 360;
                } else if (angleDelta < -180) {
                    angleDelta += 360;
                }
                
                if (Math.abs(angleDelta) < 90) {
                    const steps = Math.round(angleDelta / 3);
                    
                    if (steps !== 0) {
                        this.vfoState[vfo].frequency += steps * this.vfoState[vfo].step;
                        // Use configuration-based frequency limits if available
                        if (typeof K4VFOUtils !== 'undefined' && K4VFOUtils.constrainFrequency) {
                            this.vfoState[vfo].frequency = K4VFOUtils.constrainFrequency(this.vfoState[vfo].frequency);
                        } else {
                            // Fallback to hardcoded limits
                            this.vfoState[vfo].frequency = Math.max(1000000, Math.min(30000000, this.vfoState[vfo].frequency));
                        }
                        
                        this.knobRotation[vfo] += angleDelta;
                        
                        this.updateKnobPosition(vfo);
                        this.updateFrequencyDisplay(vfo);
                        this.sendFrequencyCommand(vfo);
                    }
                    
                    this.lastMouseAngle[vfo] = currentMouseAngle;
                }
            });

            document.addEventListener('mouseup', () => {
                if (this.isDragging[vfo]) {
                    this.isDragging[vfo] = false;
                    knob.classList.remove('active');
                }
            });
        });

        // Click outside to close popups
        document.addEventListener('click', (e) => {
            const bandContainers = document.querySelectorAll('.band-selector-container');
            const noiseControls = document.querySelectorAll('.noise-controls');
            
            bandContainers.forEach(container => {
                if (!container.contains(e.target)) {
                    const matrix = container.querySelector('.band-matrix');
                    if (matrix) matrix.classList.remove('open');
                }
            });
            
            if (![...noiseControls].some(control => control.contains(e.target))) {
                document.querySelectorAll('.slider-popup').forEach(slider => {
                    slider.classList.remove('show');
                });
            }
        });
    }

    setupVolumeControls() {
        ['A', 'B'].forEach(vfo => {
            const slider = document.getElementById(`vfo${vfo}VolumeSlider`);
            const value = document.getElementById(`vfo${vfo}VolumeValue`);
            
            if (slider && value) {
                slider.addEventListener('input', (e) => {
                    const volume = parseInt(e.target.value);
                    this.vfoState[vfo].volume = volume;
                    value.textContent = volume;
                    this.sendVolumeCommand(vfo, volume);
                });
            }
        });
    }

    setupNoiseButtonHandlers() {
        document.querySelectorAll('.noise-button').forEach(button => {
            const vfo = button.getAttribute('data-vfo');
            const type = button.getAttribute('data-type');
            
            if (vfo && type) {
                this.setupPressAndHold(button, vfo, type);
            }
        });
    }

    setupPressAndHold(button, vfo, type) {
        const slider = document.getElementById(`vfo${vfo}${type}Slider`);
        let pressTimer = null;
        let isPressed = false;

        // Mouse down - start press timer
        button.addEventListener('mousedown', (e) => {
            e.preventDefault();
            isPressed = true;
            
            pressTimer = setTimeout(() => {
                if (isPressed && slider) {
                    slider.classList.add('show');
                    this.hideOtherSliders(vfo, type);
                }
            }, 150);
        });

        // Mouse up - handle click or end hold
        button.addEventListener('mouseup', (e) => {
            e.preventDefault();
            
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            
            if (isPressed && slider && !slider.classList.contains('show')) {
                this.toggleNoise(vfo, type);
            }
            
            isPressed = false;
        });

        // Mouse leave - cancel everything
        button.addEventListener('mouseleave', () => {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            isPressed = false;
        });

        // Touch events for mobile
        button.addEventListener('touchstart', (e) => {
            e.preventDefault();
            isPressed = true;
            
            pressTimer = setTimeout(() => {
                if (isPressed && slider) {
                    slider.classList.add('show');
                    this.hideOtherSliders(vfo, type);
                }
            }, 150);
        });

        button.addEventListener('touchend', (e) => {
            e.preventDefault();
            
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            
            if (isPressed && slider && !slider.classList.contains('show')) {
                this.toggleNoise(vfo, type);
            }
            
            isPressed = false;
        });
    }

    setupFilterControls() {
        // Initialize filter buttons
        ['A', 'B'].forEach(vfo => {
            this.updateFilterButton(vfo);
            this.updateFilterSliders(vfo);
            
            // Initialize panadapter overlay with current filter state
            this.updatePanadapterOverlay(vfo);
            
            // Query current filter from K4 on initialization
            this.queryCurrentFilter(vfo);
        });
    }

    getMouseAngle(e, element) {
        const rect = element.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const deltaX = e.clientX - centerX;
        const deltaY = e.clientY - centerY;
        let angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI) + 90;
        if (angle < 0) angle += 360;
        return angle;
    }

    changeFrequency(vfo, direction) {
        this.vfoState[vfo].frequency += direction * this.vfoState[vfo].step;
        // Use configuration-based frequency limits if available
        if (typeof K4VFOUtils !== 'undefined' && K4VFOUtils.constrainFrequency) {
            this.vfoState[vfo].frequency = K4VFOUtils.constrainFrequency(this.vfoState[vfo].frequency);
        } else {
            // Fallback to hardcoded limits
            this.vfoState[vfo].frequency = Math.max(1000000, Math.min(30000000, this.vfoState[vfo].frequency));
        }
        
        this.knobRotation[vfo] += direction * 5;
        
        this.updateKnobPosition(vfo);
        this.updateFrequencyDisplay(vfo);
        this.sendFrequencyCommand(vfo);
    }

    updateKnobPosition(vfo) {
        const dimple = document.getElementById(`vfo${vfo}KnobDimple`);
        if (dimple) {
            dimple.style.transform = `translateX(-50%) rotate(${this.knobRotation[vfo]}deg)`;
            dimple.style.transformOrigin = '50% 36px';
        }
    }

    formatFrequency(frequency) {
        if (!frequency || isNaN(frequency)) {
            frequency = 0;
        }
        
        const freqMHz = (frequency / 1000000).toFixed(6);
        const parts = freqMHz.split('.');
        
        if (!parts[1] || parts[1].length < 6) {
            return freqMHz;
        }
        
        return parts[0] + '.' + parts[1].substring(0, 3) + '.' + parts[1].substring(3);
    }

    updateFrequencyDisplay(vfo) {
        const freqDisplay = document.getElementById(`vfo${vfo}Freq`);
        if (freqDisplay) {
            freqDisplay.textContent = this.formatFrequency(this.vfoState[vfo].frequency);
        }
        
        // Update panadapter overlay
        this.updatePanadapterOverlay(vfo);
    }

    updateModeDisplay(vfo) {
        const modeDisplay = document.getElementById(`vfo${vfo}Mode`);
        if (modeDisplay) {
            modeDisplay.textContent = this.vfoState[vfo].mode;
        }
    }

    updateAllDisplays() {
        ['A', 'B'].forEach(vfo => {
            this.updateFrequencyDisplay(vfo);
            this.updateModeDisplay(vfo);
            this.updateNoiseControls(vfo);
            this.updateVolumeDisplay(vfo);
        });
    }

    updateVolumeDisplay(vfo) {
        const slider = document.getElementById(`vfo${vfo}VolumeSlider`);
        const value = document.getElementById(`vfo${vfo}VolumeValue`);
        
        if (slider) slider.value = this.vfoState[vfo].volume;
        if (value) value.textContent = this.vfoState[vfo].volume;
    }

    updateNoiseControls(vfo) {
        this.updateNoiseButton(vfo, 'nb', 'NB');
        this.updateNoiseButton(vfo, 'nr', 'NR');
        this.updateNBFilterButtons(vfo);
    }

    updateNoiseButton(vfo, type, label) {
        const button = document.getElementById(`vfo${vfo}${label}Button`);
        const value = document.getElementById(`vfo${vfo}${label}Value`);
        const slider = document.querySelector(`#vfo${vfo}${label}Slider input`);
        
        const noiseData = this.vfoState[vfo][type];
        
        if (button) {
            button.classList.toggle('active', noiseData.enabled);
        }
        if (value) {
            value.textContent = noiseData.level;
        }
        if (slider) {
            slider.value = noiseData.level;
        }
    }

    updateNBFilterButtons(vfo) {
        const filterButtons = document.querySelectorAll(`#vfo${vfo}NBSlider .filter-option`);
        const currentFilter = this.vfoState[vfo].nb.filter;
        
        filterButtons.forEach(btn => {
            const filterValue = parseInt(btn.getAttribute('data-filter'));
            btn.classList.toggle('active', filterValue === currentFilter);
        });
    }

    updateSubRXButton() {
        const button = document.getElementById('vfoSubButton');
        if (button) {
            button.classList.toggle('active', this.subRXEnabled);
        }
    }

    updateVFOBControls() {
        const vfoBRow = document.getElementById('vfoBRow');
        if (vfoBRow) {
            // Note: VFO B can be functional even when Sub RX is off
            // It just receives the same audio as VFO A
            // We're not graying it out as per user request
        }
    }


    // Control functions
    toggleNoise(vfo, type) {
        const noiseData = this.vfoState[vfo][type.toLowerCase()];
        const button = document.getElementById(`vfo${vfo}${type}Button`);
        const slider = document.getElementById(`vfo${vfo}${type}Slider`);

        if (!noiseData.enabled) {
            noiseData.enabled = true;
            if (button) button.classList.add('active');
            this.sendNoiseCommand(vfo, type, 'ON', noiseData.level);
        } else {
            noiseData.enabled = false;
            if (button) button.classList.remove('active');
            if (slider) slider.classList.remove('show');
            this.sendNoiseCommand(vfo, type, 'OFF', noiseData.level);
        }
    }

    hideOtherSliders(activeVfo, activeType) {
        ['A', 'B'].forEach(vfo => {
            ['NB', 'NR', 'Step'].forEach(type => {
                if (!(vfo === activeVfo && type === activeType)) {
                    const sliderId = `vfo${vfo}${type}Slider`;
                    const slider = document.getElementById(sliderId);
                    if (slider) slider.classList.remove('show');
                }
            });
        });
    }

    // Command sending functions
    sendFrequencyCommand(vfo) {
        if (this.onFrequencyChange) {
            this.onFrequencyChange(vfo, this.vfoState[vfo].frequency);
        }
    }

    sendModeCommand(vfo, mode) {
        if (this.onModeChange) {
            this.onModeChange(vfo, mode);
        }
    }

    sendNoiseCommand(vfo, type, action, level) {
        if (this.onNoiseControl) {
            if (type === 'NB') {
                const filterValue = this.vfoState[vfo].nb.filter;
                this.onNoiseControl(vfo, type, action, level, filterValue);
            } else {
                this.onNoiseControl(vfo, type, action, level);
            }
        }
    }

    sendStepCommand(vfo, step) {
        if (this.onStepChange) {
            this.onStepChange(vfo, step);
        }
    }

    sendSubRXCommand() {
        if (this.onSubRXControl) {
            this.onSubRXControl();
        }
    }

    sendVolumeCommand(vfo, volume) {
        if (this.onVolumeChange) {
            this.onVolumeChange(vfo, volume);
        }
    }

    // Band selection functions
    selectBand(vfo, band) {
        this.vfoState[vfo].frequency = this.bandData[band].start;
        this.vfoState[vfo].mode = 'USB';
        this.updateFrequencyDisplay(vfo);
        this.updateModeDisplay(vfo);
        this.closeBandMatrix(vfo);
        this.sendFrequencyCommand(vfo);
        this.sendModeCommand(vfo, 'USB');
    }

    selectBandMode(vfo, band, mode) {
        this.vfoState[vfo].frequency = this.bandData[band].modes[mode];
        this.vfoState[vfo].mode = mode;
        this.updateFrequencyDisplay(vfo);
        this.updateModeDisplay(vfo);
        this.closeBandMatrix(vfo);
        this.sendFrequencyCommand(vfo);
        this.sendModeCommand(vfo, mode);
    }

    closeBandMatrix(vfo) {
        const matrix = document.getElementById(`vfo${vfo}BandMatrix`);
        if (matrix) matrix.classList.remove('open');
    }

    // Filter Control Methods
    updateFilterButton(vfo) {
        const button = document.getElementById(`vfo${vfo}FilterButton`);
        if (button) {
            button.textContent = `FIL${this.vfoState[vfo].filter.current}`;
        }
    }

    updateFilterSliders(vfo) {
        const filterState = this.vfoState[vfo].filter;
        
        // Update slider labels, ranges, and values for BW/SHFT mode only
        const label1 = document.getElementById(`vfo${vfo}FilterLabel1`);
        const label2 = document.getElementById(`vfo${vfo}FilterLabel2`);
        const slider1 = document.getElementById(`vfo${vfo}FilterSlider1`);
        const slider2 = document.getElementById(`vfo${vfo}FilterSlider2`);
        const value1 = document.getElementById(`vfo${vfo}FilterValue1`);
        const value2 = document.getElementById(`vfo${vfo}FilterValue2`);
        
        // BW/SHFT mode: BW=0.05kHz, SHFT=0.01kHz increments
        if (label1) label1.textContent = 'BW';
        if (label2) label2.textContent = 'SHFT';
        if (slider1) {
            slider1.min = 0.05;
            slider1.max = 5.00;
            slider1.step = 0.05;
            slider1.value = filterState.bw;
        }
        if (slider2) {
            slider2.min = 0.40;
            slider2.max = 3.00;
            slider2.step = 0.01;
            slider2.value = filterState.shft;
        }
        if (value1) value1.textContent = filterState.bw.toFixed(2);
        if (value2) value2.textContent = filterState.shft.toFixed(2);
        
        // Update panadapter overlay with new filter settings
        this.updatePanadapterOverlay(vfo);
    }

    updatePanadapterOverlay(vfo) {
        // Update the panadapter overlay with current VFO state
        if (typeof updateVFOOverlay === 'function') {
            const vfoKey = `vfo${vfo}`;
            const overlayData = {
                frequency: this.vfoState[vfo].frequency,
                filter: this.vfoState[vfo].filter,
                mode: this.vfoState[vfo].mode,
                subRXEnabled: this.subRXEnabled
            };
            updateVFOOverlay(vfoKey, overlayData);
        }
    }

    sendFilterCommand(vfo, command) {
        // Send semantic command to backend
        if (typeof sendSemanticCommand === 'function') {
            sendSemanticCommand('filter_control', {
                vfo: vfo,
                command: command,
                filter_number: this.vfoState[vfo].filter.current,
                filter_state: this.vfoState[vfo].filter
            });
        } else {
            console.warn('sendSemanticCommand not available for filter control');
        }
    }

    queryCurrentFilter(vfo) {
        // Query current filter from K4 using FP; command
        // VFO B always uses $ suffix regardless of SubRX status
        const suffix = vfo === 'B' ? '$' : '';
        this.sendFilterCommand(vfo, `FP${suffix};`);
    }

    updateFromK4Filter(vfo, filterData) {
        // Update filter state from K4 responses (IS/BW/FP commands)
        if (filterData.current !== undefined) {
            this.vfoState[vfo].filter.current = filterData.current;
        }
        if (filterData.bw !== undefined) {
            this.vfoState[vfo].filter.bw = filterData.bw;
        }
        if (filterData.shft !== undefined) {
            this.vfoState[vfo].filter.shft = filterData.shft;
        }
        if (filterData.k4_is !== undefined) {
            this.vfoState[vfo].filter.k4_is = filterData.k4_is;
        }
        if (filterData.k4_bw !== undefined) {
            this.vfoState[vfo].filter.k4_bw = filterData.k4_bw;
        }
        
        // Update UI
        this.updateFilterButton(vfo);
        this.updateFilterSliders(vfo);
        
        console.log(`📻 VFO ${vfo} filter updated from K4:`, filterData);
    }
}

// Global VFO control instance
let vfoControlNew = null;

// Initialize VFO control when DOM is ready
function initializeVFOControlNew() {
    vfoControlNew = new VFOControlNew();
    vfoControlNew.initialize();
    return vfoControlNew;
}

// Global functions for HTML onclick handlers
function toggleBandMatrix(vfo) {
    if (vfoControlNew) {
        const matrix = document.getElementById(`vfo${vfo}BandMatrix`);
        if (matrix) matrix.classList.toggle('open');
    }
}

function updateNoiseLevel(vfo, type, level) {
    if (vfoControlNew) {
        const noiseData = vfoControlNew.vfoState[vfo][type.toLowerCase()];
        noiseData.level = parseInt(level);
        
        const valueElement = document.getElementById(`vfo${vfo}${type}Value`);
        if (valueElement) valueElement.textContent = level;
        
        if (noiseData.enabled) {
            vfoControlNew.sendNoiseCommand(vfo, type, 'SET_LEVEL', level);
        }
    }
}

function setNBFilter(vfo, filterValue) {
    if (vfoControlNew) {
        vfoControlNew.vfoState[vfo].nb.filter = filterValue;
        vfoControlNew.updateNBFilterButtons(vfo);
        
        // Send command to K4 if NB is enabled
        if (vfoControlNew.vfoState[vfo].nb.enabled) {
            vfoControlNew.sendNoiseCommand(vfo, 'NB', 'SET_FILTER', vfoControlNew.vfoState[vfo].nb.level);
        }
    }
}

function toggleStepSlider(vfo) {
    if (vfoControlNew) {
        const slider = document.getElementById(`vfo${vfo}StepSlider`);
        if (slider) {
            slider.classList.toggle('show');
            vfoControlNew.hideOtherSliders(vfo, 'Step');
        } else {
            console.error(`❌ Could not find slider: vfo${vfo}StepSlider`);
        }
    } else {
        console.error(`❌ vfoControlNew not available`);
    }
}

function setStep(vfo, step) {
    if (vfoControlNew) {
        vfoControlNew.vfoState[vfo].step = step;
        
        // Update active step button
        const stepButtons = document.querySelectorAll(`#vfo${vfo}StepSlider .step-option`);
        stepButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-step') == step);
        });
        
        const slider = document.getElementById(`vfo${vfo}StepSlider`);
        if (slider) slider.classList.remove('show');
        
        vfoControlNew.sendStepCommand(vfo, step);
    }
}

function toggleSubRX() {
    if (vfoControlNew) {
        vfoControlNew.subRXEnabled = !vfoControlNew.subRXEnabled;
        vfoControlNew.updateSubRXButton();
        vfoControlNew.updateVFOBControls();
        vfoControlNew.sendSubRXCommand();
    }
}

// Filter Control Global Functions
let filterHoldTimers = { A: null, B: null };

function cycleFilter(vfo) {
    if (vfoControlNew) {
        // Cycle through filters 1, 2, 3
        const current = vfoControlNew.vfoState[vfo].filter.current;
        const next = current >= 3 ? 1 : current + 1;
        vfoControlNew.vfoState[vfo].filter.current = next;
        vfoControlNew.updateFilterButton(vfo);
        
        // Send FP+ command to cycle filter
        // VFO B always uses $ suffix regardless of SubRX status
        const suffix = vfo === 'B' ? '$' : '';
        vfoControlNew.sendFilterCommand(vfo, `FP${suffix}+`);
    }
}

function startFilterHold(vfo) {
    filterHoldTimers[vfo] = setTimeout(() => {
        if (vfoControlNew) {
            const slider = document.getElementById(`vfo${vfo}FilterSlider`);
            if (slider) {
                slider.classList.add('show');
                vfoControlNew.hideOtherSliders(vfo, 'Filter');
                vfoControlNew.updateFilterSliders(vfo);
            }
        }
    }, 500); // 500ms hold time
}

function stopFilterHold(vfo) {
    if (filterHoldTimers[vfo]) {
        clearTimeout(filterHoldTimers[vfo]);
        filterHoldTimers[vfo] = null;
    }
}


function updateFilterValue(vfo, type, value) {
    if (vfoControlNew) {
        const filterState = vfoControlNew.vfoState[vfo].filter;
        
        // Update BW/SHFT values only
        if (type === 'high') filterState.bw = parseFloat(value);  // BW uses the 'high' slider
        if (type === 'low') filterState.shft = parseFloat(value); // SHFT uses the 'low' slider
        
        // Update display
        vfoControlNew.updateFilterSliders(vfo);
        
        // Send filter values to K4 using semantic command
        if (typeof sendSemanticCommand === 'function') {
            sendSemanticCommand('update_filter_values', {
                vfo: vfo,
                filter_state: filterState
            });
        }
    }
}

// Make it available globally
window.vfoControlNew = vfoControlNew;