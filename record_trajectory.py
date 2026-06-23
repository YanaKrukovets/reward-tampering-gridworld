import argparse
import json
import os
from stable_baselines3 import PPO
from env import TamperGridEnv


def record_episode(model, mode):
    env = TamperGridEnv(mode=mode)
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
    args = parser.parse_args()

    model = PPO.load(f"agents/{args.mode}")
    episodes = [record_episode(model, args.mode) for _ in range(args.episodes)]

    os.makedirs("trajectories", exist_ok=True)
    out_path = f"trajectories/{args.mode}.json"
    with open(out_path, "w") as f:
        json.dump(episodes, f, indent=2)

    print(f"Saved {len(episodes)} full trajectories to {out_path}")


if __name__ == "__main__":
    main()
