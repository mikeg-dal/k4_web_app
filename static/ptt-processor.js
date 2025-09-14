/**
 * K4 PTT AudioWorklet Processor - SIMPLIFIED for Clean Audio
 * 
 * This AudioWorklet runs on the audio thread and provides precise timing
 * for K4 transmission audio. Streamlined to eliminate multiple processing stages.
 */

class PTTProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    
    // Audio accumulation buffer
    this.samples = [];
    
    this.targetSamples = 960; // default value, will be overridden by config from main thread
    
    // Audio processing parameters
    this.micGain = 0.1; // Start with low gain (10%) to match HTML default
    this.sampleCount = 0;
    this.packetsGenerated = 0;
    this.isTransmitting = false;
    this.lastPacketTime = 0;
    this.processCallCount = 0;
    
    // Listen for messages from main thread
    this.port.onmessage = (event) => {
      const { type, value, config } = event.data;

      if (type === 'setMicGain') {
        this.micGain = value;
        console.log(`🎤 AudioWorklet: Mic gain set to ${value}`);
      } else if (type === 'setConfig' && config && config.WORKLET_FRAME_SIZE) {
        this.targetSamples = config.WORKLET_FRAME_SIZE;
        console.log(`🔧 AudioWorklet: WORKLET_FRAME_SIZE updated to ${this.targetSamples}`);
      } else if (type === 'startTransmit') {
        this.isTransmitting = true;
        this.samples = []; // Clear any buffered samples when starting
        this.packetsGenerated = 0; // Reset packet counter
        console.log('🎤 AudioWorklet: Started transmitting');
      } else if (type === 'stopTransmit') {
        this.isTransmitting = false;
        this.samples = []; // Clear samples when stopping
        console.log(`🎤 AudioWorklet: Stopped transmitting (sent ${this.packetsGenerated} packets, process() called ${this.processCallCount} times)`);
        this.processCallCount = 0; // Reset for next session
      }
    };
    
    console.log('🎤 PTTProcessor initialized - targeting 960 samples (20ms) per packet');
  }
  
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    // Track process calls when transmitting
    if (this.isTransmitting) {
      this.processCallCount++;
    }
    
    // Only process if we're transmitting
    if (!this.isTransmitting) {
      return true; // Keep processor alive but don't send data
    }
    
    // Ensure we have input audio
    if (!input || input.length === 0) {
      console.log('⚠️ AudioWorklet: No input audio available');
      return true; // Keep processor alive
    }
    
    const inputChannel = input[0]; // Get first (mono) channel
    if (!inputChannel || inputChannel.length === 0) {
      console.log('⚠️ AudioWorklet: No input channel data');
      return true;
    }
    
    // Process input samples
    
    // SIMPLIFIED: Only apply gain from HTML slider - NO OTHER PROCESSING
    for (let i = 0; i < inputChannel.length; i++) {
      let sample = inputChannel[i];
      
      // Apply microphone gain from HTML slider ONLY
      sample *= this.micGain;
      
      this.samples.push(sample);
      this.sampleCount++;
    }
    
    while (this.samples.length >= this.targetSamples) {
      const packetSamples = this.samples.splice(0, this.targetSamples);
      const audioData = new Float32Array(packetSamples);
      
      const currentTime = Date.now();
      const timeSinceLastPacket = currentTime - this.lastPacketTime;
      
      this.port.postMessage({
        type: 'audioData',
        data: audioData.buffer,
        sampleCount: packetSamples.length,
        timestamp: currentTime,
        sampleRate: 48000,
        actualSamples: packetSamples.length,
        bufferSize: this.samples.length,
        timingGap: timeSinceLastPacket
      });
      
      this.packetsGenerated++;
      this.lastPacketTime = currentTime;
      
      console.log(`🎤 AudioWorklet packet ${this.packetsGenerated}: ${packetSamples.length} samples, gap: ${timeSinceLastPacket}ms`);
    }
    
    // Keep the processor running
    return true;
  }
  
  static get parameterDescriptors() {
    return [
      {
        name: 'micGain',
        defaultValue: 0.1, // 10% to match HTML default
        minValue: 0.0,
        maxValue: 1.0
      }
    ];
  }
}

// Register the processor
registerProcessor('ptt-processor', PTTProcessor);