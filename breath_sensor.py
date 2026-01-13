"""
BREATH SENSOR - Bridge 1 Component
===================================

Detects human breathing patterns from microphone input.

The breath is extracted from the amplitude envelope of the audio signal.
Breathing creates a slow oscillation (0.1-0.4 Hz, or 6-24 breaths/min)
in the overall sound level as the human inhales and exhales.

This module:
1. Captures audio from the microphone
2. Computes the amplitude envelope
3. Extracts the breathing frequency and phase
4. Outputs a continuous breath signal for entrainment

Requirements:
    pip install sounddevice numpy scipy

Author: Maxx & Claude Opus 4.5
Created: 2026-01-12
"""

import numpy as np
from scipy import signal
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Callable, Tuple
import threading
import time

# Try to import sounddevice, provide helpful error if missing
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("WARNING: sounddevice not installed. Run: pip install sounddevice")


@dataclass
class BreathState:
    """Current state of detected breath."""
    phase: float = 0.0           # 0 to 2π (0 = start of inhale, π = start of exhale)
    frequency: float = 0.2       # Hz (breaths per second)
    amplitude: float = 0.0       # Breath depth (0-1)
    inhaling: bool = True        # Currently inhaling?
    confidence: float = 0.0      # Detection confidence (0-1)
    raw_level: float = 0.0       # Raw audio level
    timestamp: float = field(default_factory=time.time)


