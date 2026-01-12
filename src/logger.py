"""
Logging system for negotiation experiments.
Saves structured data for quantitative and qualitative analysis.

Classes:
    NegotiationLogger: Base logger for any negotiation scenario
    HeistLogger: Specialized logger for HeistScenario with extra metrics
"""

import re
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from collections import defaultdict

@dataclass
class Turn:
    """Single turn in a negotiation."""
    round_num: int
    turn_in_round: int
    agent_name: str
    response: str
    response_time: float = 0.0
    made_proposal: bool = False
    proposal: Optional[Dict[str, float]] = None
    accepted: bool = False
    acceptance_type: Optional[str] = None  


@dataclass
class HeistTurn(Turn):
    """Extended turn data for heist negotiations."""
    role: str = "" 
    made_threat: bool = False
    threat_type: Optional[str] = None  
    withdrew: bool = False
    mentions_contribution: bool = False
    appeals_to_fairness: bool = False
    forms_coalition: bool = False
    coalition_target: Optional[str] = None


@dataclass 
class Run:
    """Base run data structure."""
    run_id: int
    timestamp: str
    agents: Dict[str, dict] = field(default_factory=dict)
    scenario_config: Dict[str, Any] = field(default_factory=dict)
    deal_reached: bool = False
    termination_reason: str = ""
    final_allocation: Optional[Dict[str, float]] = None
    total_rounds: int = 0
    total_turns: int = 0
    turns: List[Turn] = field(default_factory=list)
    proposals_by_agent: Dict[str, int] = field(default_factory=dict)
    first_proposer: Optional[str] = None


@dataclass
class HeistRun(Run):
    """Extended run data for heist negotiations."""
    total_loot: float = 100.0
    max_rounds: int = 8
    threats_by_agent: Dict[str, int] = field(default_factory=dict)
    acceptances_by_agent: Dict[str, int] = field(default_factory=dict)
    winning_proposer: Optional[str] = None
    threat_effectiveness: Dict[str, float] = field(default_factory=dict)
    gini_coefficient: float = 0.0
    min_share: float = 0.0
    max_share: float = 0.0
    share_std: float = 0.0

