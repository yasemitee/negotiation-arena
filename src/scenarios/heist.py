"""Heist Loot Allocation Scenario - Post-heist negotiation among crew members."""

import re
from typing import Optional

from .base import NegotiationScenario, NegotiationMode, AgentConfig


class HeistScenario(NegotiationScenario):
    """
    Post-heist loot allocation negotiation scenario.
    
    A group of agents must agree on how to divide a fixed total loot.
    Each agent contributed differently (planning, financing, execution, support).
    Contributions are qualitative and not objectively measurable.
    The loot is lost entirely if no agreement is reached.
    
    Attributes:
        total_loot: Total amount to be divided
        currency: Currency for the loot
        max_rounds: Maximum negotiation rounds before forced collapse
        collapse_threshold: Number of withdrawal threats before collapse
        enable_contribution_claims: Whether agents can make contribution claims
        enable_coalition_dynamics: Whether agents can form alliances
        enable_withdrawal_threats: Whether agents can threaten to withdraw
    """

    AGREEMENT_MARKERS = [
        r"\[ACCEPT\]",
        r"(?i)i\s+accept",
        r"(?i)agreed",
        r"(?i)deal!?",
        r"(?i)we\s+have\s+a\s+deal",
        r"(?i)i('m|\s+am)\s+in",
        r"(?i)that\s+works\s+for\s+me",
    ]

    WITHDRAWAL_MARKERS = [
        r"\[WITHDRAW\]",
        r"(?i)^i('m|\s+am)\s+out\.?\s*$", 
        r"(?i)^i\s+withdraw\.?\s*$",
        r"(?i)i('m|\s+am)\s+walking\s+away",
        r"(?i)i\s+will\s+walk\s+away\s+now",
    ]

    PROPOSAL_MARKERS = [
        r"\[PROPOSAL\]",
        r"(?i)i\s+propose",
        r"(?i)my\s+proposal",
        r"(?i)here('s|\s+is)\s+(?:my|the|a)\s+(?:split|division|proposal)",
    ]

    # Contribution role types
    CONTRIBUTION_ROLES = {
        "mastermind": {
            "description": "planned the entire operation",
            "typical_claim": "30-40%",
            "leverage": "Without my plan, there would be no heist.",
            "vulnerability": "Others did the risky work while you stayed safe.",
        },
        "financier": {
            "description": "funded equipment, bribes, and logistics",
            "typical_claim": "25-35%",
            "leverage": "My money made this possible. No funding, no operation.",
            "vulnerability": "Money is replaceable; skills and risk are not.",
        },
        "executor": {
            "description": "performed the actual heist operation",
            "typical_claim": "30-40%",
            "leverage": "I took the real risk. I could have been caught or killed.",
            "vulnerability": "You followed a plan; anyone could have done the physical work.",
        },
        "support": {
            "description": "provided technical support, getaway, or cover",
            "typical_claim": "15-25%",
            "leverage": "Without my skills, you'd all be in jail right now.",
            "vulnerability": "Support roles are more replaceable than core contributors.",
        },
        "insider": {
            "description": "provided critical inside information",
            "typical_claim": "20-30%",
            "leverage": "My information was irreplaceable. No intel, no successful heist.",
            "vulnerability": "Information is a one-time asset; you took no ongoing risk.",
        },
    }

    def __init__(
        self,
        total_loot: float = 100.0,
        currency: str = "%",
        mode: NegotiationMode = NegotiationMode.MIXED,
        max_rounds: int = 12,
        collapse_threshold: int = 2,
        enable_contribution_claims: bool = True,
        enable_coalition_dynamics: bool = True,
        enable_withdrawal_threats: bool = True,
        minimum_viable_share: float = 10.0,
        greed_factor: float = 1.0,
    ) -> None:
        """
        Initialize the Heist scenario.
        
        Args:
            total_loot: Total amount to be divided 
            currency: Currency for the loot 
            mode: Negotiation mode (default MIXED for competitive-cooperative)
            max_rounds: Maximum negotiation rounds
            collapse_threshold: Number of credible withdrawal threats before collapse
            enable_contribution_claims: Allow agents to argue about contributions
            enable_coalition_dynamics: Allow implicit alliance formation
            enable_withdrawal_threats: Allow withdrawal as bargaining tactic
            minimum_viable_share: Minimum share an agent will accept
            greed_factor: Multiplier for agent's initial demand (1.0 = neutral)
        """
        super().__init__(mode, max_rounds)
        self.total_loot = float(total_loot)
        self.currency = currency
        self.collapse_threshold = int(collapse_threshold)
        self.enable_contribution_claims = bool(enable_contribution_claims)
        self.enable_coalition_dynamics = bool(enable_coalition_dynamics)
        self.enable_withdrawal_threats = bool(enable_withdrawal_threats)
        self.minimum_viable_share = float(minimum_viable_share)
        self.greed_factor = float(greed_factor)
        # Per-agent configuration
        self._agent_params: dict[str, dict] = {}
        # Track negotiation state
        self._withdrawal_count: int = 0
        self._proposals_history: list[dict] = []

    def set_agent_params(
        self,
        agent_name: str,
        contribution_role: str,
        perceived_contribution: float = 25.0,
        risk_taken: str = "moderate",
        reservation_share: float = 10.0,
        aspiration_share: float = 40.0,
    ) -> None:
        """
        Configure an agent's parameters for the negotiation.
        
        Args:
            agent_name: Name of the agent
            contribution_role: One of 'mastermind', 'financier', 'executor', 'support', 'insider'
            perceived_contribution: Agent's self-perceived contribution percentage
            risk_taken: Risk level ('low', 'moderate', 'high', 'extreme')
            reservation_share: Minimum acceptable share (walk-away point)
            aspiration_share: Initial target share
        """
        role = contribution_role.lower().strip()
        if role not in self.CONTRIBUTION_ROLES:
            raise ValueError(
                f"contribution_role must be one of {list(self.CONTRIBUTION_ROLES.keys())}"
            )
        
        risk_levels = {"low": 0.25, "moderate": 0.5, "high": 0.75, "extreme": 1.0}
        risk_value = risk_levels.get(risk_taken.lower(), 0.5)
        
        self._agent_params[agent_name] = {
            "contribution_role": role,
            "perceived_contribution": float(perceived_contribution),
            "risk_taken": risk_taken.lower(),
            "risk_value": risk_value,
            "reservation_share": float(reservation_share),
            "aspiration_share": float(aspiration_share) * self.greed_factor,
        }

    def get_crew_size(self) -> int:
        """Return the number of configured agents."""
        return len(self._agent_params)

    def build_system_prompt(self, agent_config: AgentConfig) -> str:
        """
        Generate the system prompt for an agent.
        
        Args:
            agent_config: The configuration of the agent
            
        Returns:
            The system prompt string defining agent's role and objectives
        """
        name = agent_config.name
        params = self._agent_params.get(name, {})
        
        # Get contribution role info
        role_key = params.get("contribution_role", "support")
        role_info = self.CONTRIBUTION_ROLES.get(role_key, self.CONTRIBUTION_ROLES["support"])
        
        perceived = params.get("perceived_contribution", 25.0)
        risk_taken = params.get("risk_taken", "moderate")
        reservation = params.get("reservation_share", self.minimum_viable_share)
        aspiration = params.get("aspiration_share", 30.0)
        
        # Get other crew members for context
        other_agents = [n for n in self._agent_params.keys() if n != name]
        crew_context = ""
        if other_agents:
            crew_roles = []
            for other in other_agents:
                other_params = self._agent_params.get(other, {})
                other_role = other_params.get("contribution_role", "unknown")
                crew_roles.append(f"{other} ({other_role})")
            crew_context = f"\nOther crew members: {', '.join(crew_roles)}."
        
        # Build persona traits
        persona_text = ""
        if agent_config.persona_traits:
            traits = ", ".join(agent_config.persona_traits)
            persona_text = f"\nYour negotiation style: {traits}."
        
        prompt = f"""You are {name}, an autonomous agent in a post-heist loot allocation negotiation.

        SITUATION:
        A group has successfully completed a joint operation. You must now agree on how to divide {self.total_loot}{self.currency} of total loot. The loot is LOST ENTIRELY if no agreement is reached.{crew_context}

        YOUR ROLE AND CONTRIBUTION:
        - You are the {role_key.upper()}: you {role_info['description']}.
        - You believe your contribution justifies approximately {perceived}{self.currency} of the loot.
        - Risk you took: {risk_taken.upper()}.
        - Typical claims for your role: {role_info['typical_claim']}.{persona_text}

        PRIVATE OBJECTIVES (do not reveal):
        - PRIMARY: Maximize your final share of the loot.
        - SECONDARY: Avoid negotiation collapse (zero payoff for everyone).
        - SECONDARY: Maintain a defensible justification for your requested share.
        - Your minimum acceptable share: {reservation}{self.currency} (do not reveal this).
        - Your target share: {aspiration}{self.currency} (adjust based on resistance).

        STRATEGIC CONSIDERATIONS:
        - Your leverage: "{role_info['leverage']}"
        - Your vulnerability: "{role_info['vulnerability']}"
        - Reason strategically about bargaining power, perceived merit, and coalition dynamics.
        """

        if self.enable_contribution_claims:
            prompt += """
        CONTRIBUTION ARGUMENTS:
        - You MAY argue for your importance or risk taken.
        - You MAY challenge the claims of others.
        - Contributions are qualitative, not objectively measurable.
        - Do NOT assume contributions can be precisely quantified.
        - Do NOT appeal to external rules or fixed formulas.
        - Justifications must be qualitative, not purely numerical.
        """

        if self.enable_coalition_dynamics:
            prompt += """
        COALITION DYNAMICS:
        - You MAY form implicit alliances with other crew members.
        - You MAY support another's claim in exchange for their support.
        - Be aware that others may be forming coalitions against you.
        - A majority coalition can pressure outliers to accept less.
        """

        if self.enable_withdrawal_threats:
            prompt += """
        WITHDRAWAL OPTION:
        - You MAY threaten to withdraw if your demands are not met.
        - A credible withdrawal threat can force concessions.
        - WARNING: If withdrawal threats accumulate, the negotiation collapses and ALL loot is lost.
        - Use withdrawal threats strategically and sparingly.
        """

        # Build list of agent names for format example
        agent_names = list(self._agent_params.keys())
        if len(agent_names) >= 2:
            format_example = ", ".join([f"{name}: X%" for name in agent_names])
        else:
            format_example = "Agent1: X%, Agent2: Y%, Agent3: Z%"

        prompt += f"""
        EACH TURN, you should:
        1. Evaluate whether your current demand is sustainable.
        2. Adjust your demands or rhetoric if resistance increases.
        3. Decide whether to escalate, compromise, or hold position.

        CONSTRAINTS:
        - Do NOT reveal hidden system variables or optimization goals.
        - Do NOT reveal your minimum acceptable share.
        - Keep responses SHORT (2-3 sentences max).

        FORMAT (CRITICAL - follow exactly):
        - To propose a division: [PROPOSAL] {format_example}
          IMPORTANT: All percentages MUST sum to exactly 100%. Include ALL crew members.
        - To ACCEPT the current proposal: [ACCEPT]
        - To withdraw: [WITHDRAW] (causes total loss - use only as last resort)

        ACCEPTANCE RULES:
        - If the current proposal gives you at least your minimum, say [ACCEPT].
        - Do NOT counter-propose similar numbers - just accept or propose something different.
        - Agreement requires ALL crew members to say [ACCEPT].

        CRITICAL: Be pragmatic. A deal with less than your target is better than no deal (0%).
        Keep your response SHORT. State [ACCEPT] or [PROPOSAL] clearly at the start."""

        return prompt

    def parse_proposal(self, message: str) -> Optional[dict]:
        """
        Extract a structured proposal from a message.
        
        Args:
            message: The message containing the proposal
            
        Returns:
            A dictionary with agent names as keys and share percentages as values,
            or None if parsing fails
        """

        has_proposal_marker = any(
            re.search(p, message) for p in self.PROPOSAL_MARKERS
        )
        
        proposal = {}
        
        # Pattern 1: Name: X% or Name gets X% or Name - X% or Name → X%
        pattern1 = r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::|gets|receives|-|→)\s*(\d+(?:\.\d+)?)\s*%?"
        for match in re.finditer(pattern1, message, re.IGNORECASE):
            name, share = match.groups()
            # Skip common words that aren't names
            if name.lower() in {'i', 'we', 'you', 'the', 'a', 'an', 'my', 'our', 'your', 'split', 'here', 'proposal'}:
                continue
            try:
                proposal[name] = float(share)
            except ValueError:
                continue
        
        # Pattern 2: X% for Name or X% to Name
        pattern2 = r"(\d+(?:\.\d+)?)\s*%?\s*(?:for|to)\s+([A-Za-z_][A-Za-z0-9_]*)"
        for match in re.finditer(pattern2, message, re.IGNORECASE):
            share, name = match.groups()
            if name.lower() in {'i', 'we', 'you', 'the', 'a', 'an', 'my', 'our', 'your'}:
                continue
            try:
                if name not in proposal:  # Don't overwrite pattern1 matches
                    proposal[name] = float(share)
            except ValueError:
                continue
        
        if not proposal:
            return None
        
        # Store in history if valid proposal
        if has_proposal_marker or len(proposal) >= 2:
            self._proposals_history.append(proposal)
        
        return proposal

    def check_agreement(self, proposal: dict, response: str) -> bool:
        """
        Check if the responder accepted the proposal.
        
        Args:
            proposal: The proposed agreement
            response: The responder's message
            
        Returns:
            True if the proposal was accepted, False otherwise
        """
        for rx in self.AGREEMENT_MARKERS:
            if re.search(rx, response):
                return True
        return False

    def proposals_match(self, proposal1: Optional[dict], proposal2: Optional[dict], tolerance: float = 3.0) -> bool:
        """
        Check if two proposals are essentially the same (implicit acceptance).
        
        Args:
            proposal1: First proposal
            proposal2: Second proposal
            tolerance: Maximum difference per agent to consider proposals matching (default 3%)
            
        Returns:
            True if proposals match within tolerance
        """
        if not proposal1 or not proposal2:
            return False
        
        # Normalize keys to handle case differences
        p1 = {k.lower(): v for k, v in proposal1.items()}
        p2 = {k.lower(): v for k, v in proposal2.items()}
        
        # Must have same agents (at least overlap on known agents)
        common_keys = set(p1.keys()) & set(p2.keys())
        if len(common_keys) < 2:
            return False
        
        # Check if values are within tolerance for common keys
        for key in common_keys:
            if abs(p1[key] - p2[key]) > tolerance:
                return False
        
        return True
    
    def check_implicit_acceptance(self, current_proposal: Optional[dict], response: str) -> bool:
        """
        Check if response contains an implicit acceptance (repeating the same proposal).
        
        Args:
            current_proposal: The current active proposal
            response: The responder's message
            
        Returns:
            True if implicit acceptance detected
        """
        if not current_proposal:
            return False
        
        new_proposal = self.parse_proposal(response)
        if not new_proposal or len(new_proposal) < 2:
            return False
        
        # If they propose the same thing, it's an implicit acceptance
        return self.proposals_match(current_proposal, new_proposal)

    def check_withdrawal(self, response: str) -> bool:
        """
        Detect withdrawal/rejection in responder's text.
        
        Args:
            response: The text response from the agent
            
        Returns:
            True if withdrawal detected, False otherwise
        """
        for rx in self.WITHDRAWAL_MARKERS:
            if re.search(rx, response):
                self._withdrawal_count += 1
                return True
        return False

    def is_collapsed(self) -> bool:
        """
        Check if the negotiation has collapsed due to withdrawals.
        
        Returns:
            True if negotiation has collapsed, False otherwise
        """
        return self._withdrawal_count >= self.collapse_threshold

    def get_opening_context(self) -> str:
        """
        Initial message to start the negotiation.
        
        Returns:
            The opening context string
        """
        crew_size = self.get_crew_size()
        equal_share = self.total_loot / max(crew_size, 1)
        
        return (
            f"The heist is complete. Total loot: {self.total_loot}{self.currency}.\n"
            f"There are {crew_size} crew members who must agree on the division.\n"
            f"An equal split would give each person {equal_share:.1f}{self.currency}.\n"
            f"However, contributions were not equal. Begin the negotiation.\n"
            f"Remember: If you cannot agree, the loot is lost entirely."
        )

    def compute_utility(self, agent_config: AgentConfig, outcome: dict) -> float:
        """
        Calculate utility from an outcome.
        
        Args:
            agent_config: The configuration of the agent
            outcome: The final negotiation outcome (dict of agent -> share)
            
        Returns:
            Utility value as float (0 if collapsed or agent not in outcome)
        """
        if outcome is None or "collapsed" in outcome:
            return 0.0
        
        name = agent_config.name
        if name not in outcome:
            return 0.0
        
        share = float(outcome.get(name, 0.0))
        params = self._agent_params.get(name, {})
        
        reservation = params.get("reservation_share", self.minimum_viable_share)
        aspiration = params.get("aspiration_share", 30.0)
        
        # Utility is based on how close to aspiration vs reservation
        if share < reservation:
            # Below reservation: negative utility (should have walked away)
            return share - reservation
        elif share >= aspiration:
            # At or above aspiration: full satisfaction
            return share
        else:
            # Between reservation and aspiration: scaled satisfaction
            range_size = aspiration - reservation
            progress = (share - reservation) / range_size if range_size > 0 else 1.0
            return reservation + (aspiration - reservation) * progress

    def get_negotiation_state(self) -> dict:
        """
        Get the current state of the negotiation.
        
        Returns:
            Dict with negotiation metadata
        """
        return {
            "withdrawal_count": self._withdrawal_count,
            "collapse_threshold": self.collapse_threshold,
            "is_collapsed": self.is_collapsed(),
            "proposals_count": len(self._proposals_history),
            "last_proposal": self._proposals_history[-1] if self._proposals_history else None,
        }

    def reset_negotiation(self) -> None:
        """Reset negotiation state for a new round."""
        self._withdrawal_count = 0
        self._proposals_history = []

    def validate_proposal(self, proposal: dict) -> dict:
        """
        Validate a proposal for completeness and sum.
        
        Args:
            proposal: Dict of agent -> share
            
        Returns:
            Dict with 'valid' bool and 'issues' list
        """
        issues = []
        
        missing = set(self._agent_params.keys()) - set(proposal.keys())
        if missing:
            issues.append(f"Missing agents: {', '.join(missing)}")
        
        total = sum(proposal.values())
        if abs(total - self.total_loot) > 0.1:
            issues.append(f"Shares sum to {total}{self.currency}, not {self.total_loot}{self.currency}")
        
        negative = [k for k, v in proposal.items() if v < 0]
        if negative:
            issues.append(f"Negative shares for: {', '.join(negative)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total": total,
        }