# Hide or Flee? Adaptive Predator–Prey Multi-Agent Simulation

A NetLogo multi-agent simulation investigating when prey should:

- remain still;
- hide using environmental cover;
- flee from a predator; or
- move toward better cover before hiding.

The model is inspired by cephalopod camouflage, but it is an abstract computational model rather than a biologically complete simulation of octopus behavior.

## Research question

> Under which environmental and predator–prey conditions is it better for an autonomous prey agent to stay still, hide, flee, or seek nearby cover?

The visual animation helps explain the model, but the main contribution is the controlled experimental comparison of prey strategies across quantified environmental conditions.

---

## Contents

1. [Project overview](#project-overview)
2. [Research objectives](#research-objectives)
3. [Model entities](#model-entities)
4. [Environment](#environment)
5. [Prey strategies](#prey-strategies)
6. [Adaptive decision model](#adaptive-decision-model)
7. [Predator behavior](#predator-behavior)
8. [Detection model](#detection-model)
9. [Reaction delay](#reaction-delay)
10. [Capture rule](#capture-rule)
11. [Model parameters](#model-parameters)
12. [Metrics](#metrics)
13. [Running the model](#running-the-model)
14. [Recommended Interface controls](#recommended-interface-controls)
15. [Experimental design](#experimental-design)
16. [BehaviorSpace configuration](#behaviorspace-configuration)
17. [Interpreting results](#interpreting-results)
18. [Hypotheses](#hypotheses)
19. [Important experimental cautions](#important-experimental-cautions)
20. [Assumptions and limitations](#assumptions-and-limitations)
21. [Implemented functionality](#implemented-functionality)
22. [Future work](#future-work)
23. [Suggested report structure](#suggested-report-structure)

---

# Project overview

The model contains autonomous prey agents and predator agents in a spatial environment.

Each patch has a continuous environmental cover value. Prey can use this cover to reduce their probability of being detected. Predators search the world, detect visible prey, and pursue the nearest detected target.

The model supports fixed prey policies and an adaptive policy.

The fixed policies provide experimental baselines:

- always stay still;
- always hide;
- always flee.

The adaptive policy uses local information to decide whether to:

- stay still;
- hide immediately;
- flee;
- or seek better cover.

The purpose is not to prove that one strategy is universally superior. The purpose is to identify the conditions under which the relative advantage of each strategy changes.

---

# Research objectives

The model is intended to answer questions such as:

1. Does hiding outperform fleeing when environmental cover is abundant?
2. How much usable cover must exist before hiding becomes effective?
3. Does the spatial arrangement of cover matter independently of total cover?
4. Is patchy cover better or worse than uniformly distributed cover?
5. When does seeking cover become too dangerous?
6. How does predator speed affect the hide-versus-flee boundary?
7. How does prey speed affect the same boundary?
8. Does movement-related visibility make fleeing ineffective in some conditions?
9. Does the adaptive strategy outperform fixed strategies?
10. Does the adaptive strategy make decisions appropriate to its environment?
11. How much longer do prey survive even when all prey are eventually captured?
12. Are results robust across repeated random seeds?

These questions must be answered using repeated experiments and numerical results, not by observing one visually interesting run.

---

# Model entities

## Prey: octopuses

Each octopus has:

- a fixed policy;
- a currently active strategy;
- a previous counted strategy;
- an individual movement speed;
- a reaction timer;
- a reacting state;
- a hidden state;
- a moving state;
- local access to environmental cover;
- local awareness of nearby predators.

Prey decisions are decentralized. There is no central controller choosing actions for the whole population.

Each adaptive prey independently observes its local situation and selects an action.

## Predators

Each predator has:

- a base detection radius;
- movement speed;
- a current target;
- a search state;
- a pursuit state.

Predators search by wandering through the environment. When one or more prey are detected, a predator selects the nearest visible prey and moves toward it.

## Patches

Each patch has:

```text
cover-density
```

`cover-density` is a continuous value in the range:

```text
0.0 to 1.0
```

Interpretation:

| Cover value | Interpretation |
|---:|---|
| `0.0` | No environmental cover |
| `0.25` | Weak cover |
| `0.50` | Moderate cover |
| `0.75` | Strong cover |
| `1.0` | Maximum modeled cover |

Cover is an abstract combination of environmental properties that could help conceal an animal, such as:

- rocks;
- reef structures;
- vegetation;
- shadows;
- visual texture;
- background matching opportunities.

It is not intended to represent a specific physical measurement.

---

# Environment

Two independent settings define an environment:

1. **cover amount**;
2. **cover arrangement**.

Separating these properties is important.

If a patchy environment always contains more total cover than a uniform environment, it is impossible to know whether differences in survival were caused by:

- the amount of cover; or
- its spatial arrangement.

The improved model therefore treats them as separate experimental variables.

## Cover amount categories

The `cover-amount-category` setting determines the target mean cover.

| Category | Target mean cover |
|---|---:|
| `"low"` | `0.15` |
| `"medium"` | `0.45` |
| `"high"` | `0.75` |

The realized value is available through:

```netlogo
average-world-cover
```

and:

```netlogo
realized-cover-mean
```

Small differences can arise from numeric operations, but the environment generation procedure normalizes cover toward the selected target.

## Cover arrangements

The `cover-arrangement` setting supports:

| Arrangement | Description |
|---|---|
| `"uniform"` | Cover is distributed relatively evenly across patches |
| `"patchy"` | Cover is concentrated into spatial clusters |
| `"mixed"` | Background cover is combined with stronger clusters |

### Uniform

Uniform environments contain only small local variations around the target mean.

A medium-uniform environment should therefore have approximately the same total cover as a medium-patchy environment, but its cover is distributed more evenly.

### Patchy

Patchy environments begin with very low background cover. Cover is then added around randomly selected cluster centers.

Cover strength decreases with distance from the center of each cluster.

This creates:

- high-cover hiding locations;
- low-cover open spaces;
- travel costs between cover patches;
- differences in accessibility.

### Mixed

Mixed environments combine:

- moderate background cover;
- stronger local clusters.

They represent an intermediate condition between uniform and strongly patchy environments.

## Environment normalization

After the initial pattern is generated, patch values are adjusted toward the selected target mean.

When the current mean is below the target, patches are proportionally moved toward `1`.

When the current mean is above the target, values are proportionally scaled toward `0`.

This preserves the broad spatial pattern while allowing arrangements with approximately comparable mean cover.

All final values are constrained to:

```text
0 <= cover-density <= 1
```

---

# Prey strategies

## Still

A still prey:

- does not move;
- does not receive the movement detection penalty;
- is not treated as actively camouflaged;
- remains vulnerable according to local environmental cover.

This is a useful baseline because it separates the effect of avoiding movement from the additional effect of hiding.

Model state:

```text
is-moving? = false
is-hidden? = false
```

## Hide

A hiding prey:

- remains stationary;
- attempts to use local environmental cover;
- receives a cover-dependent camouflage benefit;
- does not receive the movement detection penalty.

Model state:

```text
is-moving? = false
is-hidden? = true
```

Hiding does not automatically work in open water. Its effectiveness increases continuously with local cover.

## Flee

A fleeing prey:

- turns away from the nearest predator;
- moves at its prey speed;
- does not receive the hiding benefit;
- receives the movement detection modifier.

Model state:

```text
is-moving? = true
is-hidden? = false
```

Fleeing can increase distance from the predator, but movement can also make prey easier to detect.

## Seek cover

A prey seeking cover:

- identifies the strongest nearby cover patch;
- checks whether the patch offers a meaningful cover improvement;
- estimates whether it can reach that patch before the predator;
- moves toward it when the target appears useful and reachable;
- hides after reaching sufficiently strong cover.

Seeking cover is best interpreted as a **transitional action**, not necessarily as a primary fixed-strategy baseline.

It combines two risks:

1. movement temporarily increases detectability;
2. the prey may not reach cover before the predator arrives.

## Fixed and adaptive policies

The model supports the following values for `octopus-strategy-mode`:

| Value | Meaning |
|---|---|
| `"still"` | All prey remain still |
| `"hide"` | All prey attempt to hide |
| `"flee"` | All prey flee when their action is executed |
| `"seek-cover"` | All prey attempt to move toward better cover |
| `"adaptive-dmas"` | Each prey selects an action from local information |
| `"experimental-assigned"` | Each prey is randomly assigned a fixed strategy |

The main experimental comparison should use:

- `"still"`;
- `"hide"`;
- `"flee"`;
- `"adaptive-dmas"`.

The `"experimental-assigned"` mode is useful for demonstrations of heterogeneous populations, but it is not as easy to interpret as separate controlled baseline runs.

---

# Adaptive decision model

The adaptive policy uses only local information available to each prey.

It does not know:

- the global strategy distribution;
- future predator movements;
- future capture outcomes;
- which strategy will produce the best experimental result.

The policy follows these general steps:

1. Find the nearest predator.
2. Stay still if there is no predator within the awareness radius.
3. Flee if the predator is critically close.
4. Evaluate the value of hiding locally.
5. Evaluate the value of fleeing.
6. Evaluate whether stronger nearby cover is useful and reachable.
7. Seek cover if its projected hiding value exceeds the immediate alternatives.
8. Otherwise choose the greater of the hide and flee scores.
9. Stay still if both scores are negligible.

## Threat awareness

A predator is considered relevant when:

```text
distance to predator <= threat-awareness-radius
```

If no predator is in this range, an adaptive prey selects `"still"`.

## Emergency flee rule

If:

```text
distance to predator <= critical-threat-distance
```

the adaptive prey immediately selects `"flee"`.

This emergency rule is evaluated before the normal score comparison.

## Threat urgency

Threat urgency is:

```text
urgency =
    1 - predator distance / threat awareness radius
```

The result is constrained to the range `0` to `1`.

Interpretation:

| Urgency | Meaning |
|---:|---|
| `0` | Predator is at or beyond the awareness boundary |
| `0.5` | Predator is halfway through the awareness range |
| `1` | Predator is at the prey’s location |

## Hide score

The hide score is based on:

- candidate cover;
- modeled camouflage strength;
- threat urgency.

Conceptually:

```text
hide score =
    cover
    × camouflage strength
    × reaction safety
```

Camouflage strength is:

```text
1 - hide-detection-multiplier
```

Reaction safety is:

```text
1 - 0.35 × threat urgency
```

The score is constrained to the range `0` to `1`.

Hiding becomes more attractive when:

- cover is strong;
- the configured hiding multiplier represents effective camouflage;
- the predator has not already reached critical distance.

The emergency flee rule separately handles extremely close threats.

## Flee score

The flee score is based on:

- threat urgency;
- prey speed relative to predator speed.

Conceptually:

```text
flee score =
    threat urgency
    × relative prey speed
```

Relative speed is:

```text
prey speed / predator speed
```

and is constrained to the range `0` to `1` for scoring.

Fleeing becomes more attractive when:

- the threat is closer;
- prey speed is competitive with predator speed.

## Minimum decision score

If both hide and flee scores are below:

```text
minimum-decision-score
```

the adaptive prey stays still.

This prevents very weak score differences from forcing unnecessary movement or hiding actions.

## Cover target selection

The prey searches patches within:

```text
seek-cover-radius
```

It selects the patch with the greatest `cover-density`.

The target is useful only if:

```text
target cover >= minimum-cover-target
```

and:

```text
target cover >= local cover + minimum-cover-improvement
```

This prevents prey from moving toward a patch that is only trivially better than its current location.

## Cover reachability estimate

The model estimates travel time as:

```text
distance to target cover / prey speed
```

Estimated predator arrival time is:

```text
distance to predator / predator speed
```

The target is considered reachable when:

```text
travel time < estimated predator arrival time
```

This is deliberately a simple local estimate. It is not a complete prediction of future movement, obstacles, or predator strategy.

---

# Predator behavior

Predators have two main states.

## Search

When no prey is detected, a predator:

- has no target;
- randomly changes heading;
- moves at a fraction of its normal speed.

Search movement is:

```text
predator speed × predator-search-speed-factor
```

The random turning range is controlled by:

```text
predator-wander-angle
```

## Pursuit

When prey are visible, a predator:

1. selects the nearest visible prey;
2. faces that prey;
3. moves toward it;
4. captures it if the capture-distance condition is satisfied.

If the previously selected target is no longer visible, the predator can select another visible prey or return to searching.

---

# Detection model

Detection is represented through an effective predator detection radius.

The general equation is:

```text
effective detection radius =
    base predator detection radius
    × environmental cover modifier
    × hiding modifier
    × movement modifier
```

A prey is detected when:

```text
distance to predator <= effective detection radius
```

## Environmental cover modifier

The environmental cover modifier is:

```text
1 - local cover × cover-impact-strength
```

It is constrained to remain nonnegative.

As local cover increases, detection radius decreases.

For example, with:

```text
cover-impact-strength = 0.8
```

the environmental modifier is approximately:

| Local cover | Cover modifier |
|---:|---:|
| `0.00` | `1.00` |
| `0.25` | `0.80` |
| `0.50` | `0.60` |
| `0.75` | `0.40` |
| `1.00` | `0.20` |

## Hiding modifier

If the prey is not hiding:

```text
hiding modifier = 1
```

If the prey is hiding:

```text
hiding modifier =
    1 - local cover × (1 - hide-detection-multiplier)
```

This corrects an important problem in the original prototype.

Hiding now provides no additional benefit when cover is zero. Its maximum benefit is only reached when cover is `1`.

With:

```text
hide-detection-multiplier = 0.15
```

the approximate modifiers are:

| Local cover | Hiding modifier |
|---:|---:|
| `0.00` | `1.0000` |
| `0.25` | `0.7875` |
| `0.50` | `0.5750` |
| `0.75` | `0.3625` |
| `1.00` | `0.1500` |

This means hiding in an open environment is not automatically effective.

## Movement modifier

If the prey is not moving:

```text
movement modifier = 1
```

If the prey is moving:

```text
movement modifier = motion-detection-multiplier
```

The default is:

```text
motion-detection-multiplier = 1.5
```

Movement therefore increases the effective detection radius by 50% under the default configuration.

## Example calculation

Suppose:

```text
base detection radius = 10
local cover = 0.50
cover impact strength = 0.80
hide detection multiplier = 0.15
```

The environmental modifier is:

```text
1 - 0.50 × 0.80 = 0.60
```

For a hiding prey, the hiding modifier is:

```text
1 - 0.50 × (1 - 0.15) = 0.575
```

The effective radius is:

```text
10 × 0.60 × 0.575 × 1 = 3.45
```

For a moving prey with a movement multiplier of `1.5`, the effective radius is:

```text
10 × 0.60 × 1 × 1.5 = 9
```

This demonstrates the central trade-off:

- hiding can reduce detection;
- fleeing can increase distance;
- movement can also increase visibility.

---

# Reaction delay

Prey do not necessarily act immediately after detecting a relevant threat.

The delay is controlled by:

```text
prey-reaction-time-setting
```

While reacting, a prey:

- does not move;
- is not hidden;
- displays the `"WAIT"` state when labels are enabled.

When no threat is present, its reaction timer resets.

Reaction delay should be included in experiments because it can change whether hiding, fleeing, or seeking cover is viable.

---

# Capture rule

A predator captures its selected prey when:

```text
distance to target <= capture-distance
```

When capture occurs:

- the prey is removed from the model;
- `total-captures` increases;
- the current tick is added to `capture-ticks`;
- `first-capture-tick` is updated if this is the first capture;
- `last-capture-tick` is updated.

---

# Model parameters

## Population parameters

| Parameter | Default | Description |
|---|---:|---|
| `initial-octopuses` | `40` | Number of prey created during setup |
| `initial-predators` | `3` | Number of predators created during setup |

## Movement and detection parameters

| Parameter | Default | Description |
|---|---:|---|
| `predator-detection-radius-setting` | `10` | Base predator detection radius in patch-distance units |
| `predator-speed-setting` | `0.8` | Predator movement distance per tick |
| `prey-speed-setting` | `0.6` | Prey movement distance per tick |
| `prey-reaction-time-setting` | `2` | Number of reaction-delay ticks |
| `capture-distance` | `0.5` | Distance at which a predator captures prey |

## Predator search parameters

| Parameter | Default | Description |
|---|---:|---|
| `predator-wander-angle` | `15` | Maximum random search turn in degrees |
| `predator-search-speed-factor` | `0.5` | Search speed as a fraction of normal predator speed |

## Adaptive decision parameters

| Parameter | Default | Description |
|---|---:|---|
| `threat-awareness-radius` | `10` | Distance within which a predator affects adaptive decisions |
| `hide-cover-threshold` | `0.55` | Cover required for a patch to count as usable hiding cover in environmental metrics |
| `critical-threat-distance` | `3` | Distance that activates emergency fleeing |
| `seek-cover-radius` | `5` | Radius searched for a better cover patch |
| `minimum-cover-target` | `0.60` | Minimum cover required for a useful target |
| `minimum-cover-improvement` | `0.10` | Required improvement over current cover |
| `minimum-decision-score` | `0.08` | Score below which prey remain still |

## Detection parameters

| Parameter | Default | Description |
|---|---:|---|
| `cover-impact-strength` | `0.8` | Strength of environmental cover’s effect on detection |
| `hide-detection-multiplier` | `0.15` | Maximum hiding multiplier reached at cover `1` |
| `motion-detection-multiplier` | `1.5` | Detection multiplier applied to moving prey |

## Environment parameters

| Parameter | Default | Description |
|---|---|---|
| `cover-amount-category` | `"medium"` | Selected target cover category |
| `cover-arrangement` | `"patchy"` | Selected spatial cover arrangement |
| `reef-cluster-count` | `15` | Number of cover cluster centers |
| `reef-cluster-radius` | `3` | Radius of each cover cluster |

## Experiment parameters

| Parameter | Default | Description |
|---|---:|---|
| `experiment-duration` | `500` | Maximum duration of a run in ticks |
| `experiment-seed` | `1` | Random seed applied before environment and agent creation |
| `octopus-strategy-mode` | `"adaptive-dmas"` | Population policy used in the run |

## Display parameters

| Parameter | Default | Description |
|---|---:|---|
| `show-predator-radii?` | `true` | Shows predator perception rings |
| `show-state-labels?` | `true` | Shows agent state labels |

---

# Metrics

The model provides both final-outcome and process metrics.

A strong analysis should not rely on only one metric.

## Survival rate

```netlogo
survival-rate
```

Calculated as:

```text
100 × surviving prey / initial prey
```

A high value means more prey remain alive at the observation time.

Use survival at a fixed tick, such as tick 500, when comparing treatments.

## Capture rate

```netlogo
capture-rate
```

Calculated as:

```text
100 × total captures / initial prey
```

## Total captures

```netlogo
total-captures
```

The total number of prey captured during the run.

## Cumulative survival

```netlogo
cumulative-survival
```

After each simulation step, the current number of surviving prey is added to this value.

Its units are approximately:

```text
octopus-ticks
```

This distinguishes runs that end with the same final survival rate but have different survival histories.

For example, two treatments may both end with zero survivors, but the treatment with greater cumulative survival kept prey alive for longer.

## Mean survival-time contribution

```netlogo
mean-survival-time-contribution
```

Calculated as:

```text
cumulative survival / initial prey
```

This gives an average survival contribution per original prey.

## Pursuit events

```netlogo
pursuit-events
```

A pursuit event is counted when a predator begins pursuing a different target.

## Detection events

```netlogo
detection-events
```

A detection event is counted when a searching predator with no target acquires visible prey.

This avoids simply counting every visible prey on every tick.

It is still a model-specific event definition and must be reported exactly this way in any analysis.

## Predator capture efficiency

```netlogo
predator-capture-efficiency
```

Calculated as:

```text
100 × total captures / pursuit events
```

This represents captures relative to pursuit-target acquisitions.

It should not be interpreted as a biological probability without further validation.

## Capture-time metrics

Available reporters:

```netlogo
mean-capture-tick
median-capture-tick
```

Available variables:

```netlogo
first-capture-tick
last-capture-tick
```

A value of `-1` means no capture has occurred.

These metrics help distinguish between:

- immediate capture;
- delayed capture;
- complete survival.

## Strategy transition counts

Available counters:

```netlogo
hide-decisions
flee-decisions
still-decisions
seek-cover-decisions
```

These count transitions into a strategy.

An octopus that remains hidden for 20 ticks contributes one hide transition, not 20 separate hide decisions.

This avoids overcounting sustained states.

## Decision proportions

Available reporters:

```netlogo
hide-decision-proportion
flee-decision-proportion
still-decision-proportion
seek-cover-decision-proportion
```

Each is calculated as:

```text
strategy transitions / total strategy transitions
```

These are particularly useful for testing whether adaptive agents respond to their environments.

For example:

- does the hide proportion increase as cover increases?
- does the flee proportion increase as predator speed increases?
- does seek-cover occur more frequently in patchy environments?

## Current-state counts

Available reporters:

```netlogo
hidden-octopus-count
moving-octopus-count
reacting-octopus-count
hide-strategy-count
flee-strategy-count
still-strategy-count
seek-cover-strategy-count
```

These report the current state of surviving prey.

They are useful for live plots, but they are not substitutes for cumulative decision counts because captured prey no longer appear in current-state counts.

## Average world cover

```netlogo
average-world-cover
```

The mean cover value across all patches.

This reports the realized numeric cover level rather than relying only on category names.

## Average cover usage

```netlogo
average-cover-usage
```

The mean cover value occupied by currently surviving prey.

## Relative cover use

```netlogo
relative-cover-use
```

Calculated as:

```text
average prey cover / average world cover
```

Interpretation:

| Result | Interpretation |
|---:|---|
| `< 1` | Prey occupy lower-cover areas than the world average |
| `≈ 1` | Prey use cover approximately in proportion to availability |
| `> 1` | Prey disproportionately occupy stronger cover |

Because this is calculated from surviving prey, survivorship bias should be considered.

## Cover availability

```netlogo
cover-availability
```

The proportion of patches where:

```text
cover-density >= hide-cover-threshold
```

The result is in the range `0` to `1`.

The percentage version is:

```netlogo
cover-availability-percent
```

This metric can be more informative than mean cover because it measures how much of the world qualifies as usable hiding habitat.

## Cover variation

```netlogo
cover-variation
```

The standard deviation of patch cover.

Interpretation:

- low variation indicates relatively uniform cover;
- high variation indicates environmental heterogeneity;
- environments can have the same mean cover but different variation.

## Mean distance to usable cover

```netlogo
mean-distance-to-usable-cover
```

This reports the mean distance from every patch to its nearest patch where:

```text
cover-density >= hide-cover-threshold
```

A result of `-1` means no patch qualifies as usable cover.

This metric measures the accessibility of hiding habitat.

## Predator/prey speed ratio

```netlogo
predator-prey-speed-ratio
```

Calculated as:

```text
predator speed / prey speed
```

Interpretation:

| Ratio | Meaning |
|---:|---|
| `< 1` | Prey are faster |
| `1` | Speeds are equal |
| `> 1` | Predators are faster |

This ratio is useful for plotting strategy performance across relative movement capabilities.

## Run completion

```netlogo
run-complete?
```

A run is complete when:

```text
ticks >= experiment-duration
```

or no prey remain alive.

---

# Running the model

## Requirements

- NetLogo `7.0.4`
- The model file `octoplus.nlogox`

## Basic procedure

1. Open `octoplus.nlogox` in NetLogo.
2. Open the Code tab.
3. Click **Check** to verify the code.
4. Click **setup**.
5. Click **go**.
6. Allow the model to run until:
   - `experiment-duration` is reached; or
   - all prey are captured.

## Important initialization note

The model uses `startup` to assign defaults when the model opens.

The `setup` procedure does not reset valid experimental parameter values. This allows Interface controls and BehaviorSpace to change settings before setup.

If the model was already open while new code was pasted, either:

- reopen the model; or
- run the following once from the Command Center:

```netlogo
set-default-parameters
```

Then run:

```netlogo
setup
```

## Command Center example

To create a low-cover, uniform, always-hide treatment:

```netlogo
set cover-amount-category "low"
set cover-arrangement "uniform"
set octopus-strategy-mode "hide"
set experiment-seed 1
setup
```

Then run `go`.

To compare fleeing under the same generated initial conditions:

```netlogo
set cover-amount-category "low"
set cover-arrangement "uniform"
set octopus-strategy-mode "flee"
set experiment-seed 1
setup
```

Using the same seed and setup parameters recreates the same initial random environment and agent positions.

Agent behavior may diverge after setup because each strategy causes different subsequent actions and random-number use.

## Inspecting outputs

After a run, useful commands include:

```netlogo
show survival-rate
show capture-rate
show total-captures
show cumulative-survival
show mean-survival-time-contribution
show mean-capture-tick
show median-capture-tick
show first-capture-tick
show last-capture-tick
```

Environment outputs:

```netlogo
show average-world-cover
show cover-availability
show cover-variation
show mean-distance-to-usable-cover
show average-cover-usage
show relative-cover-use
```

Decision outputs:

```netlogo
show hide-decisions
show flee-decisions
show still-decisions
show seek-cover-decisions
show hide-decision-proportion
show flee-decision-proportion
```

---

# Recommended Interface controls

The core model can be controlled from the Command Center, but adding Interface widgets makes experiments easier.

Because `.nlogox` stores its Interface as XML, widgets should preferably be added through the NetLogo Interface editor rather than by manually editing raw XML.

## Recommended choosers

### Cover amount

Global variable:

```text
cover-amount-category
```

Choices:

```text
"low"
"medium"
"high"
```

### Cover arrangement

Global variable:

```text
cover-arrangement
```

Choices:

```text
"uniform"
"patchy"
"mixed"
```

### Strategy

Global variable:

```text
octopus-strategy-mode
```

Choices:

```text
"still"
"hide"
"flee"
"adaptive-dmas"
"seek-cover"
"experimental-assigned"
```

## Recommended sliders

| Global | Minimum | Maximum | Increment | Default |
|---|---:|---:|---:|---:|
| `initial-octopuses` | 1 | 100 | 1 | 40 |
| `initial-predators` | 0 | 10 | 1 | 3 |
| `predator-speed-setting` | 0 | 2 | 0.1 | 0.8 |
| `prey-speed-setting` | 0 | 2 | 0.1 | 0.6 |
| `predator-detection-radius-setting` | 1 | 20 | 1 | 10 |
| `prey-reaction-time-setting` | 0 | 10 | 1 | 2 |
| `critical-threat-distance` | 0 | 10 | 0.5 | 3 |
| `seek-cover-radius` | 1 | 15 | 1 | 5 |
| `cover-impact-strength` | 0 | 1 | 0.05 | 0.8 |
| `hide-detection-multiplier` | 0 | 1 | 0.05 | 0.15 |
| `motion-detection-multiplier` | 1 | 3 | 0.1 | 1.5 |
| `experiment-duration` | 100 | 2000 | 100 | 500 |
| `experiment-seed` | 1 | 10000 | 1 | 1 |

## Recommended switches

```text
show-predator-radii?
show-state-labels?
```

## Recommended monitors

Add monitors for:

```text
ticks
count octopuses
survival-rate
total-captures
cumulative-survival
mean-capture-tick
average-world-cover
cover-availability-percent
cover-variation
relative-cover-use
hide-decision-proportion
flee-decision-proportion
```

## Recommended plot

Plot name:

```text
Prey Population by Active Strategy
```

Pens:

```text
Hide
Flee
Still
Seek Cover
Total
```

The code safely ignores missing plots, so the model can still run before this plot is created.

---

# Experimental design

## Main principle

Do not determine whether a strategy is effective by watching one run.

The simulation is stochastic because it includes:

- random environment generation;
- random agent placement;
- predator wandering;
- random boundary-turning behavior;
- agent execution ordering.

Every experimental condition must therefore be repeated across multiple seeds.

## Primary independent variables

### Strategy

```text
still
hide
flee
adaptive-dmas
```

### Cover amount

```text
low
medium
high
```

### Cover arrangement

```text
uniform
patchy
mixed
```

### Prey speed

Suggested values:

```text
0.4
0.6
0.8
```

### Predator speed

Suggested values:

```text
0.6
0.8
1.0
```

## Initial factorial design

A full design could include:

```text
4 strategies
× 3 cover amounts
× 3 cover arrangements
× 3 prey speeds
× 3 predator speeds
× 30 seeds
```

This gives:

```text
9,720 runs
```

That is suitable for BehaviorSpace but may be excessive for an initial test.

## Recommended staged design

### Stage 1: strategy and cover amount

Hold speed constant:

```text
prey speed = 0.6
predator speed = 0.8
```

Test:

```text
4 strategies
× 3 cover amounts
× 2 arrangements
× 30 seeds
```

Use uniform and patchy arrangements first.

This produces:

```text
720 runs
```

### Stage 2: spatial arrangement

Hold cover amount constant at medium:

```text
cover amount = medium
```

Test uniform, patchy, and mixed arrangements.

This isolates whether spatial arrangement changes performance when mean cover is comparable.

### Stage 3: speed ratio

Test:

```text
prey speed = 0.4, 0.6, 0.8
predator speed = 0.6, 0.8, 1.0
```

Compare results using:

```netlogo
predator-prey-speed-ratio
```

### Stage 4: sensitivity analysis

Vary:

- `hide-detection-multiplier`;
- `cover-impact-strength`;
- `motion-detection-multiplier`;
- `critical-threat-distance`;
- `prey-reaction-time-setting`.

This determines whether conclusions depend excessively on one arbitrary parameter.

---

# BehaviorSpace configuration

A BehaviorSpace experiment should use:

## Setup command

```netlogo
setup
```

## Go command

```netlogo
go
```

## Stop condition

```netlogo
run-complete?
```

Alternatively, set the time limit to:

```text
500 steps
```

and use:

```netlogo
experiment-duration = 500
```

## Suggested variables

### Strategy

```netlogo
["still" "hide" "flee" "adaptive-dmas"]
```

### Cover amount

```netlogo
["low" "medium" "high"]
```

### Cover arrangement

Initial experiment:

```netlogo
["uniform" "patchy"]
```

Expanded experiment:

```netlogo
["uniform" "patchy" "mixed"]
```

### Prey speed

```netlogo
[0.4 0.6 0.8]
```

### Predator speed

```netlogo
[0.6 0.8 1.0]
```

### Seeds

Use explicit seeds so treatments can be matched.

For example:

```text
1 through 30
```

Set:

```text
experiment-seed
```

as the varied seed parameter.

Do not rely only on the BehaviorSpace repetition option if matched seeds across strategy conditions are required. Explicitly varying `experiment-seed` makes the seed visible in exported results.

## Recommended metrics

Record:

```netlogo
ticks
experiment-seed
count octopuses
survival-rate
capture-rate
total-captures
cumulative-survival
mean-survival-time-contribution
mean-capture-tick
median-capture-tick
first-capture-tick
last-capture-tick
detection-events
pursuit-events
predator-capture-efficiency
average-world-cover
cover-availability
cover-variation
mean-distance-to-usable-cover
average-cover-usage
relative-cover-use
predator-prey-speed-ratio
hide-decisions
flee-decisions
still-decisions
seek-cover-decisions
hide-decision-proportion
flee-decision-proportion
still-decision-proportion
seek-cover-decision-proportion
```

## Fixed settings for the first experiment

Recommended initial constants:

```text
initial octopuses = 40
initial predators = 3
detection radius = 10
reaction time = 2
capture distance = 0.5
experiment duration = 500
cover impact strength = 0.8
hiding multiplier = 0.15
movement multiplier = 1.5
```

Change one group of parameters at a time.

---

# Interpreting results

## Which strategy is best?

For each experimental condition:

1. Calculate mean survival rate for each fixed strategy.
2. Calculate uncertainty across repeated seeds.
3. Identify the fixed strategy with the greatest mean survival.
4. Compare adaptive survival against the best fixed strategy.
5. Examine cumulative survival and capture time as secondary outcomes.
6. Examine adaptive decision proportions to understand why its result occurred.

Do not compare adaptive behavior only with the average of the fixed strategies. Compare it with the **best fixed strategy available in that condition**.

## Adaptive advantage

Adaptive advantage should be calculated during external analysis because strategies run in separate simulations.

For a condition \(c\):

```text
best fixed survival(c) =
    max(
        mean still survival(c),
        mean hide survival(c),
        mean flee survival(c)
    )
```

Then:

```text
adaptive advantage(c) =
    mean adaptive survival(c)
    - best fixed survival(c)
```

Interpretation:

| Adaptive advantage | Meaning |
|---:|---|
| Positive | Adaptive outperformed the best fixed baseline |
| Approximately zero | Adaptive matched the best fixed baseline |
| Negative | A fixed strategy outperformed adaptive |

This difference should be reported with uncertainty, not as a single unsupported number.

## When is hiding better?

Evidence favoring hiding would include:

- always-hide survival exceeding always-flee survival;
- increased time to capture under hiding;
- positive performance as cover availability increases;
- stronger hiding performance at lower `hide-detection-multiplier` values;
- stronger hiding performance when predators are faster than prey.

A useful comparison is:

```text
hide advantage =
    mean hide survival - mean flee survival
```

Positive values favor hiding.

## When is fleeing better?

Evidence favoring fleeing would include:

- always-flee survival exceeding always-hide survival;
- lower predator/prey speed ratios;
- low cover availability;
- large distances between usable cover patches;
- weak camouflage effectiveness;
- a low movement detection penalty.

## When is staying still better?

Staying still may perform well when:

- movement greatly increases detection;
- hiding provides little benefit because local cover is weak;
- predators are sufficiently distant;
- movement would expose prey without creating enough separation.

The still baseline is important because hiding and immobility should not be treated as the same action.

## When does seeking cover help?

Seeking cover may help when:

- current local cover is weak;
- strong cover exists nearby;
- cover improvement is substantial;
- prey can reach it before the predator;
- the movement detection penalty is not too large.

It may hurt when:

- useful patches are too far away;
- predators are fast;
- prey reaction time is long;
- movement strongly increases detection;
- cover is already adequate locally.

## Interpreting environmental categories

Do not report only that an environment was `"low"`, `"medium"`, or `"high"`.

Also report:

- realized mean cover;
- cover availability;
- cover variation;
- mean distance to usable cover.

For example, two medium-cover environments may both have mean cover near `0.45`, but one could have:

- low variation and moderate cover everywhere;

while the other has:

- high-cover clusters separated by open areas.

Those environments can produce different behavior even though their means are similar.

## Recommended plots

### Strategy survival by cover amount

```text
x-axis: average-world-cover
y-axis: mean survival-rate
line or color: strategy
```

### Strategy survival by arrangement

```text
x-axis: cover arrangement
y-axis: mean survival-rate
group: strategy
```

### Hide versus flee heatmap

```text
x-axis: average-world-cover or cover-availability
y-axis: predator-prey-speed-ratio
cell color: hide survival - flee survival
```

Interpretation:

- positive cells favor hiding;
- negative cells favor fleeing;
- values near zero indicate similar performance.

### Adaptive advantage heatmap

```text
x-axis: cover availability
y-axis: predator-prey-speed-ratio
cell color: adaptive advantage
```

### Adaptive decision response

```text
x-axis: average-world-cover
y-axis: hide-decision-proportion
```

A functioning adaptive policy should generally hide more often as useful cover increases, although the relationship may also depend on predator distance and speed.

### Survival through time

Plot:

```text
tick
against
mean number of surviving prey
```

This can reveal important differences hidden by final survival alone.

---

# Hypotheses

The following are hypotheses to test, not established findings.

## H1: Cover amount

Increasing environmental cover will improve hiding performance more strongly than fleeing performance.

## H2: Open environments

Fleeing will outperform hiding when:

- cover availability is low;
- prey speed is competitive with predator speed;
- movement detection costs are moderate.

## H3: Dense environments

Hiding will outperform fleeing when:

- cover availability is high;
- camouflage is effective;
- predators are faster than prey.

## H4: Spatial arrangement

Patchy and uniform environments with similar mean cover will produce different outcomes because usable hiding patches have different accessibility.

## H5: Seeking cover

Seeking cover will be beneficial when strong cover is nearby, but harmful when useful cover is too distant relative to predator arrival time.

## H6: Adaptive behavior

Adaptive prey will outperform fixed strategies in heterogeneous environments where the best action changes across local situations.

## H7: Uniform conditions

In highly uniform environments, one fixed strategy may match or outperform adaptive behavior because local decisions have less environmental variation to exploit.

## H8: Movement visibility

Increasing `motion-detection-multiplier` will reduce the relative benefit of fleeing.

## H9: Reaction time

Longer prey reaction times will reduce survival, especially when predators begin close to prey.

---

# Important experimental cautions

## Do not use one run as evidence

A single simulation can be affected by:

- favorable initial positions;
- unfavorable initial positions;
- an unusually easy environment;
- predator wandering;
- stochastic action ordering.

Use at least 20–30 seeds per condition.

## Use matched seeds

Use the same seed values for all strategies within a condition.

For example:

```text
seed 1: still, hide, flee, adaptive
seed 2: still, hide, flee, adaptive
...
seed 30: still, hide, flee, adaptive
```

This improves fairness by recreating the same initial environment and initial agent locations across strategy treatments.

## Use a fixed observation period

Compare survival at the same duration, such as:

```text
500 ticks
```

Do not compare one treatment at tick 100 with another at tick 500.

## Report uncertainty

For each condition, report:

- number of runs;
- mean;
- standard deviation;
- confidence interval or another uncertainty measure.

Where possible, inspect the full distribution rather than only the mean.

## Separate hypotheses from findings

Statements such as:

> Hiding should work better in dense cover.

are hypotheses.

Statements such as:

> Hiding produced a mean survival rate 12 percentage points above fleeing in high-cover patchy environments across 30 seeds.

are findings, assuming the experiment actually produced that result.

Do not write predicted results as if they have already been observed.

## Avoid changing too many parameters initially

Begin with a controlled experiment. Add sensitivity analysis only after the primary comparison works.

## Validate the decision equations

The adaptive policy is intentionally transparent, but its score weights are still modeling assumptions.

Test whether conclusions remain stable when changing:

- camouflage strength;
- motion penalty;
- emergency distance;
- minimum decision score;
- reaction delay.

If small changes completely reverse every result, the conclusions may not be robust.

---

# Assumptions and limitations

## Abstract camouflage

The model does not simulate:

- real octopus skin physiology;
- chromatophore control;
- predator visual systems;
- color perception;
- texture perception;
- polarization;
- realistic camouflage pattern generation.

`cover-density` is an abstract environmental value.

## Detection is deterministic

A prey is detected whenever its distance is within the calculated effective radius.

Real detection is probabilistic. A future model could convert effective radius into a detection probability.

## Simple predator behavior

Predators use:

- random search;
- nearest-visible-prey pursuit.

They do not learn, remember hiding locations, cooperate, or anticipate prey movement.

## Simple fleeing behavior

Fleeing prey move directly away from the nearest predator.

They do not evaluate:

- multiple escape routes;
- future boundary positions;
- several predators simultaneously;
- collision avoidance;
- complex terrain.

## Approximate cover reachability

The seek-cover reachability estimate compares simple travel times.

It does not simulate the future trajectories of both agents before making the decision.

## No energy cost

Movement, hiding, searching, and waiting have no explicit energy cost.

## No reproduction or evolution

The model evaluates survival during a run. It does not simulate:

- reproduction;
- inheritance;
- evolution;
- long-term population adaptation.

## Shared parameter values

Most capability values are global settings shared by agents.

Future versions could introduce individual variation in:

- prey speed;
- predator speed;
- detection ability;
- camouflage effectiveness;
- reaction time.

## Toroidal world

The current NetLogo view allows wrapping in both dimensions.

This means that leaving one edge causes an agent to reappear on the opposite edge. The world therefore behaves like a torus rather than a bounded reef.

This avoids hard boundary traps but is not a literal representation of a real habitat.

Any report using the model should state that world wrapping is enabled unless it is deliberately changed.

## Survivorship bias

Metrics such as:

```netlogo
average-cover-usage
```

are calculated using surviving prey.

Captured prey are no longer included, so apparent cover use can partly reflect which prey survived rather than only which cover they originally selected.

Cumulative decision counts help, but a complete individual event history would provide stronger analysis.

## Score assumptions

The adaptive hide and flee scores are transparent rules, not learned optimal policies.

The coefficients and thresholds must be justified as modeling assumptions and tested through sensitivity analysis.

## No universal best strategy

The model should not be used to claim that hiding or fleeing is universally superior.

The intended conclusion is conditional:

```text
Strategy X performed better under conditions Y and Z.
```

---

# Implemented functionality

The improved research prototype includes:

- predator and prey agents;
- decentralized prey decisions;
- predator search and pursuit;
- continuous patch-level environmental cover;
- low, medium, and high target cover categories;
- uniform, patchy, and mixed cover arrangements;
- environment normalization toward comparable mean cover;
- fixed still, hide, flee, and seek-cover policies;
- an adaptive decision policy;
- cover-dependent hiding;
- movement-dependent detection;
- environmental detection reduction;
- reaction delay;
- emergency fleeing;
- local cover search;
- simple cover reachability evaluation;
- fixed experiment duration;
- reproducible random seeds;
- survival and capture metrics;
- cumulative survival;
- capture-time metrics;
- strategy transition counters;
- strategy decision proportions;
- environmental cover metrics;
- current strategy counts;
- optional predator perception rings;
- optional state labels;
- safe live plotting when the expected plot is present.

---

# Future work

Potential improvements include:

## Model validation

- Validate detection equations against relevant literature.
- Justify parameter ranges.
- Test alternate detection formulations.
- Compare deterministic and probabilistic detection.

## Better experimental support

- Add the complete set of Interface controls.
- Add BehaviorSpace experiments directly to the model.
- Add automatic CSV-friendly reporters.
- Add automated tests for environment means and reporter bounds.

## Individual histories

Record per-prey:

- every strategy transition;
- detection time;
- pursuit time;
- capture time;
- cover at decision time;
- predator distance at decision time;
- hide and flee scores.

## Improved adaptive policy

Possible extensions include:

- utility-based decision-making;
- probabilistic choice;
- reinforcement learning;
- memory of previous outcomes;
- limited prediction of predator movement.

These should only be added if they improve the research question rather than adding unnecessary complexity.

## Predator extensions

Useful predator treatments might include:

- random search only;
- search plus pursuit;
- memory-based search;
- multiple detection capabilities.

Avoid adding many predator types without a clear experiment.

## Environmental extensions

Possible environmental improvements include:

- bounded worlds;
- obstacles;
- movement costs through different terrain;
- dynamic cover;
- separate visual cover and physical obstruction;
- controlled patch-size distributions.

## Statistical analysis

Recommended analysis outside NetLogo includes:

- confidence intervals;
- effect sizes;
- paired comparisons using matched seeds;
- regression models;
- survival analysis;
- response-surface plots;
- strategy-boundary heatmaps.

---

# Suggested report structure

## Introduction

Explain:

- predator avoidance;
- camouflage and escape as competing strategies;
- the multi-agent framing;
- the research question.

## Related work

Discuss:

- cephalopod camouflage;
- environmental effects on concealment;
- predator–prey multi-agent systems;
- computational models of avoidance;
- the research gap addressed by comparing hide and flee strategies.

## Model

Describe:

- agents;
- environment;
- local perception;
- prey actions;
- adaptive decision rules;
- predator behavior;
- detection equation;
- capture rule;
- assumptions.

## Experimental design

Describe:

- independent variables;
- fixed strategy baselines;
- adaptive strategy;
- random seeds;
- repeated trials;
- fixed run duration;
- outcome metrics;
- hypotheses.

## Results

Present:

- survival by strategy;
- survival by cover amount;
- survival by cover arrangement;
- effects of predator/prey speed ratio;
- adaptive decision proportions;
- adaptive advantage over the best fixed baseline;
- uncertainty across seeds.

## Discussion

Interpret:

- when hiding was advantageous;
- when fleeing was advantageous;
- when staying still was useful;
- whether seeking cover helped;
- whether adaptive decisions responded appropriately;
- whether findings were robust;
- limitations of the abstraction.

## Conclusion

Return to the central question:

> When should an autonomous prey agent hide, and when should it flee?

The conclusion should describe conditional findings rather than declaring one universally superior strategy.

---

# Project summary

The project can be summarized in one sentence:

> We develop a multi-agent predator–prey simulation in which prey autonomously choose between remaining still, camouflage-based hiding, active escape, and seeking environmental cover, and investigate how quantified cover structure and predator–prey capabilities affect the survival advantage of each strategy.

The animation is the visualization.

The project itself is the controlled experimental study conducted using the model.