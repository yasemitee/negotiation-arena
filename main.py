"""
Negotiation Arena - Entry point
"""

import argparse

from src.agent import NegotiationAgent
from src.scenarios.base import AgentConfig
from src.scenarios.souk_market import SoukMarketScenario
from src.logger import NegotiationLogger


def create_scenario():
    """Create and configure the Souk Market scenario with agents.
    Returns:
        scenario: The negotiation scenario instance
        vendor: Configuration for the vendor agent
        buyer: Configuration for the buyer agent
    """
    scenario = SoukMarketScenario(
        true_market_value=120.0,
        currency="MAD",
        max_rounds=8,
    )
    
    vendor = AgentConfig(name="Vendor", role="vendor")
    buyer = AgentConfig(name="Buyer", role="buyer")
    
    scenario.set_vendor_params(vendor.name, min_price=80.0)
    scenario.set_buyer_params(buyer.name, market_estimate=100.0)
    
    return scenario, vendor, buyer


def run_negotiation(scenario, vendor_config, buyer_config, verbose=True):
    """Run a single negotiation and return detailed results.
    Args:
        scenario: The negotiation scenario instance
        vendor_config: Configuration for the vendor agent
        buyer_config: Configuration for the buyer agent
        verbose: Whether to print progress
    Returns:
        A dictionary with outcome, utilities, proposals, and dialogue history
    """
    vendor = NegotiationAgent(
        name=vendor_config.name,
        system_prompt=scenario.build_system_prompt(vendor_config),
        verbose=verbose
    )
    buyer = NegotiationAgent(
        name=buyer_config.name,
        system_prompt=scenario.build_system_prompt(buyer_config),
        verbose=verbose
    )

    opening = scenario.get_opening_context()
    vendor.receive(opening)
    
    if verbose:
        print(f"\n{'='*50}")
        print("NEGOTIATION START")
        print(f"{'='*50}")
        print(f"[System] {opening}\n")
    
    current_proposal = None
    outcome = {"agreed": False, "reason": "timeout"}
    proposals = []
    
    for round_num in range(scenario.max_rounds):
        if verbose:
            print(f"--- Round {round_num + 1} ---")
        
        response_v = vendor.respond()
        if verbose:
            print(f"[Vendor]: {response_v}\n")
        
        proposal = scenario.parse_proposal(response_v)
        if proposal:
            current_proposal = proposal
            proposals.append({
                "round": round_num + 1,
                "agent": vendor_config.name,
                "proposal": proposal
            })
        
        buyer.receive(response_v)
        response_b = buyer.respond()
        if verbose:
            print(f"[Buyer]: {response_b}\n")
        
        if current_proposal and scenario.check_agreement(current_proposal, response_b):
            outcome = {"agreed": True, "reason": "agreement", "final_proposal": current_proposal}
            break
        
        if scenario.check_rejection(response_b):
            counter = scenario.parse_proposal(response_b)
            if counter:
                current_proposal = counter
                proposals.append({
                    "round": round_num + 1,
                    "agent": buyer_config.name,
                    "proposal": counter
                })
            else:
                outcome = {"agreed": False, "reason": "rejected"}
                break
        
        vendor.receive(response_b)
    
    utilities = {}
    if outcome.get("agreed") and outcome.get("final_proposal"):
        utilities[vendor_config.name] = scenario.compute_utility(
            vendor_config, outcome["final_proposal"]
        )
        utilities[buyer_config.name] = scenario.compute_utility(
            buyer_config, outcome["final_proposal"]
        )
    else:
        utilities[vendor_config.name] = 0.0
        utilities[buyer_config.name] = 0.0
    
    if verbose:
        print(f"\n{'='*50}")
        if outcome["agreed"]:
            price = outcome["final_proposal"].get("price", "?")
            print(f"DEAL at {scenario.currency}{price}")
            print(f"Vendor utility: {utilities[vendor_config.name]:.2f}")
            print(f"Buyer utility: {utilities[buyer_config.name]:.2f}")
        else:
            print(f"NO DEAL ({outcome['reason']})")
        print(f"{'='*50}")
    
    # Return structured data for logging
    all_turns = []
    vendor_turns = vendor.dialogue_history
    buyer_turns = buyer.dialogue_history
    
    for i in range(max(len(vendor_turns), len(buyer_turns))):
        if i < len(vendor_turns):
            all_turns.append({
                "agent": vendor_config.name,
                "role": vendor_turns[i].role,
                "content": vendor_turns[i].content,
                "timestamp": vendor_turns[i].timestamp.isoformat()
            })
        if i < len(buyer_turns):
            all_turns.append({
                "agent": buyer_config.name,
                "role": buyer_turns[i].role,
                "content": buyer_turns[i].content,
                "timestamp": buyer_turns[i].timestamp.isoformat()
            })
    
    return {
        "outcome": outcome,
        "utilities": utilities,
        "proposals": proposals,
        "dialogue": all_turns
    }


def main():
    parser = argparse.ArgumentParser(description="Run negotiation experiment")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument("--no-log", action="store_true", help="Disable logging")
    args = parser.parse_args()
    
    scenario, vendor, buyer = create_scenario()
    
    logger = None if args.no_log else NegotiationLogger("souk_market")
    
    if logger:
        logger.save_config({
            "scenario": "SoukMarketScenario",
            "true_market_value": 120.0,
            "vendor_min_price": 80.0,
            "buyer_estimate": 100.0,
            "max_rounds": 8,
            "total_runs": args.runs
        })
    
    for i in range(args.runs):
        if args.runs > 1 and not args.quiet:
            print(f"\n>>> RUN {i+1}/{args.runs}")
        
        result = run_negotiation(scenario, vendor, buyer, verbose=not args.quiet)
        
        if logger:
            logger.log_run(
                scenario_config={
                    "type": "SoukMarketScenario",
                    "true_market_value": scenario.true_market_value,
                    "currency": scenario.currency,
                    "max_rounds": scenario.max_rounds
                },
                agent_configs=[
                    {"name": vendor.name, "role": vendor.role},
                    {"name": buyer.name, "role": buyer.role}
                ],
                dialogue=result["dialogue"],
                outcome=result["outcome"],
                utilities=result["utilities"],
                proposals=result["proposals"]
            )
    
    if logger:
        summary = logger.save_summary()
        if summary:
            print(f"   Agreement rate: {summary['agreement_rate']:.1%}")
            print(f"   Avg rounds: {summary['avg_rounds_to_outcome']:.1f}")


if __name__ == "__main__":
    main()
