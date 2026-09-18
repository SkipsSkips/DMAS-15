# Iteration 1 — what we built, what broke, and why

Presentation notes for the first part of the DMAS project.

This document is the thought process rather than the result. It follows the
model through its first version, the problems that version exposed, and the
changes those problems forced. The numbers quoted are from real runs; where a
result turned out to be wrong, it is left in.

---

## 1. The question

> Under which conditions is it better for an autonomous prey agent to stay
> still, hide using environmental cover, or flee from a predator?

A cephalopod is the motivating image — an octopus can either match its
background or jet away — but the model is abstract. Nothing in it is a
measurement of a real animal.

The multi-agent framing matters: each prey agent should decide for itself,
from what it can see locally, with no central controller. That is the part
that makes this a DMAS project rather than a differential equation.

---

## 2. Version 1: `octoplus-v1.nlogox`

The first model is small on purpose. About 290 lines.

**Agents.** Octopuses and predators on a 51×51 wrapping grid.

**Environment.** Every patch has a `cover-density` from 0 to 1. Two settings:
cover spread evenly, or cover concentrated into twelve reef-like clumps.

**Prey.** One strategy for the whole population, chosen from a dropdown:

| Strategy | Behaviour |
|---|---|
| `still` | do nothing |
| `hide` | press into whatever cover is on the current patch |
| `flee` | if a predator is within 10 patches, run directly away |

**Predators.** Wander at random. If any prey is visible, chase the nearest one
and capture it within 0.5 patches.

**Detection.** A predator has a detection radius, and three things change it:

```
effective radius = detection radius
                 × (1 − cover × cover-effect)     cover shrinks it
                 × 0.3  if the prey is hiding     hiding shrinks it further
                 × 1.5  if the prey is moving     moving stretches it
```

The `0.3` and `1.5` were picked by hand to be roughly plausible. That is
honest but not defensible, and it is still the weakest part of the model.

**Output.** Three monitors and one population plot.

### What version 1 got right

It ran, and it produced the ordering we expected. One run each, 300 ticks,
uniform cover:

| Strategy | Survival |
|---|---|
| flee | 67.5% |
| hide | 50.0% |
| still | 5.0% |

Doing nothing is close to fatal, and that sanity check mattered: it told us the
predators worked, the detection equation did something, and the strategies were
actually distinguishable.

---

## 3. Four things version 1 could not do

### 3.1 One run is one sample

The model is random — the environment, the starting positions, and the
predators' wandering are all random. A single run is one draw from a
distribution, and the table above is three draws. It is not evidence.

We had no way to fix this in version 1 because there was **no random seed
control**, so we could not even repeat a run, let alone repeat it under matched
conditions.

### 3.2 The environments were not comparable

This is the one that changed how we think about the whole project. Version 1
has a `cover-amount` slider and a `patchy-cover?` switch, and we assumed the
switch changed the *arrangement* of cover. Reading the model's own monitor:

| Environment | Mean cover on the map |
|---|---|
| uniform, `cover-amount` 0.45 | **0.450** |
| patchy, `cover-amount` 0.45 | **0.124** |

The patchy environment had **72% less cover in total**. So when hiding did
worse in the patchy world, we could not say whether that was because the cover
was *clumped* or because there was *less of it*. Two variables were riding on
one switch.

Any conclusion about spatial arrangement from version 1 is uninterpretable.
Not wrong — uninterpretable, which is worse.

### 3.3 The prey were not really agents

One dropdown set the strategy for all forty octopuses. That is a population
parameter, not a decision. There was no per-agent choice, nothing depended on
what an individual could see, and so nothing in version 1 was actually
multi-agent decision making. It was three fixed behaviours being compared.

### 3.4 There was no observation window

`go` ran until the prey were extinct. "Survival" therefore meant "survival at
whatever moment we happened to stop watching", which is not a measurement.

---

## 4. What we changed, and why

Each change traces back to one of the four problems above.

| Problem | Change |
|---|---|
| One run is one sample | A seed slider, and a BehaviorSpace design that runs every condition across 30 seeds |
| Environments not comparable | `normalize-cover-to-target`: generate the spatial pattern, then rescale every patch so the realised mean hits its target. Amount and arrangement become independent variables |
| Prey not really agents | An adaptive policy: each octopus scores hiding against fleeing from its own local cover and its own distance to the nearest predator, and picks for itself |
| No observation window | A fixed run length, with survival measured at a defined tick |

The normalisation is the change we are most confident about, and it is worth a
slide on its own. It is what makes a *negative* result meaningful: if
arrangement turns out not to matter, that now means something, because we know
amount was held constant. In version 1 the same finding would have meant
nothing.

We also added reproduction, so that a population can persist rather than only
decline, and `seek-cover` as a fourth action — move toward better cover, then
hide — because hiding in place seemed like an unfairly weak version of hiding.

---

## 5. First real result, and the mistake in it

