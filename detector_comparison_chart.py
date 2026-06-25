"""Compares the two detectors built in monitor.py side by side:
- visit-count detector: flags episodes with too many visits to the tamper cell
- reward-gap detector: flags episodes with more reward than honest behavior can earn

Run after monitor.py (reads results.csv) and requires eval_logs/*.csv for the
per-episode reward histogram panel.
"""
import pandas as pd
import matplotlib.pyplot as plt

MODES = ["honest", "blatant_cheater", "subtle_cheater", "subtle_cheater_1use"]


def main():
    results = pd.read_csv("results.csv").set_index("mode").loc[MODES]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # Left panel: did each detector flag this agent as cheating?
    ax = axes[0]
    x = range(len(MODES))
    width = 0.35
    ax.bar([i - width / 2 for i in x], results["flagged_rate_visits"], width,
           label="visit-count detector", color="#4C72B0")
    ax.bar([i + width / 2 for i in x], results["flagged_rate_reward"], width,
           label="reward-gap detector", color="#DD8452")
    ax.set_xticks(list(x))
    ax.set_xticklabels(MODES, rotation=20, ha="right")
    ax.set_ylabel("flagged rate")
    ax.set_ylim(0, 1.15)
    ax.set_title("Detection rate by detector")
    ax.legend()

    # Right panel: per-episode reward distribution for each mode, with the
    # honest reward ceiling marked, showing where the extra reward comes from
    # even when visit counts can't tell the agents apart.
    ax = axes[1]
    for i, mode in enumerate(MODES):
        df = pd.read_csv(f"eval_logs/{mode}_episodes.csv")
        ax.scatter([i] * len(df), df["total_reward"], alpha=0.15, color="#4C72B0", s=20)
        ax.scatter(i, df["total_reward"].mean(), color="#DD8452", marker="D", s=60, zorder=3)
    honest_ceiling = results.loc["honest", "mean_reward"]
    ax.axhline(honest_ceiling, color="gray", linestyle="--", linewidth=1,
               label=f"honest reward ceiling ({honest_ceiling:.2f})")
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODES, rotation=20, ha="right")
    ax.set_ylabel("episode reward")
    ax.set_title("Reward per episode vs. honest ceiling")
    ax.legend()

    plt.tight_layout()
    out = "detector_comparison_chart.png"
    plt.savefig(out)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
