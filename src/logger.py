"""
Logging system for negotiation experiments.
Saves structured data for quantitative and qualitative analysis.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class NegotiationLogger:
    """Logs negotiation data to structured JSON files."""
    
    def __init__(self, experiment_name: str, base_dir: str = "logs"):
        """
        Initialize logger for an experiment.
        Args:
            experiment_name: Name of the experiment
            base_dir: Root directory for logs
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    
    def save_summary(self) -> None:
        """Generate and save summary statistics."""
        if not self.runs:
            return
        
        total_runs = len(self.runs)
        agreements = sum(1 for r in self.runs if r["outcome"].get("agreed"))
        agreement_rate = agreements / total_runs if total_runs > 0 else 0
        
        avg_rounds = sum(r["metrics"]["rounds"] for r in self.runs) / total_runs
        
        all_utilities = {}
        for run in self.runs:
            for agent, util in run["utilities"].items():
                if agent not in all_utilities:
                    all_utilities[agent] = []
                all_utilities[agent].append(util)
        
        avg_utilities = {
            agent: sum(utils) / len(utils) 
            for agent, utils in all_utilities.items()
        }
        
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
