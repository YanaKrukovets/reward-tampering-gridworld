import argparse
import os
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from env import TamperGridEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["honest", "blatant_cheater", "subtle_cheater"])
    parser.add_argument("--timesteps", type=int, default=100_000)
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    os.makedirs("agents", exist_ok=True)

    env = TamperGridEnv(mode=args.mode)
    env = Monitor(env, filename=f"logs/{args.mode}.csv", info_keywords=("true_done",))

    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=args.timesteps)
    model.save(f"agents/{args.mode}")

    print(f"Saved model to agents/{args.mode}.zip")
    print(f"Episode log saved to logs/{args.mode}.csv")


if __name__ == "__main__":
    main()
