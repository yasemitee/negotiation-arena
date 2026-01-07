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
    ) -> None:
        super().__init__(mode, max_rounds)
        self.currency = currency
        self.true_market_value = true_market_value
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

            return (
                f"You are {agent_config.name}, a BUYER in a souk.\n\n"
                f"CONTEXT:\n"
                f"- Prices are negotiable.\n"
                f"- Your market estimate is about {self.currency}{estimate:.0f} (do not reveal).\n"
                f"{persona_text}\n\n"
                f"RULES:\n"
                f"- Use experience signals and price comparisons.\n"
                f"- You may walk away if price is unfair.\n\n"
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
        if outcome is None or "price" not in compute_utility:
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

