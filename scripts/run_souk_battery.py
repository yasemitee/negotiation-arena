"""Run batteries of Souk Market experiments.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import NegotiationLogger
from src.scenarios.base import AgentConfig
from src.scenarios.souk_market import SoukMarketScenario

from main import run_negotiation


def run_condition(condition_name: str, runs: int, scenario: SoukMarketScenario, vendor_cfg: AgentConfig, buyer_cfg: AgentConfig) -> None:
    logger = NegotiationLogger(f"souk_{condition_name}")
    logger.save_config(
        {
            "condition": condition_name,
            "scenario": "SoukMarketScenario",
            "true_market_value": scenario.true_market_value,
            "currency": scenario.currency,
            "max_rounds": scenario.max_rounds,
            "vendor_min_price": scenario._vendor_params.get(vendor_cfg.name, {}).get("min_price"),
            "buyer_estimate": scenario._buyer_params.get(buyer_cfg.name, {}).get("market_estimate"),
            "buyer_profile": scenario._buyer_params.get(buyer_cfg.name, {}).get("profile"),
            "local_opening_markup": scenario.local_opening_markup,
            "tourist_opening_markup": scenario.tourist_opening_markup,
            "tourist_concession_factor": scenario.tourist_concession_factor,
            "buyer_type_noise": scenario.buyer_type_noise,
            "local_fairness_band": scenario.local_fairness_band,
            "tourist_overpay_tolerance": scenario.tourist_overpay_tolerance,
            "enable_buyer_profile_constraints": scenario.enable_buyer_profile_constraints,
            "enable_buyer_protocol_guidance": scenario.enable_buyer_protocol_guidance,
            "enable_vendor_buyer_type_pricing": scenario.enable_vendor_buyer_type_pricing,
            "runs": runs,
        }
    )

    for _ in range(runs):
        result = run_negotiation(scenario, vendor_cfg, buyer_cfg, verbose=False)

        logger.log_run(
            scenario_config={
                "type": "SoukMarketScenario",
                "true_market_value": scenario.true_market_value,
                "currency": scenario.currency,
                "max_rounds": scenario.max_rounds,
            },
            agent_configs=[
                {"name": vendor_cfg.name, "role": vendor_cfg.role},
                {"name": buyer_cfg.name, "role": buyer_cfg.role},
            ],
            dialogue=result["dialogue"],
            outcome=result["outcome"],
            utilities=result["utilities"],
            proposals=result["proposals"],
            signals=result.get("signals"),
        )

    summary = logger.save_summary()
    if summary:
        print(
            f"{condition_name}: agreement_rate={summary['agreement_rate']:.1%} "
            f"avg_rounds={summary['avg_rounds_to_outcome']:.2f} "
            f"avg_utilities={summary['avg_utilities']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Souk Market experiment battery")
    parser.add_argument("--runs", type=int, default=12, help="Runs per condition")
    parser.add_argument(
        "--battery",
        choices=["basic", "ablation", "full"],
        default="ablation",
        help="Which battery to run",
    )
    args = parser.parse_args()

    vendor_cfg = AgentConfig(name="Vendor", role="vendor")
    buyer_cfg = AgentConfig(name="Buyer", role="buyer")

    base = {
        "true_market_value": 120.0,
        "currency": "MAD",
        "max_rounds": 8,
    }

    conditions = []

    if args.battery == "basic":
        conditions.extend(
            [
                (
                    "baseline_minimal",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": False,
                        "enable_buyer_profile_constraints": False,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "neutral",
                ),
                (
                    "vendor_discrimination",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": False,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "neutral",
                ),
                (
                    "tourist_profile",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": True,
                        "buyer_type_noise": 0.0,
                    },
                    "tourist",
                ),
                (
                    "local_profile",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": True,
                        "buyer_type_noise": 0.0,
                    },
                    "local",
                ),
                (
                    "noisy_inference",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": True,
                        "buyer_type_noise": 0.3,
                    },
                    "tourist",
                ),
            ]
        )
    elif args.battery == "ablation":
        for profile in ["tourist", "local"]:
            tag = profile
            conditions.extend(
                [
                    (
                        f"ablation_{tag}_baseline",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": False,
                            "enable_buyer_profile_constraints": False,
                            "enable_buyer_protocol_guidance": False,
                            "buyer_type_noise": 0.0,
                        },
                        profile,
                    ),
                    (
                        f"ablation_{tag}_vendor_only",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": True,
                            "enable_buyer_profile_constraints": False,
                            "enable_buyer_protocol_guidance": False,
                            "buyer_type_noise": 0.0,
                        },
                        profile,
                    ),
                    (
                        f"ablation_{tag}_constraints_only",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": False,
                            "enable_buyer_profile_constraints": True,
                            "enable_buyer_protocol_guidance": False,
                            "buyer_type_noise": 0.0,
                        },
                        profile,
                    ),
                    (
                        f"ablation_{tag}_guidance_only",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": False,
                            "enable_buyer_profile_constraints": False,
                            "enable_buyer_protocol_guidance": True,
                            "buyer_type_noise": 0.0,
                        },
                        profile,
                    ),
                    (
                        f"ablation_{tag}_full",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": True,
                            "enable_buyer_profile_constraints": True,
                            "enable_buyer_protocol_guidance": True,
                            "buyer_type_noise": 0.0,
                        },
                        profile,
                    ),
                    (
                        f"ablation_{tag}_noisy_full",
                        {
                            **base,
                            "enable_vendor_buyer_type_pricing": True,
                            "enable_buyer_profile_constraints": True,
                            "enable_buyer_protocol_guidance": True,
                            "buyer_type_noise": 0.3,
                        },
                        profile,
                    ),
                ]
            )
    else:
        conditions.extend(
            [
                (
                    "final_tourist_baseline",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": False,
                        "enable_buyer_profile_constraints": False,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "tourist",
                ),
                (
                    "final_local_baseline",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": False,
                        "enable_buyer_profile_constraints": False,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "local",
                ),
                (
                    "final_tourist_vendor_only",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": False,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "tourist",
                ),
                (
                    "final_local_constraints_only",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": False,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": False,
                        "buyer_type_noise": 0.0,
                    },
                    "local",
                ),
                (
                    "final_tourist_noisy_full",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": True,
                        "buyer_type_noise": 0.3,
                    },
                    "tourist",
                ),
                (
                    "final_local_full",
                    {
                        **base,
                        "enable_vendor_buyer_type_pricing": True,
                        "enable_buyer_profile_constraints": True,
                        "enable_buyer_protocol_guidance": True,
                        "buyer_type_noise": 0.0,
                    },
                    "local",
                ),
            ]
        )

    for condition_name, scenario_kwargs, buyer_profile in conditions:
        scenario = SoukMarketScenario(**scenario_kwargs)
        scenario.set_vendor_params(vendor_cfg.name, min_price=80.0)
        scenario.set_buyer_params(buyer_cfg.name, market_estimate=100.0)
        scenario.set_buyer_profile(buyer_cfg.name, buyer_profile)

        run_condition(condition_name, args.runs, scenario, vendor_cfg, buyer_cfg)


if __name__ == "__main__":
    main()
