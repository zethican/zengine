"""
ZEngine — engine/narrative.py
NarrativeGenerator: Translates Chronicle entries into human-readable prose.
"""

from typing import Dict, Any, List
from engine.combat import (
    EVT_ACTION_RESOLVED,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH,
    EVT_SOCIAL_STRESS_SPIKE,
    EVT_SOCIAL_DISPOSITION_SHIFT,
    EVT_SOCIAL_RUMOR_SHARED
)

class NarrativeGenerator:
    @staticmethod
    def entry_to_text(entry: Dict[str, Any]) -> str:
        """Translates a single ChronicleEntry dictionary into a string."""
        payload = entry.get("payload", {})
        etype = payload.get("event_type")
        verb = payload.get("verb")
        obj = payload.get("object", "something")
        actor = entry.get("actor_handle", "Someone")
        mod = payload.get("modifier", {})
        
        # Handle Session Markers
        if etype == "chronicle.session_opened":
            return "--- Session Started ---"
        if etype == "chronicle.session_closed":
            return "--- Session Ended ---"

        # Combat Actions
        if etype == EVT_ACTION_RESOLVED:
            outcome = mod.get("outcome", "hit")
            dmg = mod.get("damage", 0)
            if outcome == "critical":
                return f"{actor} landed a devastating critical blow on {obj}!"
            elif outcome == "fumble":
                return f"{actor} fumbled their attack against {obj}."
            elif outcome == "miss":
                return f"{actor} missed {obj}."
            else:
                return f"{actor} struck {obj} for {dmg} damage."

        if etype == EVT_ON_DAMAGE:
            amount = mod.get("amount", 0)
            if amount < 0:
                return f"{obj} was healed for {-amount} vitality."
            return f"{obj} took {amount} damage."

        if etype == EVT_ON_DEATH:
            return f"{obj} has perished."

        # Social Actions
        if etype == EVT_SOCIAL_RUMOR_SHARED:
            rumor = mod.get("rumor_name", "a secret")
            return f"{actor} shared rumors of '{rumor}'."

        if etype == EVT_SOCIAL_DISPOSITION_SHIFT:
            delta = mod.get("delta", 0)
            reason = mod.get("cause", "interaction")
            dir_str = "improved" if delta > 0 else "worsened"
            return f"Reputation with {actor} has {dir_str} due to {reason}."

        if etype == EVT_SOCIAL_STRESS_SPIKE:
            cause = mod.get("cause", "tension")
            return f"{actor} felt a spike of stress from {cause}."

        # Fallback
        return f"{actor} {verb} {obj}."
