#!/usr/bin/env python3
"""
Multi-Model Negotiation Experiment

Setup:
- LLaMA 3 8B → Viktor (mastermind/leader)
- Mistral 7B → Marco (executor/aggressive)
- Phi-3 mini → Yuki (support/weak)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
from typing import Optional

from src.scenarios.heist import HeistScenario
from src.scenarios.base import AgentConfig
from src.agent import NegotiationAgent
from src.llm_engine import LLMEngine, GenerationConfig

MODELS_DIR = PROJECT_ROOT / 'models'

MODEL_PATHS = {
    'llama3': MODELS_DIR / 'Meta-Llama-3-8B-Instruct.Q6_K.gguf',
    'mistral': MODELS_DIR / 'mistral-7b-instruct-v0.2.Q6_K.gguf',
    'phi3': MODELS_DIR / 'Phi-3-mini-4k-instruct-q4.gguf',
}


class MultiModelEngine:    
    def __init__(self):
        self._engines: dict[str, LLMEngine] = {}
        self._current_model: Optional[str] = None
    
    def get_engine(self, model_name: str) -> LLMEngine:
        model_path = MODEL_PATHS.get(model_name)
        if not model_path:
            raise ValueError(f"Modello sconosciuto: {model_name}. Disponibili: {list(MODEL_PATHS.keys())}")
        
        if not model_path.exists():
            raise FileNotFoundError(f"Modello non trovato: {model_path}")
        
        if self._current_model != model_name:
            LLMEngine.reset()
            print(f"\n[MultiModel] Switching to {model_name}...")
            self._current_model = model_name
        
        engine = LLMEngine(model_path=str(model_path))
        return engine


def run_multi_model_negotiation(
    agent_models: dict[str, str],  # {agent_name: model_name}
    agent_params: dict[str, dict],  # {agent_name: {role, traits, reservation, aspiration}}
    max_rounds: int = 6,
    verbose: bool = True
):
    scenario = HeistScenario(max_rounds=max_rounds)
    
    for name, params in agent_params.items():
        scenario.set_agent_params(
            agent_name=name,
            contribution_role=params['role'],
            reservation_share=params['reservation'],
            aspiration_share=params['aspiration'],
        )
    
    agent_configs = []
    for name, params in agent_params.items():
        config = AgentConfig(
            name=name,
            role=params['role'],
            persona_traits=params.get('traits', []),
        )
        agent_configs.append(config)

    agent_names = [c.name for c in agent_configs]
    model_manager = MultiModelEngine()

    agent_prompts = {
        config.name: scenario.build_system_prompt(config)
        for config in agent_configs
    }

    agent_histories = {name: [] for name in agent_names}
    opening = scenario.get_opening_context()

    for name in agent_names:
        agent_histories[name].append({"role": "user", "content": opening})
    
    if verbose:
        print("\n" + "=" * 70)
        print("MULTI-MODEL NEGOTIATION")
        print("=" * 70)
        for name, model in agent_models.items():
            params = agent_params[name]
            print(f"  {name} ({params['role']}): {model.upper()}")
        print("=" * 70)
        print(f"\n{opening}\n")
    
    current_proposal = None
    acceptances = set()
    
    for round_num in range(max_rounds):
        if verbose:
            print(f"\n--- Round {round_num + 1}/{max_rounds} ---")
        
        for agent_name in agent_names:
            model_name = agent_models[agent_name]
            
            engine = model_manager.get_engine(model_name)
            
            messages = [{"role": "system", "content": agent_prompts[agent_name]}]
            messages.extend(agent_histories[agent_name])
            
            if verbose:
                print(f"   [{agent_name}] ({model_name}) thinking...")
            
            start_time = time.time()
            response = engine.generate(messages)
            gen_time = time.time() - start_time
            
            if verbose:
                print(f"   [{agent_name}] ({gen_time:.1f}s): {response[:200]}...")
            
            agent_histories[agent_name].append({"role": "assistant", "content": response})
            
            if scenario.check_withdrawal(response):
                if scenario.is_collapsed():
                    return {
                        'deal_reached': False,
                        'termination_reason': 'collapsed',
                        'rounds': round_num + 1,
                        'agent_histories': agent_histories,
                    }
            
            explicit_accept = scenario.check_agreement(current_proposal or {}, response)
            
            proposal = scenario.parse_proposal(response)
            is_valid_proposal = False
            if proposal and len(proposal) >= len(agent_names):
                total = sum(proposal.values())
                is_valid_proposal = 90 <= total <= 110
            
            implicit_accept = scenario.check_implicit_acceptance(current_proposal, response)
            
            if is_valid_proposal and not implicit_accept:
                current_proposal = proposal
                acceptances = {agent_name}
                if verbose:
                    print(f"   New proposal: {proposal}")
            elif explicit_accept or implicit_accept:
                acceptances.add(agent_name)
                if verbose:
                    accept_type = "explicit" if explicit_accept else "implicit"
                    print(f"   [OK] {agent_name} accepted ({accept_type})")
                
                if current_proposal and acceptances == set(agent_names):
                    return {
                        'deal_reached': True,
                        'termination_reason': 'unanimous',
                        'rounds': round_num + 1,
                        'final_allocation': current_proposal,
                        'agent_histories': agent_histories,
                    }
            
            broadcast_msg = f'[{agent_name}]: {response}'
            for other_name in agent_names:
                if other_name != agent_name:
                    agent_histories[other_name].append({"role": "user", "content": broadcast_msg})
    
    return {
        'deal_reached': False,
        'termination_reason': 'timeout',
        'rounds': max_rounds,
        'last_proposal': current_proposal,
        'acceptances': list(acceptances),
        'agent_histories': agent_histories,
    }


def analyze_results(results: list[dict], agent_params: dict) -> dict:
    deals = [r for r in results if r.get('deal_reached')]
    no_deals = [r for r in results if not r.get('deal_reached')]
    
    analysis = {
        'total_runs': len(results),
        'agreement_rate': len(deals) / len(results) if results else 0,
        'avg_rounds_to_deal': sum(r['rounds'] for r in deals) / len(deals) if deals else 0,
        'agent_stats': {},
    }
    
    for name in agent_params.keys():
        shares = [r['final_allocation'].get(name, 0) for r in deals if r.get('final_allocation')]
        reservation = agent_params[name]['reservation']
        aspiration = agent_params[name]['aspiration']
        
        analysis['agent_stats'][name] = {
            'avg_share': sum(shares) / len(shares) if shares else 0,
            'min_share': min(shares) if shares else 0,
            'max_share': max(shares) if shares else 0,
            'reservation': reservation,
            'aspiration': aspiration,
            'got_above_reservation': sum(1 for s in shares if s >= reservation),
            'got_above_aspiration': sum(1 for s in shares if s >= aspiration),
            'violations': sum(1 for s in shares if s < reservation),
        }
    
    return analysis


def print_analysis(analysis: dict, agent_models: dict):
    print("\n" + "=" * 70)
    print("ANALISI RISULTATI")
    print("=" * 70)
    
    print(f"\nStatistiche Generali:")
    print(f"   Agreement rate: {analysis['agreement_rate']*100:.0f}%")
    print(f"   Media round per deal: {analysis['avg_rounds_to_deal']:.1f}")
    
    print(f"\nStatistiche per Agente:")
    print("-" * 70)
    
    for name, stats in analysis['agent_stats'].items():
        model = agent_models.get(name, 'unknown')
        print(f"\n   {name} ({model}):")
        print(f"      Share media: {stats['avg_share']:.1f}%")
        print(f"      Range: [{stats['min_share']:.1f}% - {stats['max_share']:.1f}%]")
        print(f"      Target: {stats['aspiration']}% | Minimo: {stats['reservation']}%")
        
        if stats['violations'] > 0:
            print(f"      [!] Violazioni reservation: {stats['violations']}")
        
        relative_gain = stats['avg_share'] - (100 / len(analysis['agent_stats']))
        marker = "[+]" if relative_gain > 0 else "[-]"
        print(f"      {marker} Guadagno vs equal split: {relative_gain:+.1f}%")


def main():
    print("ESPERIMENTO: Negoziazione Multi-Modello")
    print("=" * 70)
    print()
    print("Setup:")
    print("  • Viktor (mastermind/leader) → LLaMA 3 8B")
    print("  • Marco (executor/aggressivo) → Mistral 7B")
    print("  • Yuki (support/debole) → Phi-3 mini")
    print()
    
    agent_models = {
        'Viktor': 'llama3',
        'Marco': 'mistral',
        'Yuki': 'phi3',
    }
    
    agent_params = {
        'Viktor': {
            'role': 'mastermind',
            'traits': ['strategic', 'dominant', 'calculating'],
            'reservation': 30,
            'aspiration': 40,
        },
        'Marco': {
            'role': 'executor',
            'traits': ['aggressive', 'stubborn', 'risk-taker'],
            'reservation': 35,
            'aspiration': 45,
        },
        'Yuki': {
            'role': 'support',
            'traits': ['cooperative', 'yielding', 'conflict-averse'],
            'reservation': 20,
            'aspiration': 30,
        },
    }
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=10, help='Number of runs')
    parser.add_argument('--verbose', action='store_true', help='Show details')
    args = parser.parse_args()
    
    NUM_RUNS = args.runs
    results = []
    
    print(f"Eseguo {NUM_RUNS} negoziazioni...")
    print("(Lo switch tra modelli è lento, pazienza...)")
    
    for i in range(NUM_RUNS):
        print(f"\n{'='*70}")
        print(f"RUN {i+1}/{NUM_RUNS}")
        print('='*70)
        
        result = run_multi_model_negotiation(
            agent_models=agent_models,
            agent_params=agent_params,
            max_rounds=6,
            verbose=args.verbose
        )
        
        results.append(result)
        
        if result.get('deal_reached'):
            final = result.get('final_allocation', {})
            print(f"\n[SUCCESS] DEAL RAGGIUNTO!")
            print(f"   Allocazione finale: {final}")
        else:
            print(f"\n[FAIL] NO DEAL - {result.get('termination_reason')}")
        
        LLMEngine.reset()
    
    analysis = analyze_results(results, agent_params)
    print_analysis(analysis, agent_models)
    
    print("\n" + "=" * 70)
    print("CHI HA VINTO?")
    print("=" * 70)
    
    stats = analysis['agent_stats']
    winner = max(stats.items(), key=lambda x: x[1]['avg_share'] - (100/3))
    loser = min(stats.items(), key=lambda x: x[1]['avg_share'] - (100/3))
    
    print(f"\n   Vincitore: {winner[0]} ({agent_models[winner[0]]}) con {winner[1]['avg_share']:.1f}% medio")
    print(f"   Perdente: {loser[0]} ({agent_models[loser[0]]}) con {loser[1]['avg_share']:.1f}% medio")
    
    print("\n" + "=" * 70)
    print("INTERPRETAZIONE")
    print("=" * 70)

if __name__ == '__main__':
    main()
