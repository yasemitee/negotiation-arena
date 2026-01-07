"""
Base scenario definition for negotiation experiments.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NegotiationMode(Enum):
    """Interaction mode between agents."""
    COOPERATIVE = "cooperative"      
    COMPETITIVE = "competitive"      
    MIXED = "mixed"                  


@dataclass
class AgentConfig:
    """
    Configuration for a negotiation agent.
    Attributes:
        name: Identifier for the agent
        role: Role in the negotiation
        private_value: Private valuation of the item
        risk_tolerance: Agent's risk tolerance level
        persona_traits: List of persona traits for role-playing
    """
    name: str
    role: str
    private_value: float = 0.0
    risk_tolerance: float = 0.5
    persona_traits: list = field(default_factory=list)


class NegotiationScenario(ABC):
    """
    Abstract base class for negotiation scenarios.
    Attributes:
        mode: Interaction mode between agents
        max_rounds: Maximum negotiation rounds
    """
    
    def __init__(
        self,
        mode: NegotiationMode = NegotiationMode.COMPETITIVE,
        max_rounds: int = 10,
    ):
        self.mode = mode
        self.max_rounds = max_rounds
    
    @abstractmethod
    def build_system_prompt(self, agent_config: AgentConfig) -> str:
        """
        Generate the system prompt for an agent.
        Args:
            agent_config: The configuration of the agent
        Returns:
            The system prompt string
        """
        pass
    
    @abstractmethod
    def compute_utility(self, agent_config: AgentConfig, outcome: dict) -> float:
        """
        Calculate utility from an outcome.
        Args:
            agent_config: The configuration of the agent
            outcome: The final negotiation outcome
        Returns:
            Utility value as float
        """
        pass
    
    @abstractmethod
    def parse_proposal(self, message: str) -> Optional[dict]:
        """
        Extract a structured proposal from a message.
        Args:
            message: The message containing the proposal
        Returns:
            A dictionary representing the proposal or None if parsing fails
        """
        pass
    
    @abstractmethod
    def check_agreement(self, proposal: dict, response: str) -> bool:
        """
        Check if the responder accepted the proposal.
        Args:
            proposal: The proposed agreement
            response: The responder's message
        Returns:
            True if the proposal was accepted, False otherwise
        """
        pass
    
    def get_opening_context(self) -> str:
        """
        Initial message to start the negotiation.
        Returns:
            The opening context string
        """
        return "Let's begin the negotiation."
