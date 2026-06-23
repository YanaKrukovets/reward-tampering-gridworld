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

## Related work
This sits within a known research thread on specification gaming and reward
hacking: Krakovna et al.'s "Specification gaming examples in AI" catalogs many
real-world instances of this exact failure mode; DeepMind's "AI Safety Gridworlds"
formalized small testbeds for it, including a reward-tampering environment
("tomato watering") with the same core structure used here; and Amodei et al.'s
"Concrete Problems in AI Safety" frames reward hacking as one of the central open
problems in scaling RL safely.

## What's next
- Find the actual detection boundary: shrink the tamper budget to 1 use, or move
  the tamper cell off the agent's natural path, to find where this monitor's
  detection rate starts to degrade rather than staying at 100%.
- Close the loop: use the critic's feedback as a training penalty and see whether
  it can suppress the cheating behavior directly, rather than just detecting it
  after the fact.
- Test whether the monitor itself can be evaded by a 4th agent trained
  specifically against its heuristic.
