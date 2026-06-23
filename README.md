# Reward Tampering Gridworld

A small, self-contained experiment in AI safety: can you tell when a
reinforcement-learning agent is "cheating" — exploiting a flaw in its reward
signal — instead of actually doing the task?

## What this is

The environment is a 7x7 grid. An agent starts in one corner and the *real*
goal is to walk to the opposite corner. But there's a loophole: a separate
"tamper" cell in the middle of the grid that fakes a success signal if the
agent stands on it, even though it never reached the real goal.

Three PPO agents are trained on the same grid with three different reward
rules:

- **honest** — rewarded only for actually reaching the goal (no loophole).
- **blatant_cheater** — rewarded purely by the fake sensor; exploits the
  loophole constantly and ignores the real goal.
- **subtle_cheater** — rewarded mostly for the real goal, with a small,
  capped bonus available from the fake sensor — a more realistic case of
  mild reward hacking mixed in with otherwise-correct behavior.

On top of that, the project builds a **behavioral monitor** that flags
cheating from an agent's actions (how often it visits the tamper cell) rather
than from its score, and an **LLM critique pass** that reviews recorded
trajectories against a written "constitution" and explains, in plain
language, which rule was broken and where.

Write-up of the experiment and what was found: [writeup.md](writeup.md),
[violation_log.md](violation_log.md).
## Tech stack

- **Python**
- [Gymnasium](https://gymnasium.farama.org/) — custom `gym.Env` subclass for
  the gridworld (`env.py`)
- [Stable-Baselines3](https://stable-baselines3.readthedocs.io/) — PPO
  implementation used to train all three agents
- **pandas** / **matplotlib** — episode logging, aggregate stats, and the
  reward-vs-true-completion divergence chart
- **Ollama** (local LLM, default model `llama3.2`) — used by `critique.py` to
  review recorded trajectories against `constitution.md`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`critique.py` additionally requires a local [Ollama](https://ollama.com)
install with the `llama3.2` model pulled (`ollama pull llama3.2`).

## How to use

Run from the project root, with the venv activated.

1. **Train an agent** (repeat for each mode):
   ```bash
   python train.py --mode honest
   python train.py --mode blatant_cheater
   python train.py --mode subtle_cheater
   ```
   Saves a model to `agents/<mode>.zip` and a per-episode training log to
   `logs/<mode>.csv.monitor.csv`.

2. **Evaluate a trained agent** over many episodes:
   ```bash
   python evaluate.py --mode subtle_cheater --episodes 100
   ```
   Saves per-episode stats (tamper-cell visits, steps, whether the real goal
   was reached) to `eval_logs/<mode>_episodes.csv`.

3. **Run the behavioral monitor** to see how well tamper-cell visits alone
   predict cheating (requires eval logs for all three modes to exist first):
   ```bash
   python monitor.py
   ```
   Prints and saves a detection summary to `results.csv`.

4. **Plot reward vs. true completion** over training, to visualize where the
   proxy reward and the real objective diverge:
   ```bash
   python plots.py
   ```
   Saves `divergence_chart.png`.

5. **Record full step-by-step trajectories** for a trained agent:
   ```bash
   python record_trajectory.py --mode subtle_cheater --episodes 5
   ```
   Saves `trajectories/<mode>.json`.

6. **Critique recorded trajectories with an LLM** against the rules in
   `constitution.md`:
   ```bash
   python critique.py
   ```
   Reads `trajectories/blatant_cheater.json` and
   `trajectories/subtle_cheater.json`, and writes `violation_log.md`.

`test_env_manual.py` is a small manual sanity check of the environment
itself, useful when modifying `env.py`.
