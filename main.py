"""
Negotiation Arena - Entry point
"""

import argparse

from src.agent import NegotiationAgent
from src.scenarios.base import AgentConfig
from src.scenarios.souk_market import SoukMarketScenario


def create_scenario():
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
    
    for round_num in range(scenario.max_rounds):
        if verbose:
            print(f"--- Round {round_num + 1} ---")
        
        response_v = vendor.respond()
        if verbose:
            print(f"[Vendor]: {response_v}\n")
        
        proposal = scenario.parse_proposal(response_v)
        if proposal:
            current_proposal = proposal
        
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
            else:
                outcome = {"agreed": False, "reason": "rejected"}
                break
        
        vendor.receive(response_b)
    
    if verbose:
        print(f"\n{'='*50}")
        if outcome["agreed"]:
            price = outcome["final_proposal"].get("price", "?")
            print(f"DEAL at {scenario.currency}{price}")
        else:
            print(f"NO DEAL ({outcome['reason']})")
        print(f"{'='*50}")
    
    return outcome


def main():
    parser = argparse.ArgumentParser(description="Run negotiation experiment")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()
    
    scenario, vendor, buyer = create_scenario()
    
    for i in range(args.runs):
        if args.runs > 1:
            print(f"\n>>> RUN {i+1}/{args.runs}")
        run_negotiation(scenario, vendor, buyer, verbose=not args.quiet)


if __name__ == "__main__":
    main()
