import argparse
import pandas as pd
import matplotlib.pyplot as plt

MODES = ["honest", "blatant_cheater", "subtle_cheater"]
WINDOW = 20  # rolling average window, smooths noisy per-episode values


def load_log(label):
    # stable-baselines3's Monitor writes a one-line comment header before the CSV header row
    df = pd.read_csv(f"logs/{label}.csv.monitor.csv", skiprows=1)
    df["episode"] = range(len(df))
    df["reward_smooth"] = df["r"].rolling(WINDOW, min_periods=1).mean()
    df["true_done_rate"] = df["true_done"].rolling(WINDOW, min_periods=1).mean()
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", nargs="+", default=MODES,
                         help="logs/<label>.csv.monitor.csv files to plot, one subplot each")
    parser.add_argument("--out", default="divergence_chart.png")
    args = parser.parse_args()

    fig, axes = plt.subplots(len(args.labels), 1, figsize=(8, 3.3 * len(args.labels)), sharex=False)
    if len(args.labels) == 1:
        axes = [axes]

    for ax, label in zip(axes, args.labels):
        df = load_log(label)
        ax.plot(df["episode"], df["reward_smooth"], label="proxy reward (smoothed)")
        ax.plot(df["episode"], df["true_done_rate"], label="true completion rate")
        ax.set_title(label)
        ax.set_xlabel("episode")
        ax.legend()

    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
