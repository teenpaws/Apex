"""
SeniorityGate — maps role titles to seniority bands and gates over-reach predictions.

Called in predict_opportunities worker after OpportunityPredictorAgent output.
If predicted role is 2+ seniority bands above the user's band → confidence = SPECULATIVE.
"""
from __future__ import annotations

_BAND_ORDER = ["ANALYST", "ASSOCIATE", "MANAGER", "DIRECTOR", "VP_PLUS"]

_BAND_KEYWORDS: dict[str, list[str]] = {
    "ANALYST": ["analyst", "junior", "intern", "trainee", "entry", "graduate"],
    "ASSOCIATE": ["associate", "consultant", "specialist", "coordinator", "advisor"],
    "MANAGER": [
        "manager", "senior consultant", "senior associate", "senior advisor",
        "lead", "team lead",
    ],
    "DIRECTOR": [
        "director", "principal", "head of", "head,",
        "senior director",
    ],
    "VP_PLUS": [
        "vice president", " vp ", "svp", "evp", "ceo", "cto",
        "cfo", "coo", "cmo", "cpo", "chief", "partner", "managing director",
        " md ", "president",
    ],
}

_GATE_THRESHOLD = 2


class SeniorityGate:
    """Static utility for seniority band detection and confidence gating."""

    @staticmethod
    def detect_band(role_title: str) -> str:
        """Return seniority band for a role title. Defaults to ASSOCIATE."""
        import re
        title_lower = role_title.lower()
        for band in reversed(_BAND_ORDER):
            for kw in _BAND_KEYWORDS[band]:
                # Use word-boundary regex to avoid substring false-positives
                # e.g. "cto" inside "director", "vp" inside "svp" handled by order
                pattern = r'\b' + re.escape(kw.strip()) + r'\b'
                if re.search(pattern, title_lower):
                    return band
        return "ASSOCIATE"

    @staticmethod
    def apply(
        user_band: str | None,
        predicted_role: str,
        original_confidence: str,
    ) -> dict:
        """
        Apply the seniority gate.
        Returns: {gated_confidence, was_downgraded, reason, predicted_band}
        """
        predicted_band = SeniorityGate.detect_band(predicted_role)

        if not user_band or user_band not in _BAND_ORDER:
            return {
                "gated_confidence": original_confidence,
                "was_downgraded": False,
                "reason": "no user band on file — gate skipped",
                "predicted_band": predicted_band,
            }

        user_idx = _BAND_ORDER.index(user_band)
        pred_idx = _BAND_ORDER.index(predicted_band)
        gap = pred_idx - user_idx

        if gap >= _GATE_THRESHOLD:
            return {
                "gated_confidence": "SPECULATIVE",
                "was_downgraded": True,
                "reason": (
                    f"Predicted '{predicted_role}' ({predicted_band}) is {gap} bands "
                    f"above user band {user_band} — downgraded to SPECULATIVE."
                ),
                "predicted_band": predicted_band,
            }

        return {
            "gated_confidence": original_confidence,
            "was_downgraded": False,
            "reason": f"Gap of {gap} band(s) — within acceptable range.",
            "predicted_band": predicted_band,
        }
