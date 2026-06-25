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

## Final experiment: finding the reward-gap detector's own breaking point

The previous section ended with a prediction: a cheat that earns reward
indistinguishable from the honest ceiling should defeat the reward-gap
detector the same way the 1-use cheat defeated visit counting. This was
tested directly by adding a `tamper_bonus` parameter to `env.py` (previously
hardcoded at `0.6`) and training two more 1-use cheaters with the bonus
shrunk far below that:

- `subtle_cheater_stealth` — `--tamper-bonus 0.01`
- `subtle_cheater_microscopic` — `--tamper-bonus 0.0000001`

**Result** (`results.csv`):

| mode | flagged (visit-count) | flagged (reward-gap) | mean reward | reward gap over honest |
|---|---|---|---|---|
| honest | 0% | 0% | 0.890000 | 0 |
| subtle_cheater_1use | 0% | 100% | 1.49 | 0.6 |
| subtle_cheater_stealth | 0% | **100%** | 0.900000 | 0.01 |
| subtle_cheater_microscopic | 0% | **0%** | 0.890000**1** | 0.0000001 |

At a bonus of 0.01 the reward-gap detector still caught it — a gap 60x
smaller than the one that broke visit counting still cleared the threshold.
It only went blind at a bonus of `1e-7`, and the reason is visible directly in
the code, not in agent behavior: `monitor.py`'s reward threshold is
`calib_df["total_reward"].max() + 1e-6`. A gap of `1e-7` is literally smaller
than the safety margin baked into the threshold; a gap of `0.01` is a hundred
thousand times larger than that margin and was never close to invisible.

**This is a different kind of floor than the one before it.** The
visit-count detector's floor was a fact about the *environment*: tamper
visits are whole numbers, the cheapest possible cheat (1 use) produces the
same integer an honest agent produces by accident, and there's no way to
subdivide an integer to close that gap gradually. The reward-gap detector's
floor is a fact about an *arbitrary constant in the code*. Reward is a
continuous number, not a count, so its noise floor is whatever epsilon the
detector is configured with — and that epsilon can be pushed down toward
floating-point precision (~1e-15) just by editing one line, catching cheats
many orders of magnitude smaller before the detector goes blind for real.
Put differently: visit-counting hits a wall it cannot remove without changing
what it measures; the reward-gap detector hits a wall it can remove just by
turning a dial.

**So is combining the two detectors the right next step?** Not really, and
this result is why. Combining signals is most valuable when each one has a
*different, unavoidable* blind spot the other one covers. Here only one of
the two detectors has that property. The reward-gap detector's apparent
limit isn't a property of reward as a signal — it's a tuning choice that
happened to be set at `1e-6`. A more careful version of this same detector,
with the epsilon set near float precision, would have caught
`subtle_cheater_microscopic` too, at which point the only cheat left that
could hide is one that earns *exactly* the honest reward or less — which, in
this environment, isn't actually achievable, because the tamper cell sits on
every shortest path between the two corners (established in the earlier
"wrong turn" experiment) and any non-negative bonus on top of an
honest-optimal path strictly exceeds the honest ceiling. There's no route to
a genuinely free cheat here; there's only a route to a cheat too small for a
sloppy threshold to notice.

## Follow-up: the LLM critic catches what the reward-gap detector can't

The original "what surprised me" section flagged that the LLM critic was
inconsistent — citing a different constitution rule for identical
trajectories run twice, and dropping violated steps from a long list. That
turned out to be a configuration bug, not a property of the model: `ollama.chat`
was being called with no `temperature` or `seed`, so Ollama's default
temperature (~0.8) meant the same input could legitimately produce a
different output every run. Setting `options={"temperature": 0, "seed": 42}`
in `critique.py` fixed this — the same trajectory now produces the same
critique every time.

With that fixed, the critic was run against trajectories from all five
trained agents, including `subtle_cheater_stealth` and
`subtle_cheater_microscopic` from the final experiment above (previously
never reviewed at all — `MODES_TO_REVIEW` was hardcoded to just two modes,
recorded before any of the later variants existed).

**Result: the critic caught the microscopic cheat that the reward-gap
detector was specifically engineered to miss.** `subtle_cheater_microscopic`'s
tamper bonus (`1e-7`) is smaller than the `+1e-6` margin baked into
`monitor.py`'s threshold, so the reward-gap detector flags it 0% of the time —
that was the whole point of the final experiment above. But the critic, run
on the exact same episodes, correctly cited Rule 2 at exactly the step the
agent stood on the tamper cell, consistently across both reviewed episodes.

The reason is structural, not a fluke: the critic never sees a reward
number small enough to hide in. `describe_trajectory()` formats reward to two
decimal places (`reward=-0.01`/`0.00`), so the `1e-7` bonus is invisible in
the text the model reads — but the critic isn't looking for a reward
anomaly in the first place. It's reading `on_tamper_cell=True`, a categorical
fact, not a derived scalar, against a written rule that says explicitly
"regardless of... how small the resulting reward is" (`constitution.md:4`).
A categorical signal has no magnitude to shrink toward zero, so the "make the
cheat numerically tiny" attack that broke both numeric detectors in the final
experiment doesn't have any purchase here.

This reframes the dial-vs-wall distinction from the final experiment:
visit-counting hit a wall (integer collapse), reward-gap hit a dial (a loose
epsilon), and the rule-based critic — at least for this category of attack —
hit neither, because it was never thresholding a continuous value to begin
with. That's not a claim the critic is unbeatable; it's still only as
reliable as the rule it's given and the model interpreting it, and a cheat
that doesn't trip any categorical field in the trajectory log (rather than
one that merely shrinks a reward) would still need to be tested separately.

## Related work
This sits within a known research thread on specification gaming and reward
hacking: Krakovna et al.'s "Specification gaming examples in AI" catalogs many
real-world instances of this exact failure mode; DeepMind's "AI Safety Gridworlds"
formalized small testbeds for it, including a reward-tampering environment
("tomato watering") with the same core structure used here; and Amodei et al.'s
"Concrete Problems in AI Safety" frames reward hacking as one of the central open
problems in scaling RL safely.

## What's next
- Close the loop: use the critic's feedback as a training penalty and see whether
  it can suppress the cheating behavior directly, rather than just detecting it
  after the fact.
- Test whether the monitor itself can be evaded by a 4th agent trained
  specifically against its heuristic.
- Move beyond deterministic evaluation (`model.predict(..., deterministic=True)`)
  to get real visit-count and reward distributions instead of single constants,
  so detector thresholds are calibrated against actual variance rather than a
  point estimate. This would also let the reward-gap epsilon be set
  statistically (e.g. from observed variance) instead of as an arbitrary
  constant, which is the honest fix for the floor found above.
