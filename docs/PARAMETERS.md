# Parameters

All values used by `octoplus-v3.nlogox`. Interface controls can be changed in NetLogo. The other values are set in `set-model-constants` in `src/parameters.nls`.

Scale: 1 patch = 1 m and 1 tick = 1 s. The world is 51 x 51 m and a run of 2000 ticks lasts about 33 minutes.

Type of each value:

- **Measured**: taken from studies of octopuses or reef fish.
- **Plausible**: fits the biology, but not measured in this form.
- **Choice**: our own modelling decision.
- **Calibration**: tuned so the model behaves sensibly.

## Interface controls

| Parameter | Default | Meaning | Type |
|---|---|---|---|
| `initial-octopuses` | 40 | octopuses at the start | Plausible |
| `initial-predators` | 3 | predators | Choice |
| `experiment-duration` | 2000 | run length in ticks (500 on the Interface) | Choice |
| `experiment-seed` | 1 | random seed, same seed gives the same run | |
| `prey-speed-setting` | 0.6 | jet speed in m/s (Huffard 2006) | Measured |
| `predator-speed-setting` | 0.8 | chase speed in m/s | Plausible |
| `predator-detection-radius-setting` | 10 | how far a predator sees an octopus on sand, in m | Plausible |
| `cover-amount-category` | medium | low, medium or high (mean cover 0.15, 0.45, 0.75) | Choice |
| `cover-arrangement` | patchy | uniform, or patchy with 15 reef clusters | Choice |
| `octopus-strategy-mode` | adaptive-dmas | still, hide, flee, seek-cover, adaptive-dmas or experimental-assigned (mixed) | |
| `enable-reproduction?` | on | octopuses can give birth | |
| `birth-chance` | 0.005 | chance per second that a foraging octopus gives birth | Calibration |
| `social-alarm?` | off | a jetting neighbour within `alarm-radius` alarms a foraging octopus | Choice |

## Detection

A predator sees an octopus on a patch with cover `c` when they are closer than

```
radius = 10 m x (1 - 0.8 c) x (1 - 0.85 c if hiding) x (1.5 if moving)
```

| Cover | Still | Hiding | Moving |
|---|---|---|---|
| 0 (sand) | 10.0 m | 10.0 m | 15.0 m |
| 0.15 | 8.8 m | 7.7 m | 13.2 m |
| 0.45 | 6.4 m | 4.0 m | 9.6 m |
| 0.75 | 4.0 m | 1.5 m | 6.0 m |

| Constant | Value | Meaning | Type |
|---|---|---|---|
| `cover-impact-strength` | 0.8 | how much cover hides any octopus (Scharf et al. 2006) | Choice |
| `hide-detection-multiplier` | 0.15 | camouflage is 1 minus this, so 0.85 (Hanlon et al. 2009) | Choice |
| `motion-detection-multiplier` | 1.5 | a moving octopus is seen from further away (Merilaita et al. 2017) | Choice |
| `trait-variation` | 0 | random spread in octopus traits, not used in our experiments | Choice |

## Octopuses

| Constant | Value | Meaning | Type |
|---|---|---|---|
| `crawl-speed` | 0.09 | crawling speed in m/s (Huffard 2006) | Measured |
| `forage-pause-chance` | 0.25 | share of foraging time spent still (Leite et al. 2009) | Measured |
| `home-range-radius` | 10 | octopuses stay within 10 m of home (Papadopoulo et al. 2024) | Measured |
| `open-ground-weight` | 0.1 | how much foragers avoid bare sand (lower is stronger) | Calibration |
| `threat-awareness-radius` | 10 | an octopus notices a predator within 10 m | Plausible |
| `prey-reaction-time-setting` | 2 | seconds a calm octopus stops to assess a threat | Choice |
| `calm-down-time` | 20 | seconds an octopus stays alarmed after losing sight of the predator | Choice |
| `max-jet-time` | 5 | seconds of jetting before it must stop, about 3 m (Wells et al. 1987) | Measured |
| `jet-recovery-rate` | 0.1 | jet time regained per second, so 50 s from empty to full | Choice |
| `seek-cover-radius` | 5 | how far seek-cover looks for better cover, in m | Choice |
| `minimum-cover-target` | 0.6 | cover must be at least this dense to move to it | Choice |
| `minimum-cover-improvement` | 0.10 | adaptive only moves if the new patch is this much better | Choice |
| `alarm-radius` | 5 | distance in m at which a jetting neighbour raises the alarm | Choice |

## Predators

| Constant | Value | Meaning | Type |
|---|---|---|---|
| `predator-search-speed-factor` | 0.5 | search speed is half the chase speed, so 0.4 m/s | Plausible |
| `predator-wander-angle` | 15 | maximum turn in degrees per second while searching | Choice |
| `capture-distance` | 0.5 | a predator catches an octopus within 0.5 m | Plausible |
| `handling-time` | 20 | seconds a predator eats after a catch | Calibration |

The handling time keeps kill rates in check. Our predators still catch about 109 octopuses per hour, while a real grouper hunting alone catches about 0.04 prey per hour (Bshary et al. 2006). With 10 s most low-cover populations died out, and with 30 s the policy hardly mattered.

## World and reproduction

| Constant | Value | Meaning | Type |
|---|---|---|---|
| `cover-target-low`, `-medium`, `-high` | 0.15, 0.45, 0.75 | mean cover per amount | Choice |
| `uniform-cover-noise` | 0.035 | noise in the uniform world | Choice |
| `patchy-background-noise` | 0.025 | noise on the sand in the patchy world | Choice |
| `reef-cluster-count`, `reef-cluster-radius` | 15, 3 m | reef clusters in the patchy world | Plausible |
| `cluster-base-strength`, `cluster-random-strength` | 0.30, 0.70 | cover strength of the clusters | Choice |
| `carrying-capacity` | 250 | births stop as the population nears this number | Calibration |
| `offspring-mutation-fraction` | 0.5 | only used when `trait-variation` is above 0 | Choice |

After the world is made, all cover is rescaled so the mean always matches the target. This way uniform and patchy worlds have the same amount of cover.

Only foraging octopuses can give birth, with chance `birth-chance x (1 - N / carrying-capacity)` per second. Newborns appear on a random patch and get their parent's policy.

Full references are in `report/references.bib`.
