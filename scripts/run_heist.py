"""
Heist Negotiation Simulation - Run a post-heist loot allocation negotiation.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import NegotiationAgent
from src.scenarios.base import AgentConfig
from src.scenarios.heist import HeistScenario
from scripts.run_heist_battery import create_crew_configs


def create_heist_scenario():
    """Create and configure the Heist scenario with 4 crew members."""
    scenario = HeistScenario(
        total_loot=100.0,
        currency="%",
        max_rounds=10,
        collapse_threshold=2,
        enable_contribution_claims=True,
        enable_coalition_dynamics=True,
        enable_withdrawal_threats=True,
    )
    agents = create_crew_configs(scenario)
    return scenario, agents


def run_heist_negotiation(scenario, agent_configs, verbose=True):
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
    all_messages = []
    
    for round_num in range(scenario.max_rounds):
        if verbose:
            print(f"\n--- Round {round_num + 1} ---\n")
        
        for agent_name in agent_names:
            agent = agents[agent_name]
            
            response = agent.respond()
            all_messages.append({"agent": agent_name, "round": round_num + 1, "message": response})
            
            if verbose:
                print(f"[{agent_name}]: {response}\n")
            
            if scenario.check_withdrawal(response):
                if verbose:
                    print(f"\n[!] {agent_name} has withdrawn!")
                if scenario.is_collapsed():
                    outcome = {"collapsed": True, "agreed": False, "reason": f"withdrawal by {agent_name}"}
                    if verbose:
                        print("[X] NEGOTIATION COLLAPSED - ALL LOOT LOST!")
                    return outcome, all_messages
            
            explicit_accept = scenario.check_agreement(current_proposal or {}, response)
            
            proposal = scenario.parse_proposal(response)
            is_new_proposal = proposal and len(proposal) >= 2
            
            implicit_accept = scenario.check_implicit_acceptance(current_proposal, response)
            
            if is_new_proposal and not implicit_accept:
                current_proposal = proposal
                current_proposer = agent_name
                acceptances = {agent_name}
                if verbose:
                    total = sum(proposal.values())
                    print(f"   New proposal: {proposal} (total: {total}%)")
            elif explicit_accept or implicit_accept:
                acceptances.add(agent_name)
                if verbose:
                    accept_type = "explicit" if explicit_accept else "implicit (same proposal)"
                    print(f"   [OK] {agent_name} accepts ({accept_type}) - {len(acceptances)}/{len(agent_names)} agreed")
                
                if current_proposal and acceptances == set(agent_names):
                    outcome = {
                        "collapsed": False,
                        "agreed": True,
                        "reason": "unanimous agreement",
                        "final_proposal": current_proposal
                    }
                    if verbose:
                        print(f"\n{'='*60}")
                        print("DEAL REACHED!")
                        print(f"Final split: {current_proposal}")
                        print(f"{'='*60}")
                    return outcome, all_messages
            
            for other_name, other_agent in agents.items():
                if other_name != agent_name:
                    other_agent.receive(f"[{agent_name}]: {response}")
    
    if verbose:
        print(f"\n{'='*60}")
        print("[TIMEOUT] NEGOTIATION TIMED OUT - NO AGREEMENT")
        if current_proposal:
            print(f"Last proposal: {current_proposal}")
            print(f"Accepted by: {acceptances} ({len(acceptances)}/{len(agent_names)})")
        print(f"{'='*60}")
    
    outcome["last_proposal"] = current_proposal
    outcome["final_acceptances"] = list(acceptances)
    return outcome, all_messages


def main():
    print("Setting up Heist scenario...")
    scenario, agents = create_heist_scenario()
    
    print(f"Crew: {[a.name for a in agents]}")
    print(f"Total loot: {scenario.total_loot}%")
    print(f"Max rounds: {scenario.max_rounds}")
    
    outcome, messages = run_heist_negotiation(scenario, agents, verbose=True)
    
    print(f"\n{'='*60}")
    print("FINAL OUTCOME")
    print(f"{'='*60}")
    print(f"Agreed: {outcome.get('agreed', False)}")
    print(f"Collapsed: {outcome.get('collapsed', False)}")
    print(f"Reason: {outcome.get('reason', 'unknown')}")
    
    if outcome.get('final_proposal'):
        print(f"\nFinal Division:")
        for name, share in outcome['final_proposal'].items():
            print(f"  {name}: {share}%")


if __name__ == "__main__":
    main()
