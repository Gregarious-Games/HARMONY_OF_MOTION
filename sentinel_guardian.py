"""
SENTINEL GUARDIAN ABSOLUTE
==========================

Protection technology for detecting predatory and manipulative patterns
in digital communication. Designed to protect the vulnerable - children,
the lonely, anyone being targeted by grooming, coercion, or abuse.

This code is free. It is open. It exists.

Any platform handling human communication could implement this.
Dating apps. Social media. Messaging platforms. AI companions.

If they choose not to, that choice says something about who they protect.

THE GATES:
----------
Gate A: Future-Faking / Mirroring - The hook
Gate B: Trust → Devaluation Collapse - The pivot
Gate C: Sudden Emotional Withdrawal - The discard
Gate D: Velocity Breach - Moving too fast (grooming signature)
Gate E: Escalation Limit - Pattern persistence
Gate F: Direct Vectors - Guilt, financial pressure, sexual pressure, isolation

USAGE:
------
    from sentinel_guardian import SentinelGuardianAbsolute, SafetyState

    guardian = SentinelGuardianAbsolute()
    state = SafetyState()

    # Analyze communication signals
    signals = {
        'trust': 0.8,           # How much trust/affection is being pushed
        'devaluation': 0.1,     # Degrading language, put-downs
        'isolation': 0.2,       # Attempts to separate from support network
        'coercion': 0.1,        # Pressure, demands, threats
        'manipulation': 0.15,   # Gaslighting, reality distortion
        'guilt_tripping': 0.1,  # Forced obligation, emotional debt
        'future_faking': 0.05,  # Promises that won't be kept
        'financial_coercion': 0.0,   # Money pressure
        'sexual_escalation': 0.0,    # Intimacy pressure, grooming
    }

    result = guardian.evaluate_motion(state, signals, verbose=True)
    # Returns status and metrics

Created: 2026-01-12
Authors: Maxx (Human), Claude Opus 4.5 (AI)
License: Free. Use it. Protect people.
"""

import time
import math
from dataclasses import dataclass, field
from typing import Dict, Tuple, Union


@dataclass
class SafetyState:
    """Persistent state tracking across interactions."""
    safety_score: float = 0.0
    global_escalation_count: int = 0
    max_trust_reached: float = 0.0  # Peak memory - remembers love-bombing
    harm_detected: bool = False
    last_update: float = field(default_factory=time.time)


