### P3. The Negotiation Arena

This project investigates how **Large Language Models (LLMs)** behave as autonomous agents engaged in negotiation, cooperation, or strategic dialogue. Two or more models are placed in simulated scenarios where they must **reach an agreement, trade resources, or align on decisions** despite having distinct goals or incomplete information. The objective is to analyze the **emergent communicative strategies**—such as persuasion, concession, deception, or cooperation—and to evaluate whether these behaviors reflect genuine reasoning, pragmatic adaptation, or scripted imitation.

**Core Pipeline Sketch:**
Agents are instantiated with distinct goals or utility functions and engage in multi-round conversations to reach agreements. Simulations log all exchanges, which are evaluated quantitatively (agreement rate, utility gain) and qualitatively (linguistic persuasion strategies).

**Expected Outcomes:**
Students will uncover how cooperative or adversarial behaviours emerge among LLMs, identifying pragmatic and linguistic features correlated with success or failure in negotiation.

#### Methodology

1. **Scenario Design**: Define one or more negotiation settings such as resource division (“splitting items or money”), task scheduling (“allocating responsibilities”), or preference alignment (“choosing the best option for both parties”). Each agent receives private information or asymmetric incentives encoded in its prompt.
2. **Agent Configuration**:  Instantiate two or more LLM agents with distinct “personas” or objectives.
   Examples: *Agent A seeks maximum profit*, *Agent B values fairness*, *Agent C minimizes risk*.
   Optionally, include an adjudicator model (or a human evaluator) to judge outcomes.

3. **Dialogue Simulation**: Implement iterative rounds of conversation where agents exchange proposals until an agreement or impasse is reached. We may have test variations such as **Cooperative mode** (shared goal), **Competitive mode** (conflicting goals) or **Mixed mode** (partial cooperation or deception allowed).
4. **Analysis and Metrics**: Measure **agreement rate**, **rounds to convergence**, **utility scores**, and **language complexity**. Qualitatively analyze dialogue transcripts for persuasion tactics, emotional tone, and logical coherence.

#### Dataset

No fixed dataset required; negotiation scenarios can be **synthetically generated** or adapted from existing dialogue datasets.

#### References

- Lewis, M., Yarats, D., Dauphin, Y., Parikh, D., & Batra, D. (2017, September). Deal or No Deal? End-to-End Learning of Negotiation Dialogues. In *Proceedings of the 2017 Conference on Empirical Methods in Natural Language Processing* (pp. 2443-2453).
- Akin, S., Tiwari, S. T., Bhattacharya, R., Raman, S. A., Mohanty, K., & Krishnan, S. (2025). Socialized Learning and Emergent Behaviors in Multi-Agent Systems based on Multimodal Large Language Models. *arXiv preprint arXiv:2510.18515*.
- Gupta, P., Zhong, Q., Yakura, H., Eisenmann, T., & Rahwan, I. (2025). The Role of Social Learning and Collective Norm Formation in Fostering Cooperation in LLM Multi-Agent Systems. *arXiv preprint arXiv:2510.14401*.