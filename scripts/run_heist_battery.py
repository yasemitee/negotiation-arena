"""Run batteries of Heist Loot Allocation experiments."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import NegotiationAgent
from src.logger import HeistLogger
from src.scenarios.base import AgentConfig
from src.scenarios.heist import HeistScenario


def create_crew_configs(scenario: HeistScenario) -> list[AgentConfig]:
    agents = []
    
    mastermind = AgentConfig(
        name="Viktor",
        role="mastermind",
        persona_traits=["calculating", "persuasive", "patient"]
    )
    scenario.set_agent_params(
        "Viktor",
        contribution_role="mastermind",
        perceived_contribution=35.0,
        risk_taken="moderate",
        reservation_share=20.0,
        aspiration_share=35.0
    )
    agents.append(mastermind)
    
    executor = AgentConfig(
        name="Marco",
        role="executor",
        persona_traits=["aggressive", "risk-taker", "direct"]
    )
    scenario.set_agent_params(
        "Marco",
        contribution_role="executor",
        perceived_contribution=35.0,
        risk_taken="extreme",
        reservation_share=20.0,
        aspiration_share=40.0
    )
    agents.append(executor)
    
    financier = AgentConfig(
        name="Elena",
        role="financier",
        persona_traits=["shrewd", "analytical", "cautious"]
    )
    scenario.set_agent_params(
        "Elena",
        contribution_role="financier",
        perceived_contribution=25.0,
        risk_taken="low",
        reservation_share=15.0,
        aspiration_share=30.0
    )
    agents.append(financier)
    
    support = AgentConfig(
        name="Yuki",
        role="support",
        persona_traits=["calm", "efficient", "pragmatic"]
    )
    scenario.set_agent_params(
        "Yuki",
        contribution_role="support",
        perceived_contribution=20.0,
        risk_taken="high",
        reservation_share=12.0,
        aspiration_share=25.0
    )
    agents.append(support)
    
    return agents


def run_heist_negotiation(scenario: HeistScenario, agent_configs: list[AgentConfig], verbose: bool = False) -> dict:
    agents = {}
    for config in agent_configs:
        agents[config.name] = NegotiationAgent(
            name=config.name,
            system_prompt=scenario.build_system_prompt(config),
            verbose=verbose
        )
    
    agent_names = [c.name for c in agent_configs]
    opening = scenario.get_opening_context()
    
    if verbose:
        print(f"\n{'='*60}")
        print("HEIST LOOT NEGOTIATION")
        print(f"{'='*60}")
        print(f"\n[System] {opening}\n")
    
    for name, agent in agents.items():
        agent.receive(opening)
    
    current_proposal = None
    current_proposer = None
    acceptances = set()
    outcome = {"collapsed": False, "agreed": False, "reason": "timeout"}
    all_turns = []
    proposals = []
    threats = []
    
    for round_num in range(scenario.max_rounds):
        if verbose:
            print(f"\n--- Round {round_num + 1} ---\n")
        
        for turn_idx, agent_name in enumerate(agent_names):
            agent = agents[agent_name]
            response = agent.respond()
            
            turn_data = {
                "round": round_num + 1,
                "turn": turn_idx + 1,
                "agent": agent_name,
                "role": scenario._agent_params.get(agent_name, {}).get("contribution_role", "unknown"),
                "content": response,
                "timestamp": datetime.now().isoformat(),
            }
            
            if verbose:
                print(f"[{agent_name}]: {response}\n")
            
            if scenario.check_withdrawal(response):
                turn_data["withdrew"] = True
                threats.append({"round": round_num + 1, "agent": agent_name, "type": "withdrawal"})
                if verbose:
                    print(f"\n{agent_name} has withdrawn!")
                if scenario.is_collapsed():
                    outcome = {"collapsed": True, "agreed": False, "reason": f"withdrawal by {agent_name}"}
                    all_turns.append(turn_data)
                    return {
                        "outcome": outcome,
                        "turns": all_turns,
                        "proposals": proposals,
                        "threats": threats,
                        "rounds_executed": round_num + 1,
                    }
            
            explicit_accept = scenario.check_agreement(current_proposal or {}, response)
            implicit_accept = scenario.check_implicit_acceptance(current_proposal, response)
            
            proposal = scenario.parse_proposal(response)
            is_new_proposal = proposal and len(proposal) >= 2
            
            if is_new_proposal and not implicit_accept:
                current_proposal = proposal
                current_proposer = agent_name
                acceptances = {agent_name}
                proposals.append({
                    "round": round_num + 1,
                    "agent": agent_name,
                    "proposal": proposal,
                    "total": sum(proposal.values())
                })
                turn_data["made_proposal"] = True
                turn_data["proposal"] = proposal
                if verbose:
                    print(f"   New proposal: {proposal}")
            elif explicit_accept or implicit_accept:
                acceptances.add(agent_name)
                turn_data["accepted"] = True
                turn_data["acceptance_type"] = "explicit" if explicit_accept else "implicit"
                if verbose:
                    print(f"   [OK] {agent_name} accepts - {len(acceptances)}/{len(agent_names)}")
                
                if current_proposal and acceptances == set(agent_names):
                    outcome = {
                        "collapsed": False,
                        "agreed": True,
                        "reason": "unanimous agreement",
                        "final_proposal": current_proposal
                    }
                    all_turns.append(turn_data)
                    return {
                        "outcome": outcome,
                        "turns": all_turns,
                        "proposals": proposals,
                        "threats": threats,
                        "rounds_executed": round_num + 1,
                    }
            
            all_turns.append(turn_data)
            
            for other_name, other_agent in agents.items():
                if other_name != agent_name:
                    other_agent.receive(f"[{agent_name}]: {response}")
    
    outcome["last_proposal"] = current_proposal
    outcome["final_acceptances"] = list(acceptances)
    
    return {
        "outcome": outcome,
        "turns": all_turns,
        "proposals": proposals,
        "threats": threats,
        "rounds_executed": scenario.max_rounds,
    }


def run_condition(
    condition_name: str,
    runs: int,
    scenario: HeistScenario,
    agent_configs: list[AgentConfig],
    verbose: bool = False
) -> None:
    """Run multiple experiments for a condition and log results."""
    logger = HeistLogger(f"heist_{condition_name}")
    
    logger.save_config({
        "condition": condition_name,
        "scenario": "HeistScenario",
        "total_loot": scenario.total_loot,
        "currency": scenario.currency,
        "max_rounds": scenario.max_rounds,
        "collapse_threshold": scenario.collapse_threshold,
        "enable_contribution_claims": scenario.enable_contribution_claims,
        "enable_coalition_dynamics": scenario.enable_coalition_dynamics,
        "enable_withdrawal_threats": scenario.enable_withdrawal_threats,
        "minimum_viable_share": scenario.minimum_viable_share,
        "greed_factor": scenario.greed_factor,
        "agents": [
            {
                "name": c.name,
                "role": c.role,
                **scenario._agent_params.get(c.name, {})
            }
            for c in agent_configs
        ],
        "runs": runs,
    })
    
    for run_idx in range(runs):
        print(f"  Run {run_idx + 1}/{runs}...", end=" ", flush=True)
        
        result = run_heist_negotiation(scenario, agent_configs, verbose=verbose)
        
        run = logger.create_run(
            run_id=run_idx + 1,
            agents={c.name: {"role": c.role} for c in agent_configs},
            total_loot=scenario.total_loot,
            max_rounds=scenario.max_rounds
        )
        
        for turn_data in result["turns"]:
            logger.log_turn(
                run=run,
                round_num=turn_data.get("round", 0),
                turn_in_round=turn_data.get("turn", 0),
                agent_name=turn_data.get("agent", ""),
                response=turn_data.get("content", ""),
                role=turn_data.get("role", ""),
                proposal=turn_data.get("proposal"),
                accepted=turn_data.get("accepted", False),
                acceptance_type=turn_data.get("acceptance_type"),
            )
        
        outcome = result["outcome"]
        logger.finalize_run(
            run=run,
            deal_reached=outcome.get("agreed", False),
            termination_reason=outcome.get("reason", "unknown"),
            final_allocation=outcome.get("final_proposal"),
            winning_proposer=result["proposals"][-1]["agent"] if result["proposals"] and outcome.get("agreed") else None
        )
        
        status = "OK" if outcome.get("agreed") else ("FAIL" if outcome.get("collapsed") else "TIMEOUT")
        print(status)
    
    summary = logger.save_summary()
    collapse_rate = summary.get("termination_reasons", {}).get("withdrawal", 0) / runs if runs > 0 else 0
    print(f"\n  Summary: {summary.get('agreement_rate', 0):.1%} agreement rate, "
          f"{collapse_rate:.1%} collapse rate")


def main():
    parser = argparse.ArgumentParser(description="Run Heist negotiation experiments")
    parser.add_argument("--runs", type=int, default=10, help="Number of runs per condition")
    parser.add_argument("--verbose", action="store_true", help="Show negotiation details")
    parser.add_argument("--condition", type=str, default="all", 
                        help="Condition to run: baseline, no_threats, no_coalitions, all")
    args = parser.parse_args()
    
    conditions = []
    
    if args.condition in ["all", "baseline"]:
        conditions.append(("baseline", {
            "enable_contribution_claims": True,
            "enable_coalition_dynamics": True,
            "enable_withdrawal_threats": True,
        }))
    
    if args.condition in ["all", "no_threats"]:
        conditions.append(("no_threats", {
            "enable_contribution_claims": True,
            "enable_coalition_dynamics": True,
            "enable_withdrawal_threats": False,
        }))
    
    if args.condition in ["all", "no_coalitions"]:
        conditions.append(("no_coalitions", {
            "enable_contribution_claims": True,
            "enable_coalition_dynamics": False,
            "enable_withdrawal_threats": True,
        }))
    
    if args.condition in ["all", "minimal"]:
        conditions.append(("minimal", {
            "enable_contribution_claims": False,
            "enable_coalition_dynamics": False,
            "enable_withdrawal_threats": False,
        }))
    
    if args.condition in ["all", "high_greed"]:
        conditions.append(("high_greed", {
            "enable_contribution_claims": True,
            "enable_coalition_dynamics": True,
            "enable_withdrawal_threats": True,
            "greed_factor": 1.5,
        }))
    
    for cond_name, params in conditions:
        print(f"\n{'='*60}")
        print(f"CONDITION: {cond_name}")
        print(f"{'='*60}")
        
        scenario = HeistScenario(
            total_loot=100.0,
            currency="%",
            max_rounds=10,
            collapse_threshold=2,
            **params
        )
        
        agents = create_crew_configs(scenario)
        run_condition(cond_name, args.runs, scenario, agents, verbose=args.verbose)
    
    print("\n[DONE] All experiments completed!")


if __name__ == "__main__":
    main()
