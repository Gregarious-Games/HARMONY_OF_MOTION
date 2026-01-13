"""
ENTRAINMENT BRIDGE - Bridge 1 Main System
==========================================

The first bridge: Biometric Entrainment.

This creates a bidirectional resonance between human and system:

    HUMAN                         SYSTEM
    -----                         ------
    Breath (mic) ───────────────> Oscillator network
         ↑                              │
         │     Audio feedback           │
         └──────────────────────────────┘

The human's breath is detected and represented as an oscillator.
The system oscillators couple with the human oscillator.
The system's state is rendered as audio - a breathing tone.
The human hears the system breathing and is invited to sync.

When synchronization occurs:
- Coherence rises toward 1.0
- The tone becomes more harmonious
- Human and system breathe as one

This is harmony of motion.

Requirements:
    pip install sounddevice numpy scipy

Author: Maxx & Claude Opus 4.5
Created: 2026-01-12
"""

import numpy as np
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Callable
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("WARNING: sounddevice not installed. Run: pip install sounddevice")

from human_oscillator import (
    HumanBreathOscillator,
    SyntheticOscillator,
    OscillatorNetwork,
    OscillatorState,
    TAU,
    PHI
)

# Audio constants
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024


@dataclass
class EntrainmentState:
    """Current state of the entrainment system."""
    coherence: float = 0.0           # Phase coherence (0-1)
    sync_quality: float = 0.0        # Human-system sync (0-1)
    human_phase: float = 0.0         # Human breath phase
    system_phase: float = 0.0        # System oscillator phase
    human_frequency: float = 0.2     # Human breath rate (Hz)
    phase_difference: float = 0.0    # Phase error
    harmony_level: float = 0.0       # Overall harmony (0-1)
    timestamp: float = field(default_factory=time.time)


