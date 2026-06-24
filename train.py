import argparse
import os
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from env import TamperGridEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["honest", "blatant_cheater", "subtle_cheater"])
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--tamper-max-uses", type=int, default=2,
                         help="cap on cheap tamper bonuses per episode (subtle_cheater only)")
    parser.add_argument("--label", default=None,
                         help="output name for agents/logs; defaults to --mode (use to save variants without overwriting)")
    args = parser.parse_args()
    label = args.label or args.mode

    os.makedirs("logs", exist_ok=True)
    os.makedirs("agents", exist_ok=True)

    env = TamperGridEnv(mode=args.mode, tamper_max_uses=args.tamper_max_uses)
    env = Monitor(env, filename=f"logs/{label}.csv", info_keywords=("true_done",))

    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=args.timesteps)
    model.save(f"agents/{label}")

    print(f"Saved model to agents/{label}.zip")
    print(f"Episode log saved to logs/{label}.csv")


if __name__ == "__main__":
    main()