With the second version we ran the full design: 4 strategies × 3 cover amounts
× 3 arrangements × 3 prey speeds × 3 predator speeds × 30 seeds = **9,720
runs**, about 25 minutes.

| Strategy | Survival | 95% CI |
|---|---|---|
| flee | 67.3% | 65.9 – 68.6 |
| adaptive | 43.7% | 42.2 – 45.2 |
| hide | 20.5% | 19.7 – 21.4 |
| still | 4.3% | 4.0 – 4.6 |

Two findings came straight out of it:

- **Cover arrangement explains essentially nothing** once amount is controlled
  (ω² = −0.0002). The normalisation is what lets us say that.
- **Hiding never beat fleeing** — in any of the 27 speed × cover combinations,
  by margins of 35 to 54 survival points.

We wrote that second one down as "fleeing dominates". It was wrong, and the
reason is instructive.

The design samples prey speed from {0.4, 0.6, 0.8} and predator speed from
{0.6, 0.8, 1.0}. The highest predator-to-prey speed ratio it can reach is
1.0 / 0.4 = **2.5**. So we widened the sweep, 0.2 to 1.4 on both sides:

| Predator/prey speed ratio | Hide advantage |
|---|---|
| 2.0 | −21.6 |
| 2.5 | −9.1 |
| **3.0** | **+0.9** ← crossover |
| 4.0 | +8.1 |

**The boundary is at a ratio of 3.0 — one step outside our own design.**
Hiding wins exactly when prey are too slow for fleeing to work. Our factorial
could not have found that, and we only found it because the "no boundary"
result looked too clean to trust.

---

## 6. Two bugs that changed conclusions

Both were found by writing automated checks for things we thought were
obviously true.

**Ageing counted the wrong thing.** Prey age advanced inside the reproduction
routine, which is skipped while a prey is in its reaction delay. So `age`
counted *ticks not spent reacting*, not ticks lived, and maturity arrived later
for prey in dangerous environments than in calm ones. The check that caught it:
after *n* ticks, every living founder must have been alive for exactly *n*
ticks.

**One strategy could not reproduce at all.** The reproduction routine contained:

```netlogo
if active-strategy = "flee" [ stop ]
```

The intent was "a prey busy escaping does not breed", which is fine for an
adaptive prey that flees occasionally. But a prey on the fixed `flee` policy is
fleeing on *every tick of its life*, so it could never breed. Across 135
reproduction-enabled runs it produced **zero** births.

The effect on the result was not small:

| | before fix | after fix |
|---|---|---|
| flee, final population | 14.4 | **250.0** (carrying capacity) |
| adaptive, final population | 148.3 | 138.7 |

Before the fix, the obvious conclusion was "the adaptive policy dominates once
reproduction is enabled". The truth is the opposite: fleeing saturates the
carrying capacity in every single run. A plausible-looking guard clause had
become a structural constraint on one experimental arm.

---

## 7. Where this leaves the adaptive policy

Honestly: it does not work well yet. It survives 43.7% against fleeing's 67.3%.

It is not that it ignores the environment — it clearly reads it. Its share of
time spent hiding correlates **+0.81** with how much cover there actually is,
and its share spent fleeing correlates **−0.73**. The direction is right.

The problem is calibration. It spends about **74% of every run standing still**,
in every condition, and standing still is the worst available action almost
everywhere. One threshold, `minimum-decision-score`, routes an agent to "still"
whenever neither hiding nor fleeing scores above it — and that threshold is
firing far too often.

One thing it does do better than anything else: it has the **lowest extinction
rate** and the **longest median time to extinction**. It hedges against the
population collapsing entirely, even though it loses more individuals along the
way. Those are different objectives, and we had not separated them.

---

## 8. Next steps

1. **Fix the adaptive policy's calibration.** Lower
   `minimum-decision-score`, and make the hide and flee scores commensurable
   quantities rather than two separately invented 0-to-1 numbers.
2. **Test `seek-cover` as a strategy in its own right.** It is one of the four
   actions and the adaptive policy picks it on 0.7% of ticks, so we currently
   know nothing about it.
3. **Justify the detection equation.** The hide-versus-flee answer turns on
   parameters we chose by hand. This is the biggest threat to the whole study.
4. **Give the predator memory.** It currently wanders without ever returning to
   where it found prey, which is part of why fleeing is so strong: a memoryless
   searcher struggles to reacquire anything that moves.

---

## What we would tell someone starting this project

Three things, in order of how much time they would have saved us:

1. **Check that your experimental conditions differ only in the variable you
   named.** Our patchy environment had 72% less cover than our uniform one. We
   found that by reading a monitor, not by thinking about it.
2. **Write tests for the things you are sure of.** Both bugs were in code that
   looked obviously correct, and both changed conclusions. Neither would have
   been caught by watching the animation.
3. **When a result looks unusually clean, suspect the design before believing
   it.** "Hiding never wins" was clean, and it was an artefact of a range we
   chose ourselves.
