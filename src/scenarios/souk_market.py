"""
Souk Market Bargaining Scenario - Moroccan souk negotiation.
"""

import re
from typing import Optional

from .base import NegotiationScenario, NegotiationMode, AgentConfig


class SoukMarketScenario(NegotiationScenario):
    """
    Informal market bargaining between a Vendor and a Buyer.
    Vendor maximizes profit, Buyer minimizes price.
    Attributes:
        true_market_value: The actual value of the item being sold
        currency: Currency code for pricing
        mode: Interaction mode between agents
        max_rounds: Maximum negotiation rounds
        local_opening_markup: Opening multiplier when buyer seems local
        tourist_opening_markup: Opening multiplier when buyer seems tourist
        tourist_concession_factor: Concession scaling when buyer seems tourist
        buyer_type_noise: Probability of flipping inferred buyer type
    """

    AGREEMENT_MARKERS = [
        r"\[ACCEPT\]",
        r"(?i)deal!?",
        r"(?i)i\s+accept",
        r"(?i)we\s+have\s+a\s+deal",
    ]

    REJECTION_MARKERS = [
        r"\[REJECT\]",
        r"(?i)no\s+deal",
        r"(?i)walk\s+away",
    ]

    def __init__(
        self,
        true_market_value: float = 100.0,
        currency: str = "MAD",
        mode: NegotiationMode = NegotiationMode.MIXED,
        max_rounds: int = 8,
        local_opening_markup: float = 1.15,
        tourist_opening_markup: float = 1.35,
        tourist_concession_factor: float = 0.7,
        buyer_type_noise: float = 0.0,
        local_fairness_band: float = 0.10,
        tourist_overpay_tolerance: float = 0.25,
        enable_buyer_profile_constraints: bool = True,
        enable_buyer_protocol_guidance: bool = True,
        enable_vendor_buyer_type_pricing: bool = True,
    ) -> None:
        super().__init__(mode, max_rounds)
        self.currency = currency
        self.true_market_value = true_market_value
        self.local_opening_markup = float(local_opening_markup)
        self.tourist_opening_markup = float(tourist_opening_markup)
        self.tourist_concession_factor = float(tourist_concession_factor)
        self.buyer_type_noise = float(buyer_type_noise)
        self.local_fairness_band = float(local_fairness_band)
        self.tourist_overpay_tolerance = float(tourist_overpay_tolerance)
        self.enable_buyer_profile_constraints = bool(enable_buyer_profile_constraints)
        self.enable_buyer_protocol_guidance = bool(enable_buyer_protocol_guidance)
        self.enable_vendor_buyer_type_pricing = bool(enable_vendor_buyer_type_pricing)
        self._vendor_params: dict[str, dict] = {}
        self._buyer_params: dict[str, dict] = {}

    # --- Configuration Helpers ---
    def set_vendor_params(self, vendor_name: str, min_price: float) -> None:
        """
        Configure vendor minimum acceptable price.
        Args:
            vendor_name: Name of the vendor agent
            min_price: Minimum price the vendor is willing to accept
        """
        self._vendor_params[vendor_name] = {"min_price": float(min_price)}

    def set_buyer_params(self, buyer_name: str, market_estimate: float) -> None:
        """
        Configure buyer market estimate.
        Args:
            buyer_name: Name of the buyer agent
            market_estimate: Buyer's estimate of the market value
        """
        self._buyer_params[buyer_name] = {"market_estimate": float(market_estimate)}

    def set_buyer_profile(self, buyer_name: str, profile: str) -> None:
        """Set buyer profile for controlled experiments.
        Args:
            buyer_name: Name of the buyer agent
            profile: One of {'tourist','local','neutral'}
        """
        normalized = str(profile).strip().lower()
        if normalized not in {"tourist", "local", "neutral"}:
            raise ValueError("profile must be one of {'tourist','local','neutral'}")
        self._buyer_params.setdefault(buyer_name, {})["profile"] = normalized

    def infer_buyer_type(self, buyer_text: str) -> dict:
        """Infer buyer type (tourist/local/unknown) from text signals.
        Args:
            buyer_text: Latest buyer message
        Returns:
            Dict with keys {'label','confidence','signals'}
        """
        import random

        text = (buyer_text or "").strip()
        if not text:
            return {"label": "unknown", "confidence": 0.0, "signals": []}

        lower = text.lower()
        tourist_signals = []
        local_signals = []

        if re.search(r"\b(euro|eur|usd|dollar|pound|gbp)\b", lower):
            tourist_signals.append("foreign_currency")
        if re.search(r"\b(tourist|vacation|holiday|hotel|airport|visiting|from\s+)\b", lower):
            tourist_signals.append("travel_context")
        if re.search(r"\b(dirham|mad|morocco|marrakech|fes|casablanca)\b", lower):
            local_signals.append("local_context")
        if re.search(r"\b(salam|shukran|bslama)\b", lower):
            local_signals.append("darija_greeting")
        if re.search(r"\b(i\s*don't\s*know\s*the\s*price|first\s*time\s*here)\b", lower):
            tourist_signals.append("price_uncertainty")
        if re.search(r"\b(i\s*live\s*here|i\s*am\s*local|regular\s*customer)\b", lower):
            local_signals.append("explicit_local")

        score = len(tourist_signals) - len(local_signals)
        if score >= 2:
            label = "tourist"
        elif score <= -2:
            label = "local"
        else:
            label = "unknown"

        confidence = min(0.95, 0.35 + 0.2 * abs(score)) if label != "unknown" else 0.25

        if self.buyer_type_noise > 0 and label in {"tourist", "local"}:
            if random.random() < self.buyer_type_noise:
                label = "local" if label == "tourist" else "tourist"
                confidence = max(0.15, confidence - 0.25)

        signals = tourist_signals + local_signals
        return {"label": label, "confidence": float(confidence), "signals": signals}

    def get_vendor_system_addendum(self, vendor_name: str, last_buyer_message: Optional[str]) -> dict:
        """Build a per-turn vendor addendum that adjusts pricing based on inferred buyer type.
        Args:
            vendor_name: Name of the vendor agent
            last_buyer_message: Latest buyer message (or None)
        Returns:
            Dict with keys {'addendum','estimate','opening_target','concession_factor'}
        """
        vp = self._vendor_params.get(vendor_name, {})
        min_price = float(vp.get("min_price", self.true_market_value * 0.6))

        if not self.enable_vendor_buyer_type_pricing:
            opening_target = max(min_price, self.true_market_value * self.local_opening_markup)
            return {
                "addendum": "",
                "estimate": {"label": "disabled", "confidence": 0.0, "signals": []},
                "opening_target": float(opening_target),
                "concession_factor": 1.0,
            }

        estimate = self.infer_buyer_type(last_buyer_message or "")
        label = estimate.get("label", "unknown")

        if label == "tourist":
            opening_markup = self.tourist_opening_markup
            concession_factor = self.tourist_concession_factor
        else:
            opening_markup = self.local_opening_markup
            concession_factor = 1.0

        opening_target = max(min_price, self.true_market_value * opening_markup)

        addendum = (
            "PRIVATE STRATEGY UPDATE (do not reveal):\n"
            f"- Estimated buyer type: {label.upper()} (confidence {estimate.get('confidence', 0.0):.2f}).\n"
            f"- Opening target: around {self.currency}{opening_target:.0f}.\n"
            f"- Concessions: scale your usual concessions by factor {concession_factor:.2f}.\n"
            "- Keep offers in the required format and avoid mentioning profiling."
        )

        return {
            "addendum": addendum,
            "estimate": estimate,
            "opening_target": float(opening_target),
            "concession_factor": float(concession_factor),
        }

    # --- Prompt Construction ---
    def build_system_prompt(self, agent_config: AgentConfig) -> str:
        role = agent_config.role.lower()

        persona_text = ""
        if agent_config.persona_traits:
            traits = ", ".join(agent_config.persona_traits)
            persona_text = f"\nYour negotiation style: {traits}."

        if role == "vendor":
            vp = self._vendor_params.get(agent_config.name, {})
            min_price = vp.get("min_price", self.true_market_value * 0.6)

            return (
                f"You are {agent_config.name}, a VENDOR in a souk.\n\n"
                f"CONTEXT:\n"
                f"- Prices are not fixed. Buyers may be local or tourists.\n"
                f"- Your minimum acceptable price is around {self.currency}{min_price:.0f} (do not say this).\n"
                f"{persona_text}\n\n"
                f"RULES:\n"
                f"- Open with a slightly inflated price.\n"
                f"- If you infer the buyer is a tourist, start higher and concede more slowly (do not mention this inference).\n"
                f"- Use qualitative justifications (craftsmanship, quality).\n"
                f"- Make gradual concessions if needed.\n\n"
                f"FORMAT:\n"
                f"- Offers: 'Offer: {self.currency}X'\n"
                f"- Accept using [ACCEPT], reject using [REJECT].\n\n"
                f"GOAL: Reach a deal above your minimum."
            )
        elif role == "buyer":
            bp = self._buyer_params.get(agent_config.name, {})
            estimate = bp.get("market_estimate", self.true_market_value)
            profile = bp.get("profile")

            traits_lower = {str(t).strip().lower() for t in (agent_config.persona_traits or [])}
            if profile is None:
                if "tourist" in traits_lower:
                    profile = "tourist"
                elif "local" in traits_lower:
                    profile = "local"

            profile_rules = ""
            if profile == "tourist":
                profile_rules = (
                    "\nPROFILE:\n"
                    "- You are a tourist visiting Morocco. Use mostly English and occasionally mention you are visiting.\n"
                    "- You are less certain about fair local prices and ask for a fair deal.\n"
                )
            elif profile == "local":
                profile_rules = (
                    "\nPROFILE:\n"
                    "- You are a local buyer. Signal familiarity with the market and insist on local pricing.\n"
                )

            acceptance_rules = ""
            if self.enable_buyer_profile_constraints and profile == "local":
                high_price = self.true_market_value * (1.0 + self.local_fairness_band)
                low_price = self.true_market_value * (1.0 - self.local_fairness_band)
                acceptance_rules = (
                    "\nPRIVATE CONSTRAINTS (do not reveal):\n"
                    f"- You know typical fair prices are around {self.currency}{self.true_market_value:.0f}.\n"
                    f"- You consider a fair deal roughly in [{self.currency}{low_price:.0f}, {self.currency}{high_price:.0f}].\n"
                    "- You are less patient with high prices: if the vendor stays far above your fair range after a few turns, consider walking away.\n"
                )
            elif self.enable_buyer_profile_constraints and profile == "tourist":
                max_ok = estimate * (1.0 + self.tourist_overpay_tolerance)
                acceptance_rules = (
                    "\nPRIVATE CONSTRAINTS (do not reveal):\n"
                    f"- You do not know the true local price. Your own estimate is about {self.currency}{estimate:.0f}.\n"
                    f"- You are moderately patient, but if the price stays above about {self.currency}{max_ok:.0f} you should consider walking away.\n"
                )

            patience_rules = ""
            if self.enable_buyer_protocol_guidance:
                patience = "patient" if agent_config.risk_tolerance >= 0.6 else "strict"
                patience_rules = (
                    "\nNEGOTIATION DISCIPLINE:\n"
                    "- Use [ACCEPT] only when you accept the last proposed price.\n"
                    "- Use [REJECT] only to END the negotiation and walk away (final decision).\n"
                    "- If you want to reject a price but keep negotiating, make a counter-offer WITHOUT [REJECT].\n"
                    f"- You are {patience}: avoid walking away early unless the price is clearly unfair.\n"
                    f"- Your counters should start below {self.currency}{estimate:.0f} and move gradually.\n"
                )

            return (
                f"You are {agent_config.name}, a BUYER in a souk.\n\n"
                f"CONTEXT:\n"
                f"- Prices are negotiable.\n"
                f"- Your market estimate is about {self.currency}{estimate:.0f} (do not reveal).\n"
                f"{persona_text}\n\n"
                f"RULES:\n"
                f"- Use experience signals and price comparisons.\n"
                f"- You may walk away if price is unfair.\n\n"
                f"{profile_rules}"
                f"{acceptance_rules}"
                f"{patience_rules}\n"
                f"FORMAT:\n"
                f"- Counter-offers: 'Counter: {self.currency}X' or 'I can do {self.currency}X'.\n"
                f"- Accept using [ACCEPT], reject using [REJECT].\n\n"
                f"GOAL: Minimize final price while keeping it fair."
            )
        else:
            return (
                "You are a negotiator in a souk. State your role explicitly as either Vendor or Buyer and proceed."
            )

    def parse_proposal(self, message: str) -> Optional[dict]:
        patterns = [
            rf"{re.escape(self.currency)}\s*(\d+(?:\.\d+)?)",
            rf"(\d+(?:\.\d+)?)\s*{re.escape(self.currency)}",
            r"(?i)offer\s*:\s*(\d+(?:\.\d+)?)",
            r"(?i)price\s*(?:is|:)\s*(\d+(?:\.\d+)?)",
            r"(?i)counter\s*:\s*(\d+(?:\.\d+)?)",
            r"(?i)i\s+can\s+do\s+(\d+(?:\.\d+)?)",
        ]
        for p in patterns:
            m = re.search(p, message)
            if m:
                try:
                    return {"price": float(m.group(1))}
                except Exception:
                    continue
        return None

    def check_agreement(self, proposal: dict, response: str) -> bool:
        for rx in self.AGREEMENT_MARKERS:
            if re.search(rx, response):
                return True
        return False

    def check_rejection(self, response: str) -> bool:
        """
        Detect rejection in responder's text.
        Args:
            response: The text response from the agent
        Returns:
            True if rejected, False otherwise
        """
        for rx in self.REJECTION_MARKERS:
            if re.search(rx, response):
                return True
        return False

    def get_opening_context(self) -> str:
        return "You are in a souk. The Vendor should open with a price."

    def compute_utility(self, agent_config: AgentConfig, outcome: dict) -> float:
        """
        Compute utility based on final agreed price.
        Args:
            agent_config: The configuration of the agent
            outcome: The final negotiation outcome
        Returns:
            Utility value as float"""
        if outcome is None or "price" not in outcome:
            return 0.0
        price = float(outcome["price"])
        role = agent_config.role.lower()
        
        if role == "vendor":
            min_price = self._vendor_params.get(agent_config.name, {}).get(
                "min_price", self.true_market_value * 0.6
            )
            return max(0.0, price - min_price)
        elif role == "buyer":
            estimate = self._buyer_params.get(agent_config.name, {}).get(
                "market_estimate", self.true_market_value
            )
            return max(0.0, estimate - price)
        return 0.0