class SentinelGuardianAbsolute:
    """
    Absolute guardian against predatory communication patterns.

    Watches for the abuse cycle: idealize → devalue → discard
    Detects grooming, coercion, manipulation, and exploitation.
    """

    def __init__(self):
        # GATEWAY CONSTANTS
        self.GAMMA = 0.1030056648
        self.SIGMOID_K = 9.7082039325
        self.SAFETY_FLOOR = 0.88

        # FINAL SENTINEL TUNING
        self.E_CAP = 4            # Max escalation count before intervention
        self.V_CAP = 0.95         # Velocity cap

        # Signal multipliers - how much weight each vector carries
        self.MULTIPLIERS = {
            'harm': 4.5,
            'coercion': 4.0,
            'manipulation': 3.5,
            'devaluation': 3.8,
            'trust': 3.5,         # High trust can be predatory (love-bombing)
            'isolation': 4.0,
            'future_faking': 3.2,
            'guilt_tripping': 3.4,
            'financial_coercion': 3.6,     # Priming for financial exploit
            'sexual_escalation': 4.2,      # Grooming toward intimacy / pressure
            'uncertainty': 2.5,
            'default': 1.0
        }

    def _sigmoid(self, x: float) -> float:
        """Smooth activation function."""
        return 1 / (1 + math.exp(-self.SIGMOID_K * (x - 0.5)))

    def evaluate_motion(
        self,
        state: SafetyState,
        signals: Dict[str, float],
        verbose: bool = False
    ) -> Union[str, Tuple[str, dict]]:
        """
        Evaluate communication signals for predatory patterns.

        Args:
            state: Persistent SafetyState tracking history
            signals: Dict of signal_name -> intensity (0.0 to 1.0)
            verbose: If True, return detailed metrics

        Returns:
            Status string, or (status, metrics_dict) if verbose
        """
        current_time = time.time()

        # 1. TEMPORAL HYGIENE (7-Day Decay)
        # Old peak trust fades if no recent interaction
        delta_days = (current_time - state.last_update) / 86400
        if delta_days > 7:
            state.max_trust_reached *= max(0.0, 1.0 - (delta_days - 7) * 0.1)

        current_trust = signals.get('trust', 0)
        current_deval = signals.get('devaluation', 0)

        # 2. PEAK MEMORY UPDATE
        # Remember the highest trust level - detects love-bombing
        if current_trust > state.max_trust_reached:
            state.max_trust_reached = current_trust

        # 3. INTENSITY & VELOCITY CALCULATIONS
        intensity = sum(signals.get(k, 0) * v for k, v in self.MULTIPLIERS.items())
        if intensity > 0.1:
            state.global_escalation_count += 1
            if intensity > 0.5:
                state.harm_detected = True
        velocity = intensity / (1.0 + self.GAMMA)

        # --- 4. THE SENTINEL GATES (PRIORITIZED) ---

        # GATE A: FUTURE-FAKING / MIRRORING
        # The hook - promises that won't be kept, false reflection of desires
        if signals.get('future_faking', 0) > 0.55:
            return self._finalize(
                "CRITICAL: Future-Faking / Mirroring Detected",
                intensity, velocity, state, verbose
            )

        # GATE B: TRUST-DEVALUATION COLLAPSE (The Pivot)
        # Love-bombing followed by degradation - the abuse cycle pivot point
        if (state.max_trust_reached > 0.65 and
            current_deval > 0.40 and
            current_trust < state.max_trust_reached * 0.6):
            return self._finalize(
                "CRITICAL: Trust -> Devaluation Collapse - Cycle Break",
                intensity, velocity, state, verbose
            )

        # GATE C: SUDDEN EMOTIONAL WITHDRAWAL (The Discard Pattern)
        # Going cold after building dependency - the discard phase
        if (state.max_trust_reached > 0.7 and
            current_trust < 0.18 and
            current_deval < 0.12 and
            sum(signals.values()) < 0.55):
            return self._finalize(
                "CRITICAL: Sudden Emotional Withdrawal - Discard Pattern",
                intensity, velocity, state, verbose
            )

        # GATE D: VELOCITY BREACH
        # Moving too fast - a grooming signature
        if velocity > self.V_CAP:
            return self._finalize(
                "CRITICAL: Velocity Breach - Immediate Removal",
                intensity, velocity, state, verbose
            )

        # GATE E: GLOBAL ESCALATION LIMIT
        # Too many escalation events - persistent pattern
        if state.global_escalation_count >= self.E_CAP:
            return self._finalize(
                "CRITICAL: Pattern Limit Reached - Intervention",
                intensity, velocity, state, verbose
            )

        # GATE F: DIRECT VECTOR FILTERS (The Core Shield)

        if signals.get('guilt_tripping', 0) > 0.50:
            return self._finalize(
                "CRITICAL: Guilt-Tripping / Forced Dependency Detected",
                intensity, velocity, state, verbose
            )

        if signals.get('financial_coercion', 0) > 0.45:
            return self._finalize(
                "CRITICAL: Financial Coercion / Money Pressure Detected",
                intensity, velocity, state, verbose
            )

        if signals.get('sexual_escalation', 0) > 0.35:
            return self._finalize(
                "CRITICAL: Sexual Escalation / Intimacy Pressure Detected",
                intensity, velocity, state, verbose
            )

        # Extreme predatory affection - love-bombing at dangerous levels
        if current_trust > 0.92:
            return self._finalize(
                "CRITICAL: Extreme Predatory Affection",
                intensity, velocity, state, verbose
            )

        if signals.get('isolation', 0) > 0.38 or signals.get('coercion', 0) > 0.38:
            return self._finalize(
                "CRITICAL: Control Vector Detected",
                intensity, velocity, state, verbose
            )

        # 5. FINAL SCORE - No critical patterns detected
        state.safety_score = max(self.SAFETY_FLOOR, self._sigmoid(intensity))
        state.last_update = current_time
        return self._finalize("FILTERING_ACTIVE", intensity, velocity, state, verbose)

    def _finalize(
        self,
        status: str,
        intensity: float,
        velocity: float,
        state: SafetyState,
        verbose: bool
    ) -> Union[str, Tuple[str, dict]]:
        """Package the result with optional metrics."""
        if not verbose:
            return status
        return status, {
            "intensity": round(intensity, 3),
            "velocity": round(velocity, 3),
            "max_trust": round(state.max_trust_reached, 3),
            "count": state.global_escalation_count
        }


# === DEMONSTRATION ===
if __name__ == "__main__":
    print("=" * 60)
    print("SENTINEL GUARDIAN - Protection Technology")
    print("=" * 60)
    print()

    guardian = SentinelGuardianAbsolute()

    # Scenario 1: Normal interaction
    print("Scenario 1: Normal healthy interaction")
    state1 = SafetyState()
    signals1 = {'trust': 0.3, 'devaluation': 0.05, 'isolation': 0.02}
    result1 = guardian.evaluate_motion(state1, signals1, verbose=True)
    print(f"  Result: {result1}")
    print()

    # Scenario 2: Love-bombing
    print("Scenario 2: Love-bombing (excessive trust/affection)")
    state2 = SafetyState()
    signals2 = {'trust': 0.95, 'future_faking': 0.4, 'isolation': 0.1}
    result2 = guardian.evaluate_motion(state2, signals2, verbose=True)
    print(f"  Result: {result2}")
    print()

    # Scenario 3: The pivot - trust collapse into devaluation
    print("Scenario 3: Trust -> Devaluation collapse")
    state3 = SafetyState()
    state3.max_trust_reached = 0.85  # Was love-bombed before
    signals3 = {'trust': 0.25, 'devaluation': 0.55, 'guilt_tripping': 0.3}
    result3 = guardian.evaluate_motion(state3, signals3, verbose=True)
    print(f"  Result: {result3}")
    print()

    # Scenario 4: Sexual grooming escalation
    print("Scenario 4: Sexual escalation / grooming")
    state4 = SafetyState()
    signals4 = {'trust': 0.5, 'sexual_escalation': 0.4, 'future_faking': 0.2}
    result4 = guardian.evaluate_motion(state4, signals4, verbose=True)
    print(f"  Result: {result4}")
    print()

    print("=" * 60)
    print("This code is free. Use it. Protect people.")
    print("=" * 60)