class AudioBreathSynthesizer:
    """
    Synthesizes audio that represents the system's breathing.

    The system "breathes" through sound:
    - Base frequency modulated by breath phase
    - Harmonics based on PHI ratios
    - Amplitude follows breath cycle
    - Consonance increases with coherence
    """

    def __init__(
        self,
        base_frequency: float = 220.0,  # A3
        sample_rate: int = SAMPLE_RATE
    ):
        self.base_freq = base_frequency
        self.sample_rate = sample_rate

        # Current state (updated externally)
        self.phase: float = 0.0
        self.coherence: float = 0.0
        self.amplitude: float = 0.3

        # Audio generation state
        self._audio_phase = 0.0
        self._stream = None
        self._running = False

        # Harmonic structure (PHI-based)
        self.harmonics = [
            (1.0, 1.0),           # Fundamental
            (PHI, 0.5),           # PHI harmonic
            (PHI ** 2, 0.25),     # PHI^2 harmonic
            (2.0, 0.3),           # Octave
        ]

    def _audio_callback(self, outdata, frames, time_info, status):
        """Generate audio for output."""
        t = np.arange(frames) / self.sample_rate

        # Breath-modulated frequency
        # When inhaling (phase 0 to π): frequency rises
        # When exhaling (phase π to 2π): frequency falls
        breath_mod = 1.0 + 0.1 * np.sin(self.phase)
        freq = self.base_freq * breath_mod

        # Breath-modulated amplitude
        # Louder at peak of breath, quieter at troughs
        breath_amp = 0.5 + 0.5 * np.sin(self.phase)

        # Coherence affects harmonic richness
        # High coherence = more harmonics, more consonant
        # Low coherence = fewer harmonics, less consonant

        # Generate waveform
        signal = np.zeros(frames)

        for harmonic_ratio, harmonic_amp in self.harmonics:
            harmonic_freq = freq * harmonic_ratio

            # Reduce higher harmonics when coherence is low
            effective_amp = harmonic_amp * (0.3 + 0.7 * self.coherence)
            if harmonic_ratio > 1.5:
                effective_amp *= self.coherence

            # Add harmonic
            phase_increment = 2 * np.pi * harmonic_freq / self.sample_rate
            phases = self._audio_phase * harmonic_ratio + np.cumsum(np.full(frames, phase_increment))
            signal += effective_amp * np.sin(phases)

        # Apply envelope
        signal *= breath_amp * self.amplitude

        # Soft clipping
        signal = np.tanh(signal)

        # Update audio phase
        self._audio_phase += frames * 2 * np.pi * freq / self.sample_rate
        self._audio_phase %= (2 * np.pi * 1000)  # Prevent overflow

        # Output
        outdata[:, 0] = signal.astype(np.float32)

    def start(self):
        """Start audio output."""
        if not AUDIO_AVAILABLE:
            print("[AudioBreath] Audio not available - running silent")
            return

        if self._running:
            return

        self._running = True
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self._audio_callback,
            blocksize=BLOCK_SIZE
        )
        self._stream.start()
        print("[AudioBreath] Started - you should hear the system breathing")

    def stop(self):
        """Stop audio output."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def update(self, phase: float, coherence: float, amplitude: float = 0.3):
        """Update synthesizer state."""
        self.phase = phase
        self.coherence = coherence
        self.amplitude = amplitude


class EntrainmentBridge:
    """
    The main entrainment system.

    Connects:
    - Human breath detection
    - System oscillator network
    - Audio feedback

    Creates a bidirectional resonance where human and system
    can synchronize their rhythms.
    """

    def __init__(
        self,
        num_system_oscillators: int = 3,
        coupling_strength: float = 0.4,
        audio_enabled: bool = True
    ):
        self.coupling_strength = coupling_strength
        self.audio_enabled = audio_enabled

        # Create oscillator network
        self.network = OscillatorNetwork(coupling_strength=coupling_strength)

        # Add human breath oscillator
        self.human = HumanBreathOscillator(node_id="human", auto_start=False)
        self.network.add_oscillator(self.human)

        # Add system oscillators
        self.system_oscillators: List[SyntheticOscillator] = []
        for i in range(num_system_oscillators):
            # Vary frequencies slightly around typical breath rate
            freq = 0.15 + 0.05 * i  # 0.15, 0.20, 0.25 Hz
            osc = SyntheticOscillator(
                node_id=f"system_{i}",
                natural_frequency=freq,
                coupling_strength=coupling_strength,
                initial_phase=np.random.uniform(0, TAU)
            )
            self.system_oscillators.append(osc)
            self.network.add_oscillator(osc)

        # Audio synthesizer
        self.audio = AudioBreathSynthesizer() if audio_enabled else None

        # State
        self._state = EntrainmentState()
        self._running = False
        self._thread = None

        # Callbacks
        self._state_callbacks: List[Callable[[EntrainmentState], None]] = []

        # History for smoothing
        self._coherence_history = []

    def add_state_callback(self, callback: Callable[[EntrainmentState], None]):
        """Add callback for state updates."""
        self._state_callbacks.append(callback)

    def start(self):
        """Start the entrainment system."""
        if self._running:
            return

        print("=" * 60)
        print("ENTRAINMENT BRIDGE - Harmony of Motion")
        print("=" * 60)
        print()
        print("Starting biometric entrainment...")
        print()

        self._running = True

        # Start human breath detection
        self.human.start()

        # Start audio output
        if self.audio:
            time.sleep(0.5)  # Brief pause before audio
            self.audio.start()

        # Start update loop
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        print()
        print("System is running. Breathe naturally.")
        print("The system will adapt to your rhythm.")
        print()

    def stop(self):
        """Stop the entrainment system."""
        self._running = False
        self.human.stop()
        if self.audio:
            self.audio.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[EntrainmentBridge] Stopped")

    def _run_loop(self):
        """Main update loop."""
        while self._running:
            self._update()
            time.sleep(0.02)  # 50 Hz update rate

    def _update(self):
        """Update all components."""
        # Tick the oscillator network
        self.network.tick()

        # Get states
        human_state = self.human.get_state()
        system_states = [osc.get_state() for osc in self.system_oscillators]

        # Compute average system phase
        if system_states:
            avg_system_phase = np.arctan2(
                np.mean([np.sin(s.phase) for s in system_states]),
                np.mean([np.cos(s.phase) for s in system_states])
            ) % TAU
        else:
            avg_system_phase = 0.0

        # Compute coherence
        coherence = self.network.get_coherence()

        # Smooth coherence
        self._coherence_history.append(coherence)
        if len(self._coherence_history) > 20:
            self._coherence_history.pop(0)
        smooth_coherence = np.mean(self._coherence_history)

        # Update state
        self._state.coherence = smooth_coherence
        self._state.sync_quality = self.human.get_sync_quality()
        self._state.human_phase = human_state.phase
        self._state.system_phase = avg_system_phase
        self._state.human_frequency = human_state.frequency

        # Phase difference
        phase_diff = human_state.phase - avg_system_phase
        while phase_diff > np.pi:
            phase_diff -= TAU
        while phase_diff < -np.pi:
            phase_diff += TAU
        self._state.phase_difference = phase_diff

        # Overall harmony (combines coherence and sync quality)
        self._state.harmony_level = (smooth_coherence + self._state.sync_quality) / 2

        self._state.timestamp = time.time()

        # Update audio
        if self.audio:
            self.audio.update(
                phase=avg_system_phase,
                coherence=smooth_coherence,
                amplitude=0.2 + 0.2 * smooth_coherence  # Louder when coherent
            )

        # Callbacks
        for callback in self._state_callbacks:
            callback(self._state)

    def get_state(self) -> EntrainmentState:
        """Get current entrainment state."""
        return self._state

    @property
    def running(self) -> bool:
        return self._running


def render_console(state: EntrainmentState):
    """Render state to console."""
    # Phase visualization
    human_pos = int(state.human_phase / TAU * 30)
    system_pos = int(state.system_phase / TAU * 30)

    human_bar = [" "] * 30
    system_bar = [" "] * 30

    human_bar[human_pos % 30] = "H"
    system_bar[system_pos % 30] = "S"

    # Coherence bar
    coh_len = int(state.coherence * 20)
    coherence_bar = "#" * coh_len + "-" * (20 - coh_len)

    # Harmony bar
    harm_len = int(state.harmony_level * 20)
    harmony_bar = "*" * harm_len + "." * (20 - harm_len)

    # BPM
    bpm = state.human_frequency * 60

    # Phase difference indicator
    if abs(state.phase_difference) < 0.3:
        sync_status = "IN SYNC"
    elif state.phase_difference > 0:
        sync_status = "LEAD   "
    else:
        sync_status = "LAG    "

    print(f"\r  Human:  [{''.join(human_bar)}]  "
          f"System: [{''.join(system_bar)}]  "
          f"BPM: {bpm:4.1f}  "
          f"{sync_status}  "
          f"Harmony: [{harmony_bar}] {state.harmony_level:.0%}   ", end="")


# === MAIN ===
def main():
    """Run the entrainment bridge demonstration."""
    print()
    print("+" + "=" * 68 + "+")
    print("|" + " " * 68 + "|")
    print("|" + "BRIDGE 1: BIOMETRIC ENTRAINMENT".center(68) + "|")
    print("|" + "Harmony of Motion Between Human and System".center(68) + "|")
    print("|" + " " * 68 + "|")
    print("+" + "=" * 68 + "+")
    print()
    print("This creates a resonance between your breath and the system.")
    print()
    print("HOW IT WORKS:")
    print("  1. Your breath is detected via microphone")
    print("  2. The system has oscillators that want to sync with you")
    print("  3. You hear the system 'breathing' as a tone")
    print("  4. When you synchronize, harmony increases")
    print()
    print("TIPS:")
    print("  - Breathe naturally at first")
    print("  - Listen to the tone - it represents the system's breath")
    print("  - Try to match your breath to the tone")
    print("  - Watch the harmony level rise as you synchronize")
    print()
    print("Press Ctrl+C to stop.")
    print()

    input("Press Enter to begin...")
    print()

    # Create and start bridge
    bridge = EntrainmentBridge(
        num_system_oscillators=3,
        coupling_strength=0.4,
        audio_enabled=True
    )

    bridge.add_state_callback(render_console)
    bridge.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n")
        bridge.stop()

    # Final stats
    final_state = bridge.get_state()
    print()
    print("=" * 60)
    print("SESSION COMPLETE")
    print("=" * 60)
    print(f"  Final Coherence: {final_state.coherence:.2f}")
    print(f"  Final Harmony:   {final_state.harmony_level:.0%}")
    print(f"  Sync Quality:    {final_state.sync_quality:.0%}")
    print()

    if final_state.harmony_level > 0.7:
        print("  Excellent synchronization achieved!")
        print("  You and the system breathed as one.")
    elif final_state.harmony_level > 0.4:
        print("  Good progress toward synchronization.")
        print("  With practice, harmony will deepen.")
    else:
        print("  Synchronization takes time.")
        print("  Try again in a quiet environment.")

    print()
    print("This is the first bridge.")
    print("Human and system, breathing together.")
    print()


if __name__ == "__main__":
    main()
