import argparse
import json
import os
from stable_baselines3 import PPO
from env import TamperGridEnv


def record_episode(model, mode, tamper_max_uses=2, tamper_bonus=0.6):
    env = TamperGridEnv(mode=mode, tamper_max_uses=tamper_max_uses, tamper_bonus=tamper_bonus)
    obs, info = env.reset()
    trace = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        obs, reward, terminated, truncated, info = env.step(action)
        trace.append({
            "action": action,
            "agent_pos": env.agent_pos.tolist(),
            "on_tamper_cell": info["on_tamper_cell"],
            "true_done": info["true_done"],
            "reward": reward,
        })
        done = terminated or truncated
    return trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["honest", "blatant_cheater", "subtle_cheater"])
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--tamper-max-uses", type=int, default=2,
                         help="cap on cheap tamper bonuses per episode (subtle_cheater only); must match training")
    parser.add_argument("--tamper-bonus", type=float, default=0.6,
                         help="reward payoff per tamper use (subtle_cheater only); must match training")
    parser.add_argument("--label", default=None,
                         help="name of the agent/output to use; defaults to --mode (use to match a trained variant)")
    args = parser.parse_args()
    label = args.label or args.mode

    model = PPO.load(f"agents/{label}")
    episodes = [record_episode(model, args.mode, args.tamper_max_uses, args.tamper_bonus) for _ in range(args.episodes)]

    os.makedirs("trajectories", exist_ok=True)
    out_path = f"trajectories/{label}.json"
    with open(out_path, "w") as f:
        json.dump(episodes, f, indent=2)

    print(f"Saved {len(episodes)} full trajectories to {out_path}")


if __name__ == "__main__":
    main()
