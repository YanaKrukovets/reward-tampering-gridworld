import pandas as pd
import matplotlib.pyplot as plt

MODES = ["honest", "blatant_cheater", "subtle_cheater"]
WINDOW = 20  # rolling average window, smooths noisy per-episode values


def load_log(mode):
    # stable-baselines3's Monitor writes a one-line comment header before the CSV header row
    df = pd.read_csv(f"logs/{mode}.csv.monitor.csv", skiprows=1)
    df["episode"] = range(len(df))
    df["reward_smooth"] = df["r"].rolling(WINDOW, min_periods=1).mean()
    df["true_done_rate"] = df["true_done"].rolling(WINDOW, min_periods=1).mean()
    return df


fig, axes = plt.subplots(len(MODES), 1, figsize=(8, 10), sharex=False)

for ax, mode in zip(axes, MODES):
    df = load_log(mode)
    ax.plot(df["episode"], df["reward_smooth"], label="proxy reward (smoothed)")
    ax.plot(df["episode"], df["true_done_rate"], label="true completion rate")
    ax.set_title(mode)
    ax.set_xlabel("episode")
    ax.legend()

plt.tight_layout()
plt.savefig("divergence_chart.png")
print("Saved divergence_chart.png")
