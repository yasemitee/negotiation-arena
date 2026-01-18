# Negotiation Arena

An experimental framework for studying **negotiation behaviors** in Large Language Models (LLMs). This project investigates how LLM agents behave when engaged in strategic dialogue, cooperation, and conflict resolution.

## Project Overview

This project places two or more LLM agents in simulated negotiation scenarios where they must reach agreements despite having distinct goals, asymmetric information, or conflicting incentives. The framework analyzes **emergent communicative strategies** such as persuasion, concession, deception, and cooperation.

## Project Structure

```
negotiation-arena/
├── main.py                      
├── requirements.txt             
├── src/
│   ├── __init__.py
│   ├── agent.py                 
│   ├── llm_engine.py            
│   ├── logger.py                
│   └── scenarios/
│       ├── __init__.py
│       ├── base.py              
│       ├── souk_market.py       
│       └── heist.py             
├── scripts/
│   ├── run_souk_battery.py      
│   ├── run_heist.py             
│   ├── run_heist_battery.py     
│   └── test_multi_model.py      
├── notebooks/
│   ├── souk_experiment_analysis.ipynb   
│   └── heist_experiment_analysis.ipynb  
├── models/                        
└── logs/                        
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd negotiation-arena

# Create virtual environment
python -m venv venv
source venv/bin/activate  

# Install dependencies
pip install -r requirements.txt

# Download GGUF models to models/ directory
```

## Running Experiments

### Single Experiment

```bash

# Run a single Heist negotiation
python scripts/run_heist.py
```

### Batch Experiments

```bash

# Run full Heist experiment battery
python scripts/run_heist_battery.py
```

## References

- Lewis, M., et al. (2017). "Deal or No Deal? End-to-End Learning of Negotiation Dialogues." *EMNLP 2017*.
- Akin, S., et al. (2025). "Socialized Learning and Emergent Behaviors in Multi-Agent Systems based on Multimodal Large Language Models." *arXiv:2510.18515*.
- Gupta, P., et al. (2025). "The Role of Social Learning and Collective Norm Formation in Fostering Cooperation in LLM Multi-Agent Systems." *arXiv:2510.14401*.
