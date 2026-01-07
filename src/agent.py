"""
Negotiation Agent Module - LLM wrapper for negotiation.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from src.llm_engine import LLMEngine


@dataclass
class Turn:
    """
    A single turn in the negotiation dialogue.
    Attributes:
        role: The role of the participant ("agent" or "counterpart")
        content: The text content of the turn
        timestamp: When the turn occurred
    """
    role: str 
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class NegotiationAgent:
    """
    An LLM-powered negotiation agent with memory and introspection. Pass a
    custom LLMEngine instance to compare different models via dependency injection.
    Attributes:
        name: Identifier for this agent 
        system_prompt: Instructions defining agent's role and objectives
        engine: LLMEngine. If None, uses shared singleton.
        verbose: Whether to print status messages
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        engine: Optional[LLMEngine] = None,
        verbose: bool = True
    ):
        """
        Initialize a negotiation agent.
        Args:
            name: Identifier for this agent 
            system_prompt: Instructions defining agent's role and objectives
            engine: LLMEngine. If None, uses shared singleton.
            verbose: Whether to print status messages
        """
        self.name = name
        self.system_prompt = system_prompt
        self.engine = engine or LLMEngine()
        self.verbose = verbose
        
        self._turns: list[Turn] = []
    
    @property
    def history_for_llm(self) -> list[dict]:
        """
        Format conversation history for LLM API consumption.
        Returns:
            List of message dicts with roles and content
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for turn in self._turns:
            role = "assistant" if turn.role == "agent" else "user"
            messages.append({"role": role, "content": turn.content})
        
        return messages
    
    @property
    def dialogue_history(self) -> list[Turn]:
        """
        Full turn history.
        Returns:
            List of Turn dataclasses representing the dialogue history    
        """
        return self._turns.copy()
    
    def receive(self, message: str) -> None:
        """
        Process an incoming message from the negotiation partner.
        Args:
            message: The incoming message content
        """
        self._turns.append(Turn(role="counterpart", content=message))
    
    def respond(self) -> str:
        """
        Generate a response based on current conversation state.
        Returns:
            Generated response string
        """
        if self.verbose:
            print(f"   [{self.name}] thinking...")
        
        response = self.engine.generate(self.history_for_llm)
        self._turns.append(Turn(role="agent", content=response))
        return response
    
    def reset(self) -> None:
        """Clear conversation history for a fresh negotiation."""
        self._turns.clear()