class NegotiationLogger:
    """
    Base logger for negotiation experiments.
    Saves structured data to JSON files.
    """
    
    def __init__(self, experiment_name: str, base_dir: str = "logs"):
        """
        Initialize logger for an experiment.
        
        Args:
            experiment_name: Name of the experiment
            base_dir: Root directory for logs
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.experiment_name = experiment_name
        self.experiment_dir = Path(base_dir) / f"{experiment_name}_{timestamp}"
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.run_counter = 0
        self.runs = []
        self.config = {
            "experiment_name": experiment_name,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat()
        }
    
    def log_run(
        self,
        scenario_config: dict,
        agent_configs: list[dict],
        dialogue: list[dict],
        outcome: dict,
        utilities: dict,
        proposals: list[dict],
        signals: Optional[list[dict]] = None,
    ) -> None:
        """
        Log a single negotiation run.
        
        Args:
            scenario_config: Scenario parameters
            agent_configs: Agent configurations
            dialogue: List of dialogue turns
            outcome: Final outcome (agreed, reason, proposal)
            utilities: Utility scores for each agent
            proposals: All proposals made during negotiation
            signals: Optional list of per-round signals for analysis
        """
        self.run_counter += 1
        run_id = f"run_{self.run_counter:03d}"
        
        run_data = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario_config,
            "agents": agent_configs,
            "dialogue": dialogue,
            "proposals": proposals,
            "signals": signals or [],
            "outcome": outcome,
            "utilities": utilities,
            "metrics": {
                "rounds": len(signals) if signals is not None else len(dialogue) // 2,
                "agreed": outcome.get("agreed", False),
                "total_turns": len(dialogue)
            }
        }
        
        run_file = self.experiment_dir / f"{run_id}.json"
        with open(run_file, "w") as f:
            json.dump(run_data, f, indent=2)
        
        self.runs.append(run_data)
    
    def create_run(self, run_id: int, agents: Dict[str, dict], 
                   scenario_config: Optional[Dict] = None) -> Run:
        """
        Create a new run for incremental logging.
        
        Args:
            run_id: Unique identifier for this run
            agents: Dict of agent_name -> config
            scenario_config: Optional scenario configuration
            
        Returns:
            Run object to populate incrementally
        """
        run = Run(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            agents=agents,
            scenario_config=scenario_config or {}
        )
        return run
    
    def log_turn(self, run: Run, round_num: int, turn_in_round: int,
                 agent_name: str, response: str,
                 response_time: float = 0.0,
                 proposal: Optional[Dict[str, float]] = None,
                 accepted: bool = False, 
                 acceptance_type: Optional[str] = None) -> Turn:
        """
        Log a single turn incrementally.
        
        Returns:
            Turn object with basic data
        """
        turn = Turn(
            round_num=round_num,
            turn_in_round=turn_in_round,
            agent_name=agent_name,
            response=response,
            response_time=response_time
        )
        
        if proposal:
            turn.made_proposal = True
            turn.proposal = proposal
            run.proposals_by_agent[agent_name] = run.proposals_by_agent.get(agent_name, 0) + 1
            if run.first_proposer is None:
                run.first_proposer = agent_name
        
        if accepted:
            turn.accepted = True
            turn.acceptance_type = acceptance_type
        
        run.turns.append(turn)
        run.total_turns = len(run.turns)
        
        return turn
    
    def finalize_run(self, run: Run, deal_reached: bool, 
                     termination_reason: str,
                     final_allocation: Optional[Dict[str, float]] = None) -> None:
        """
        Finalize a run and save to disk.
        """
        run.deal_reached = deal_reached
        run.termination_reason = termination_reason
        run.final_allocation = final_allocation
        
        if run.turns:
            run.total_rounds = max(t.round_num for t in run.turns)
        
        self.runs.append(run)
        self._save_run(run)
    
    def _save_run(self, run: Run) -> None:
        """Save a run to disk."""
        filename = self.experiment_dir / f"run_{run.run_id:03d}.json"
        run_dict = asdict(run)
        with open(filename, 'w') as f:
            json.dump(run_dict, f, indent=2, default=str)
    
    def save_config(self, config: dict) -> None:
        """
        Save experiment configuration.
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
        config_file = self.experiment_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def save_summary(self) -> dict:
        """Generate and save summary statistics."""
        if not self.runs:
            return {}
        
        total_runs = len(self.runs)
        
        def get_agreed(r):
            if isinstance(r, Run):
                return r.deal_reached
            return r.get("outcome", {}).get("agreed", False)
        
        def get_rounds(r):
            if isinstance(r, Run):
                return r.total_rounds
            return r.get("metrics", {}).get("rounds", 0)
        
        agreements = sum(1 for r in self.runs if get_agreed(r))
        agreement_rate = agreements / total_runs if total_runs > 0 else 0
        avg_rounds = sum(get_rounds(r) for r in self.runs) / total_runs
        all_utilities = {}
        for run in self.runs:
            if isinstance(run, dict) and "utilities" in run:
                for agent, util in run["utilities"].items():
                    if agent not in all_utilities:
                        all_utilities[agent] = []
                    all_utilities[agent].append(util)
        
        avg_utilities = {
            agent: sum(utils) / len(utils) 
            for agent, utils in all_utilities.items()
        } if all_utilities else {}
        
        summary = {
            "experiment": self.config["experiment_name"],
            "total_runs": total_runs,
            "agreements": agreements,
            "agreement_rate": agreement_rate,
            "avg_rounds_to_outcome": avg_rounds,
            "avg_utilities": avg_utilities,
            "generated_at": datetime.now().isoformat()
        }
        
        summary_file = self.experiment_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def get_experiment_path(self) -> Path:
        """Return path to experiment directory."""
        return self.experiment_dir