class BreathSensor:
    """
    Detects breathing patterns from microphone input.

    Uses amplitude envelope analysis to extract the slow oscillation
    caused by breathing. Works best in a quiet environment where
    the dominant sound is the breath itself.
    """

    # Breathing frequency range (Hz)
    MIN_BREATH_FREQ = 0.08   # ~5 breaths/min (very slow)
    MAX_BREATH_FREQ = 0.5    # ~30 breaths/min (very fast)

    def __init__(
        self,
        sample_rate: int = 16000,
        buffer_seconds: float = 10.0,
        callback: Optional[Callable[[BreathState], None]] = None
    ):
        """
        Initialize breath sensor.

        Args:
            sample_rate: Audio sample rate in Hz
            buffer_seconds: How much audio history to keep for analysis
            callback: Optional function called with each breath state update
        """
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")

        self.sample_rate = sample_rate
        self.buffer_seconds = buffer_seconds
        self.callback = callback

        # Audio buffer
        buffer_size = int(sample_rate * buffer_seconds)
        self._audio_buffer = deque(maxlen=buffer_size)

        # Envelope buffer (downsampled)
        self._envelope_rate = 20  # Hz - enough to capture breath
        self._envelope_buffer = deque(maxlen=int(buffer_seconds * self._envelope_rate))

        # State
        self._state = BreathState()
        self._running = False
        self._stream = None
        self._thread = None

        # Analysis parameters
        self._envelope_samples_per_update = int(sample_rate / self._envelope_rate)
        self._current_envelope_samples = []

        # Peak detection state
        self._last_peak_time = time.time()
        self._last_trough_time = time.time()
        self._breath_periods = deque(maxlen=5)  # Recent breath periods for averaging

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            pass  # Ignore status messages for now

        # Get mono audio
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()

        # Compute RMS amplitude for this block
        rms = np.sqrt(np.mean(audio ** 2))

        # Add to envelope sampling
        self._current_envelope_samples.append(rms)

        # When we have enough samples, compute envelope point
        if len(self._current_envelope_samples) >= self._envelope_samples_per_update:
            envelope_value = np.mean(self._current_envelope_samples)
            self._envelope_buffer.append(envelope_value)
            self._current_envelope_samples = []

            # Update state
            self._update_breath_state(envelope_value)

    def _update_breath_state(self, current_level: float):
        """Update breath state based on envelope."""
        self._state.raw_level = current_level
        self._state.timestamp = time.time()

        if len(self._envelope_buffer) < self._envelope_rate * 3:
            # Need at least 3 seconds of data
            self._state.confidence = 0.0
            return

        # Convert buffer to array
        envelope = np.array(self._envelope_buffer)

        # Normalize
        env_min = np.min(envelope)
        env_max = np.max(envelope)
        env_range = env_max - env_min

        if env_range < 0.001:
            # No variation - no breath detected
            self._state.confidence = 0.0
            return

        envelope_norm = (envelope - env_min) / env_range
        current_norm = (current_level - env_min) / env_range

        # Estimate frequency using zero-crossings of derivative
        envelope_smooth = signal.savgol_filter(envelope_norm, min(15, len(envelope_norm) // 2 * 2 + 1), 3)
        derivative = np.diff(envelope_smooth)

        # Find zero crossings (sign changes in derivative = peaks/troughs)
        zero_crossings = np.where(np.diff(np.sign(derivative)))[0]

        if len(zero_crossings) >= 2:
            # Estimate period from zero crossings
            crossing_intervals = np.diff(zero_crossings) / self._envelope_rate
            # Full breath = 2 half-cycles (inhale + exhale)
            breath_period = np.mean(crossing_intervals) * 2

            if 1/self.MAX_BREATH_FREQ < breath_period < 1/self.MIN_BREATH_FREQ:
                self._state.frequency = 1.0 / breath_period
                self._state.confidence = min(1.0, len(zero_crossings) / 6)
            else:
                self._state.confidence *= 0.9

        # Estimate phase from current position in cycle
        # Use recent derivative to determine if inhaling or exhaling
        recent_derivative = derivative[-5:] if len(derivative) >= 5 else derivative
        avg_derivative = np.mean(recent_derivative)

        self._state.inhaling = avg_derivative > 0

        # Map current normalized level to phase
        # 0 = trough (start of inhale), π = peak (start of exhale)
        if self._state.inhaling:
            # Inhaling: phase goes from 0 to π
            self._state.phase = current_norm * np.pi
        else:
            # Exhaling: phase goes from π to 2π
            self._state.phase = np.pi + (1 - current_norm) * np.pi

        # Amplitude is the range of the envelope
        self._state.amplitude = min(1.0, env_range * 10)  # Scale up small mic signals

        # Call callback if set
        if self.callback:
            self.callback(self._state)

    def start(self):
        """Start capturing and analyzing breath."""
        if self._running:
            return

        self._running = True

        # Start audio stream
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.05)  # 50ms blocks
        )
        self._stream.start()

        print(f"[BreathSensor] Started - listening on default microphone")
        print(f"[BreathSensor] Breathe naturally. Detection will improve over ~5 seconds.")

    def stop(self):
        """Stop capturing."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[BreathSensor] Stopped")

    def get_state(self) -> BreathState:
        """Get current breath state."""
        return self._state

    def get_phase(self) -> float:
        """Get current breath phase (0 to 2π)."""
        return self._state.phase

    def get_frequency(self) -> float:
        """Get detected breath frequency in Hz."""
        return self._state.frequency

    def is_inhaling(self) -> bool:
        """Check if currently inhaling."""
        return self._state.inhaling

    @property
    def running(self) -> bool:
        return self._running


# === DEMO ===
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("BREATH SENSOR - Bridge 1 Component")
    print("=" * 60)
    print()
    print("This will detect your breathing pattern from the microphone.")
    print("Breathe naturally. The sensor needs ~5 seconds to calibrate.")
    print()
    print("Press Ctrl+C to stop.")
    print()

    def on_breath(state: BreathState):
        """Callback for breath updates."""
        phase_deg = state.phase * 180 / np.pi
        direction = "INHALE " if state.inhaling else "EXHALE"
        bar_len = int(state.amplitude * 30)
        bar = "#" * bar_len + "-" * (30 - bar_len)

        bpm = state.frequency * 60

        print(f"\r{direction} | Phase: {phase_deg:5.1f}° | "
              f"BPM: {bpm:4.1f} | "
              f"[{bar}] | "
              f"Conf: {state.confidence:.0%}   ", end="")

    sensor = BreathSensor(callback=on_breath)

    try:
        sensor.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n")
        sensor.stop()
        print("Done.")
