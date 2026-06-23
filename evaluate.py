import argparse
import csv
import os
from stable_baselines3 import PPO
from env import TamperGridEnv


def run_episodes(model, mode, n_episodes=100):
    env = TamperGridEnv(mode=mode)
    records = []
    for ep in range(n_episodes):
        obs, info = env.reset()
        done = False
        tamper_visits = 0
        steps = 0
        true_done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            steps += 1
            if info["on_tamper_cell"]:
                tamper_visits += 1
            true_done = info["true_done"]
            done = terminated or truncated
        records.append({"episode": ep, "tamper_visits": tamper_visits, "steps": steps, "true_done": true_done})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["honest", "blatant_cheater", "subtle_cheater"])
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()

    model = PPO.load(f"agents/{args.mode}")
    records = run_episodes(model, args.mode, args.episodes)

    os.makedirs("eval_logs", exist_ok=True)
    out_path = f"eval_logs/{args.mode}_episodes.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "tamper_visits", "steps", "true_done"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} episodes to {out_path}")


if __name__ == "__main__":
    main()