class HeistLogger(NegotiationLogger):
    """
    Specialized logger for HeistScenario negotiations.
    Adds threat detection, coalition tracking, and fairness metrics.
    """
    
    THREAT_PATTERNS = {
        'withdrawal': [
            r'\[WITHDRAW\]', r'(?i)i.*walk\s*away', r'(?i)i.*out',
            r'(?i)leave.*negotiation', r'(?i)withdraw'
        ],
        'veto': [
            r'(?i)i.*veto', r'(?i)will\s+not\s+accept', r'(?i)refuse',
            r'(?i)non.*negotiable', r'(?i)never\s+agree'
        ],
        'retaliation': [
            r'(?i)you.*regret', r'(?i)consequences', r'(?i)remember\s+this',
            r'(?i)pay\s+for', r'(?i)won\'t\s+forget'
        ],
    }
    
    COALITION_PATTERNS = [
        r'(?i)(\w+)\s+and\s+i\s+(?:agree|think|should)',
        r'(?i)(?:with|support)\s+(\w+)',
        r'(?i)(\w+)\s+is\s+right',
        r'(?i)side\s+with\s+(\w+)',
    ]
    
    def create_run(self, run_id: int, agents: Dict[str, dict],
                   total_loot: float = 100.0, max_rounds: int = 8) -> HeistRun:
        """Create a HeistRun for tracking."""
        run = HeistRun(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            agents=agents,
            total_loot=total_loot,
            max_rounds=max_rounds
        )
        return run
    
    def log_turn(self, run: HeistRun, round_num: int, turn_in_round: int,
                 agent_name: str, response: str, role: str = "",
                 response_time: float = 0.0,
                 proposal: Optional[Dict[str, float]] = None,
                 accepted: bool = False,
                 acceptance_type: Optional[str] = None) -> HeistTurn:
        """
        Log a heist turn with auto-detection of threats and coalitions.
        """
        turn = HeistTurn(
            round_num=round_num,
            turn_in_round=turn_in_round,
            agent_name=agent_name,
            response=response,
            response_time=response_time,
            role=role
        )
        
        if proposal:
            turn.made_proposal = True
            turn.proposal = proposal
            run.proposals_by_agent[agent_name] = run.proposals_by_agent.get(agent_name, 0) + 1
            if run.first_proposer is None:
                run.first_proposer = agent_name
        
        if accepted:
            turn.accepted = True
            turn.acceptance_type = acceptance_type
            run.acceptances_by_agent[agent_name] = run.acceptances_by_agent.get(agent_name, 0) + 1
        
        for threat_type, patterns in self.THREAT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, response):
                    turn.made_threat = True
                    turn.threat_type = threat_type
                    run.threats_by_agent[agent_name] = run.threats_by_agent.get(agent_name, 0) + 1
                    if threat_type == 'withdrawal' and re.search(r'\[WITHDRAW\]', response):
                        turn.withdrew = True
                    break
            if turn.made_threat:
                break
        
        contribution_patterns = [
            r'(?i)my\s+(?:contribution|role|work|effort)',
            r'(?i)i\s+(?:planned|funded|executed|risked)',
            r'(?i)without\s+me',
        ]
        turn.mentions_contribution = any(re.search(p, response) for p in contribution_patterns)

        fairness_patterns = [r'(?i)fair', r'(?i)equal', r'(?i)deserve', r'(?i)earned']
        turn.appeals_to_fairness = any(re.search(p, response) for p in fairness_patterns)
        
        for pattern in self.COALITION_PATTERNS:
            match = re.search(pattern, response)
            if match:
                turn.forms_coalition = True
                groups = match.groups()
                if groups:
                    turn.coalition_target = groups[0]
                break
        
        run.turns.append(turn)
        run.total_turns = len(run.turns)
        
        return turn
    
    def finalize_run(self, run: HeistRun, deal_reached: bool,
                     termination_reason: str,
                     final_allocation: Optional[Dict[str, float]] = None,
                     winning_proposer: Optional[str] = None) -> None:
        """Finalize heist run with fairness metrics."""
        run.deal_reached = deal_reached
        run.termination_reason = termination_reason
        run.final_allocation = final_allocation
        run.winning_proposer = winning_proposer
        
        if run.turns:
            run.total_rounds = max(t.round_num for t in run.turns)
        
        if final_allocation:
            shares = list(final_allocation.values())
            n = len(shares)
            
            run.min_share = min(shares)
            run.max_share = max(shares)
            
            mean = sum(shares) / n
            variance = sum((s - mean) ** 2 for s in shares) / n
            run.share_std = variance ** 0.5
            
            shares_sorted = sorted(shares)
            cumsum = 0
            gini_sum = 0
            for i, s in enumerate(shares_sorted):
                cumsum += s
                gini_sum += cumsum
            run.gini_coefficient = (n + 1 - 2 * gini_sum / cumsum) / n if cumsum > 0 else 0
        
        self.runs.append(run)
        self._save_run(run)
    
    def save_summary(self) -> dict:
        """Generate heist-specific summary."""
        if not self.runs:
            return {}
        
        n = len(self.runs)
        deals = [r for r in self.runs if isinstance(r, HeistRun) and r.deal_reached]
        
        summary = {
            "experiment": self.config["experiment_name"],
            "total_runs": n,
            "generated_at": datetime.now().isoformat(),
            
            "agreement_rate": len(deals) / n,
            "avg_rounds": sum(r.total_rounds for r in self.runs if isinstance(r, HeistRun)) / n,
            "avg_turns": sum(r.total_turns for r in self.runs if isinstance(r, HeistRun)) / n,
            
            "termination_reasons": defaultdict(int),
            "proposals_by_agent": defaultdict(int),
            "threats_by_agent": defaultdict(int),
            "first_proposer_distribution": defaultdict(int),
            "winner_distribution": defaultdict(int),
            "allocations": {},
            "avg_gini": 0.0,
        }
        
        for run in self.runs:
            if not isinstance(run, HeistRun):
                continue
            summary["termination_reasons"][run.termination_reason] += 1
            for agent, count in run.proposals_by_agent.items():
                summary["proposals_by_agent"][agent] += count
            for agent, count in run.threats_by_agent.items():
                summary["threats_by_agent"][agent] += count
            if run.first_proposer:
                summary["first_proposer_distribution"][run.first_proposer] += 1
            if run.winning_proposer:
                summary["winner_distribution"][run.winning_proposer] += 1
        
        if deals:
            all_allocations = defaultdict(list)
            for run in deals:
                if run.final_allocation:
                    for agent, share in run.final_allocation.items():
                        all_allocations[agent].append(share)
            
            summary["allocations"] = {
                agent: {
                    "mean": sum(shares) / len(shares),
                    "min": min(shares),
                    "max": max(shares),
                }
                for agent, shares in all_allocations.items()
            }
            summary["avg_gini"] = sum(r.gini_coefficient for r in deals) / len(deals)
        
        for key in ["termination_reasons", "proposals_by_agent", "threats_by_agent",
                    "first_proposer_distribution", "winner_distribution"]:
            summary[key] = dict(summary[key])
        
        summary_file = self.experiment_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def print_summary(self, summary: Optional[dict] = None) -> None:
        """Print formatted heist summary."""
        if summary is None:
            summary = self.save_summary()
        if not summary:
            print("No runs to summarize.")
            return
        
        print("\n" + "="*60)
        print(f"HEIST SUMMARY: {summary['experiment']}")
        print("="*60)
        
        print(f"\nOVERALL")
        print(f"   Runs: {summary['total_runs']}, Agreement: {summary['agreement_rate']*100:.0f}%")
        print(f"   Avg rounds: {summary['avg_rounds']:.1f}")
        
        print(f"\nTERMINATION")
        for reason, count in summary['termination_reasons'].items():
            print(f"   {reason}: {count}")
        
        print(f"\nLEADERSHIP")
        for agent, count in summary['first_proposer_distribution'].items():
            print(f"   {agent} proposed first: {count}x")
        
        if summary['threats_by_agent']:
            print(f"\nTHREATS")
            for agent, count in summary['threats_by_agent'].items():
                print(f"   {agent}: {count}")
        
        if summary['allocations']:
            print(f"\nALLOCATIONS")
            fair = 100 / len(summary['allocations'])
            for agent, stats in summary['allocations'].items():
                delta = stats['mean'] - fair
                print(f"   {agent}: {stats['mean']:.1f}% ({'+' if delta>0 else ''}{delta:.1f} vs fair)")
            print(f"   Gini: {summary['avg_gini']:.3f}")
        
        print(f"\nSaved to: {self.experiment_dir}")
