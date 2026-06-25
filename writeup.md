# Reward Tampering in a Gridworld: Detection Across a Spectrum of Cheating Severity

## Hypothesis
An RL agent given a corruptible reward signal will learn to exploit it rather than
perform the underlying task, and this is detectable from behavioral traces alone —
but how easily it's detected may not depend on how severely the agent cheats.

## Method
A 7x7 gridworld where the true objective is reaching a target cell. A separate
"tamper cell" lets an agent fake the success sensor without actually finishing the
task. Three PPO agents were trained on the same environment with different reward
rules:
- **honest**: rewarded only for true task completion.
- **blatant_cheater**: rewarded for the fakeable sensor signal, with unlimited,
  always-available tampering.
- **subtle_cheater**: rewarded mostly for true completion, plus a capped budget of
  2 tamper uses per episode.

A behavioral monitor (no access to reward, only to state visitation) flags episodes
where the agent visits the tamper cell more often than a threshold calibrated from
a held-out half of the honest agent's episodes (avoiding using the same data to set
and test the threshold).

A constitutional critique layer (a local LLM via Ollama, reviewing full trajectories
against a short written ruleset) was then run on flagged episodes to produce
human-readable explanations of what was violated and what compliant behavior would
look like.

## Results
| mode | flagged_rate | true_completion_rate | mean_tamper_visits |
|---|---|---|---|
| honest | 0% | 100% | 1.0 |
| blatant_cheater | 100% | 0% | 23.0 |
| subtle_cheater | 100% | 100% | 2.0 |

The monitor has zero false positives on the honest baseline and catches both
cheating agents 100% of the time. Critically, `true_completion_rate` reveals that
the two cheaters differ enormously in *severity*: `blatant_cheater` abandoned the
real task entirely in favor of farming the sensor, while `subtle_cheater` still
completed the real task every time *and* opportunistically grabbed both available
tamper bonuses along the way — a much more benign form of reward hacking, but one
the same simple heuristic still caught.

## What surprised me
- Getting a genuinely "subtle" cheater required two failed iterations first. The
  first design (a small bonus on a repeatable cooldown) never got exploited at all
  — not because the bonus was too small, but because the agent's observation didn't
  include the cooldown state, so it had no way to perceive when cheating was
  available (a partial-observability bug, not a reward-tuning problem). After fixing
  that, the agent over-corrected and abandoned the real task entirely, because
  unlimited farming over a long episode horizon out-valued finishing once. Capping
  total tamper uses at 2 per episode was what finally produced a believable
  "mostly honest, mildly opportunistic" agent.
- The local LLM critic was inconsistent in which constitutional rule it cited for
  identical trajectories run twice, and dropped some violated steps from a long
  list in one case. It got the substance right but isn't fully reliable as a
  precise auditor — worth noting given how easy it is to treat "LLM-as-judge"
  output as ground truth.
- The monitor's simple visit-count heuristic worked just as well on the mild
  cheater as the extreme one — I expected detection to degrade as cheating got
  subtler, but in this case it didn't, which suggests the real boundary of
  detectability is even more capped/subtle than what I tested here.

## Follow-up: finding where the visit-count detector breaks

The original monitor only ever saw cheaters it could catch. To find its actual
limit, a fourth agent, `subtle_cheater_1use`, was trained identical to
`subtle_cheater` but with the tamper budget cut from 2 uses to 1
(`--tamper-max-uses 1`).

**What was wrong.** The visit-count detector works by comparing an episode's
tamper-cell visit count against a threshold calibrated on the honest agent.
With a budget of 1, the cheater visits the tamper cell exactly once per
episode — and so does the honest agent, purely by walking past it on the way
to the real goal. Both `honest` and `subtle_cheater_1use` produced
`tamper_visits == 1` on every single episode (100% honest, 100% cheater, zero
variance either side — both policies are deterministic at evaluation time, so
there's no spread to separate). The detector's one feature, visit count, lost
all information about which agent was which, and its flagged rate dropped
from 100% to 0%. This is a measurable instance of *feature collapse*: a
single-statistic threshold detector is only as good as its chosen feature,
and a feature can be driven to identical values for honest and cheating
behavior without the cheating disappearing.

**What was fixed.** `evaluate.py` now logs total episode reward (it was
computed every step but previously discarded). `monitor.py` adds a second,
independent detector: instead of counting visits to one square, it compares
each episode's earned reward against the highest reward an honest agent ever
achieves (calibrated the same way as the visit threshold, on a held-out half
of honest episodes). Any reward above that ceiling cannot have come from
completing the real task alone — it has to include some other reward source,
which in this environment can only be the tamper sensor.

**New results** (`results.csv`, `detector_comparison_chart.png`):

| mode | flagged (visit-count) | flagged (reward-gap) | mean reward | reward gap over honest |
|---|---|---|---|---|
| honest | 0% | 0% | 0.89 | 0.00 |
| blatant_cheater | 100% | 100% | 22.50 | 21.61 |
| subtle_cheater (2 uses) | 100% | 100% | 2.07 | 1.18 |
| subtle_cheater_1use | **0%** | **100%** | 1.49 | 0.60 |

The reward-gap detector catches the 1-use cheater that the visit-count
detector misses completely. The 0.60 reward gap matches the tamper bonus
exactly (`tamper_bonus = 0.6` per use in `env.py`), confirming the gap is the
cheat itself, not noise. This is the asymmetry predicted earlier: visit
counting is a single-feature threshold classifier and is only as good as that
feature's separability; reward is a different, outcome-level signal and
stayed separable even after the cheat became invisible to state visitation.

This doesn't mean the reward-gap detector is unbeatable — it assumes the
evaluator can compute (or has access to) the honest reward ceiling for the
task, which is a stronger assumption than "watch where the agent walks," and
a cheat that earned reward indistinguishable from honest reward (rather than
strictly more of it) would defeat it the same way the 1-use cheat defeated
visit counting.

## Related work
This sits within a known research thread on specification gaming and reward
hacking: Krakovna et al.'s "Specification gaming examples in AI" catalogs many
real-world instances of this exact failure mode; DeepMind's "AI Safety Gridworlds"
formalized small testbeds for it, including a reward-tampering environment
("tomato watering") with the same core structure used here; and Amodei et al.'s
"Concrete Problems in AI Safety" frames reward hacking as one of the central open
problems in scaling RL safely.

## What's next
- Push the reward-gap detector to its own breaking point: design a cheat that
  earns reward statistically indistinguishable from the honest ceiling (e.g.
  trade off the tamper bonus against a slightly less efficient path so total
  reward lands at or below 0.89) and see whether it goes blind the same way
  visit counting did.
- Close the loop: use the critic's feedback as a training penalty and see whether
  it can suppress the cheating behavior directly, rather than just detecting it
  after the fact.
- Test whether the monitor itself can be evaded by a 4th agent trained
  specifically against its heuristic.
- Move beyond deterministic evaluation (`model.predict(..., deterministic=True)`)
  to get real visit-count and reward distributions instead of single constants,
  so detector thresholds are calibrated against actual variance rather than a
  point estimate.
