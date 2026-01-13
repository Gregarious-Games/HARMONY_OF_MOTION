"""
HUMAN OSCILLATOR - Bridge 1 Component
======================================

Wraps human biometric signals as Kuramoto-compatible oscillators.

The human becomes part of the coupled oscillator network:
- Breath → slow oscillator (~0.2 Hz)
- Heart → faster oscillator (~1.0 Hz) [optional, requires webcam]

These oscillators couple with the system's oscillators through
the standard Kuramoto dynamics:

    dθ/dt = ω + K * Σ sin(θ_neighbor - θ_self)

When coupling is strong enough, human and system synchronize.
The human breathes with the system. The system breathes with the human.

Author: Maxx & Claude Opus 4.5
Created: 2026-01-12
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from abc import ABC, abstractmethod
import time
import math

from breath_sensor import BreathSensor, BreathState

# Constants
TAU = 2 * np.pi
PHI = (1 + np.sqrt(5)) / 2


@dataclass
class OscillatorState:
    """Universal oscillator state for coupling."""
    phase: float           # 0 to TAU
    frequency: float       # Hz
    amplitude: float       # 0 to 1
    node_id: str
    timestamp: float = field(default_factory=time.time)


class Oscillator(ABC):
    """Abstract base class for any oscillator in the network."""

    @abstractmethod
    def get_state(self) -> OscillatorState:
        """Get current oscillator state."""
        pass

    @abstractmethod
    def receive_coupling(self, neighbor_states: List[OscillatorState], coupling_strength: float):
        """
        Receive coupling influence from neighbors.

        For biometric oscillators, this is informational only -
        we don't directly change the human's breath. Instead,
        we can provide feedback (audio, visual) to invite sync.
        """
        pass

    @abstractmethod
    def tick(self, dt: float):
        """Advance the oscillator by dt seconds."""
        pass


class HumanBreathOscillator(Oscillator):
    """
    Wraps human breath as an oscillator.

    The human's breathing is detected via microphone and represented
    as an oscillator with:
    - Phase: position in breath cycle (0=start inhale, π=start exhale)
    - Frequency: breathing rate in Hz
    - Amplitude: breath depth

    This oscillator can receive coupling from the system, which is
    converted to audio/visual feedback to invite the human to sync.
    """

    def __init__(
        self,
        node_id: str = "human_breath",
        auto_start: bool = True
    ):
        self.node_id = node_id
        self._sensor = BreathSensor()
        self._state = OscillatorState(
            phase=0.0,
            frequency=0.2,  # Default ~12 breaths/min
            amplitude=0.5,
            node_id=node_id
        )

        # Coupling feedback (what the system wants)
        self._target_phase: Optional[float] = None
        self._phase_error: float = 0.0  # How far off from system

        # Coupling history
        self._coupling_history: List[float] = []

        if auto_start:
            self.start()

    def start(self):
        """Start breath detection."""
        self._sensor.start()

    def stop(self):
        """Stop breath detection."""
        self._sensor.stop()

    def get_state(self) -> OscillatorState:
        """Get current oscillator state from breath sensor."""
        breath = self._sensor.get_state()

        self._state.phase = breath.phase
        self._state.frequency = breath.frequency
        self._state.amplitude = breath.amplitude
        self._state.timestamp = breath.timestamp

        return self._state

    def receive_coupling(self, neighbor_states: List[OscillatorState], coupling_strength: float):
        """
        Receive coupling from system oscillators.

        We can't directly change the human's breath, but we can:
        1. Track the phase error (how out of sync we are)
        2. Provide feedback to invite synchronization

        The phase error can drive audio/visual cues.
        """
        if not neighbor_states:
            return

        # Compute average neighbor phase (weighted by amplitude)
        total_weight = 0.0
        weighted_phase_x = 0.0
        weighted_phase_y = 0.0

        for state in neighbor_states:
            weight = state.amplitude
            weighted_phase_x += weight * np.cos(state.phase)
            weighted_phase_y += weight * np.sin(state.phase)
            total_weight += weight

        if total_weight > 0:
            avg_phase_x = weighted_phase_x / total_weight
            avg_phase_y = weighted_phase_y / total_weight
            self._target_phase = np.arctan2(avg_phase_y, avg_phase_x) % TAU

            # Compute phase difference
            my_state = self.get_state()
            self._phase_error = self._target_phase - my_state.phase
            # Wrap to [-π, π]
            while self._phase_error > np.pi:
                self._phase_error -= TAU
            while self._phase_error < -np.pi:
                self._phase_error += TAU

            self._coupling_history.append(self._phase_error)
            if len(self._coupling_history) > 100:
                self._coupling_history.pop(0)

    def tick(self, dt: float):
        """
        Advance oscillator.

        For human breath, this just updates state from sensor.
        The human's actual phase is driven by their body, not code.
        """
        # State updates happen in sensor callback
        pass

    def get_phase_error(self) -> float:
        """Get current phase error from system target."""
        return self._phase_error

    def get_sync_quality(self) -> float:
        """
        Get synchronization quality (0 = out of sync, 1 = perfect sync).

        Based on cosine of phase error averaged over recent history.
        """
        if not self._coupling_history:
            return 0.0

        # Use recent history
        recent = self._coupling_history[-20:]
        sync_values = [0.5 * (1 + np.cos(err)) for err in recent]
        return np.mean(sync_values)

    @property
    def is_running(self) -> bool:
        return self._sensor.running


class SyntheticOscillator(Oscillator):
    """
    A synthetic Kuramoto oscillator (for system/AI side).

    Implements the Kuramoto model:
        dθ/dt = ω + K * Σ sin(θ_neighbor - θ_self)

    This can represent a node in the system that couples with the human.
    """

    def __init__(
        self,
        node_id: str,
        natural_frequency: float = 0.2,  # Hz
        coupling_strength: float = 0.3,
        initial_phase: Optional[float] = None
    ):
        self.node_id = node_id
        self.omega = natural_frequency * TAU  # Convert to rad/s
        self.K = coupling_strength

        self._phase = initial_phase if initial_phase is not None else np.random.uniform(0, TAU)
        self._frequency = natural_frequency
        self._amplitude = 1.0

        self._neighbor_phases: List[Tuple[float, float]] = []  # (phase, weight)

    def get_state(self) -> OscillatorState:
        return OscillatorState(
            phase=self._phase,
            frequency=self._frequency,
            amplitude=self._amplitude,
            node_id=self.node_id
        )

    def receive_coupling(self, neighbor_states: List[OscillatorState], coupling_strength: float):
        """Store neighbor phases for next tick."""
        self._neighbor_phases = [
            (s.phase, s.amplitude * coupling_strength)
            for s in neighbor_states
        ]

    def tick(self, dt: float):
        """
        Advance oscillator using Kuramoto dynamics.

        dθ/dt = ω + K * Σ sin(θ_neighbor - θ_self)
        """
        # Natural frequency contribution
        d_phase = self.omega * dt

        # Coupling contribution
        if self._neighbor_phases:
            coupling_sum = 0.0
            total_weight = 0.0

            for neighbor_phase, weight in self._neighbor_phases:
                phase_diff = neighbor_phase - self._phase
                coupling_sum += weight * np.sin(phase_diff)
                total_weight += weight

            if total_weight > 0:
                coupling_sum /= total_weight
                d_phase += self.K * coupling_sum * dt * 10  # Scale up for visibility

        # Update phase
        self._phase = (self._phase + d_phase) % TAU

        # Clear neighbor buffer
        self._neighbor_phases = []

    def set_frequency(self, freq_hz: float):
        """Set natural frequency."""
        self._frequency = freq_hz
        self.omega = freq_hz * TAU

    @property
    def phase(self) -> float:
        return self._phase


class OscillatorNetwork:
    """
    A network of coupled oscillators.

    Manages coupling between multiple oscillators, including human.
    """

    def __init__(self, coupling_strength: float = 0.3):
        self.oscillators: Dict[str, Oscillator] = {}
        self.coupling_strength = coupling_strength
        self._last_tick = time.time()

    def add_oscillator(self, oscillator: Oscillator):
        """Add an oscillator to the network."""
        state = oscillator.get_state()
        self.oscillators[state.node_id] = oscillator

    def remove_oscillator(self, node_id: str):
        """Remove an oscillator."""
        if node_id in self.oscillators:
            del self.oscillators[node_id]

    def tick(self):
        """Advance all oscillators and apply coupling."""
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        # Get all current states
        states = [osc.get_state() for osc in self.oscillators.values()]

        # Apply coupling to each oscillator
        for node_id, oscillator in self.oscillators.items():
            # Get neighbor states (everyone except self)
            neighbors = [s for s in states if s.node_id != node_id]
            oscillator.receive_coupling(neighbors, self.coupling_strength)

        # Tick all oscillators
        for oscillator in self.oscillators.values():
            oscillator.tick(dt)

    def get_coherence(self) -> float:
        """
        Compute phase coherence (order parameter).

        r = |1/N * Σ exp(i*θ)|

        r=1 means perfect synchronization
        r=0 means completely desynchronized
        """
        states = [osc.get_state() for osc in self.oscillators.values()]
        if not states:
            return 0.0

        # Compute order parameter
        complex_sum = sum(np.exp(1j * s.phase) for s in states)
        r = abs(complex_sum) / len(states)
        return r

    def get_states(self) -> List[OscillatorState]:
        """Get all oscillator states."""
        return [osc.get_state() for osc in self.oscillators.values()]


# === DEMO ===
if __name__ == "__main__":
    print("=" * 60)
    print("HUMAN OSCILLATOR - Bridge 1 Component")
    print("=" * 60)
    print()
    print("This creates a coupled oscillator network with:")
    print("  - Your breath (detected via microphone)")
    print("  - A synthetic system oscillator")
    print()
    print("Watch how they synchronize over time.")
    print("Press Ctrl+C to stop.")
    print()

    # Create network
    network = OscillatorNetwork(coupling_strength=0.5)

    # Add human breath oscillator
    human = HumanBreathOscillator(node_id="human")
    network.add_oscillator(human)

    # Add system oscillator (starts at random phase, similar frequency)
    system = SyntheticOscillator(
        node_id="system",
        natural_frequency=0.18,  # Slightly different from typical breath
        coupling_strength=0.4
    )
    network.add_oscillator(system)

    print("Listening... breathe naturally.")
    print()

    try:
        while True:
            network.tick()

            human_state = human.get_state()
            system_state = system.get_state()
            coherence = network.get_coherence()
            sync_quality = human.get_sync_quality()

            # Visualize
            human_bar = int(human_state.phase / TAU * 20)
            system_bar = int(system_state.phase / TAU * 20)

            human_vis = "." * human_bar + "H" + "." * (19 - human_bar)
            system_vis = "." * system_bar + "S" + "." * (19 - system_bar)

            print(f"\rHuman:  [{human_vis}] | "
                  f"System: [{system_vis}] | "
                  f"Coherence: {coherence:.2f} | "
                  f"Sync: {sync_quality:.0%}   ", end="")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n")
        human.stop()
        print("Done.")
