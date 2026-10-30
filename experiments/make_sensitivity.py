"""Write experiments/sensitivity.xml: one-at-a-time sweeps of the "Choice" constants.

The constants live in src/parameters.nls, which BehaviorSpace cannot vary. Each
experiment therefore runs `setup` and then overrides one constant. Overriding after
setup uses no random numbers, so every run starts from the same world as the
default run with the same seed.

Run:  python3 experiments/make_sensitivity.py
      java -Xmx4g -cp "NetLogo 7.0.4/lib/app/*" org.nlogo.headless.Main \
        --model octoplus-v3.nlogox --setup-file experiments/sensitivity.xml \
        --table results/v3/sensitivity.csv --threads 2
"""
from pathlib import Path

POLICIES = ["experimental-assigned", "adaptive-dmas", "still", "hide", "flee", "seek-cover"]
ENVIRONMENTS = [("low", "uniform"), ("medium", "patchy")]
SEEDS = (1, 10)

# (label, NetLogo commands run after setup, social-alarm?)
CASES = [("default", "", False)]
for v in (0.05, 0.30):  # default 0.15
    CASES.append((f"hide-detection-multiplier={v}",
                  f"set hide-detection-multiplier {v} "
                  f"ask octopuses [ set camouflage 1 - hide-detection-multiplier ]", False))
for v in (1.0, 2.0):  # default 1.5
    CASES.append((f"motion-detection-multiplier={v}", f"set motion-detection-multiplier {v}", False))
for v in (10, 40):  # default 20
    CASES.append((f"calm-down-time={v}", f"set calm-down-time {v}", False))
for v in (10, 30):  # default 20
    CASES.append((f"handling-time={v}", f"set handling-time {v}", False))
for v in (2.5, 5, 10):  # default 5, only used with social alarm on
    CASES.append((f"alarm-radius={v}", f"set alarm-radius {v}", True))

METRICS = ["count octopuses", "extinction-time", "late-mean-population", "late-population-cv",
           "total-births", "total-captures", 'time-share "forage"']


def q(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def values(var, vals, quoted=False):
    v = "".join(f'<value value="{q(chr(34) + x + chr(34)) if quoted else x}"></value>' for x in vals)
    return f'<enumeratedValueSet variable="{var}">{v}</enumeratedValueSet>'


def experiment(label, commands, alarm, cover, arrangement):
    setup = "setup" + (" " + commands if commands else "")
    return (
        f'<experiment name="{q(label)}|{cover}|{arrangement}" repetitions="1" sequentialRunOrder="true" '
        f'runMetricsEveryStep="false" timeLimit="2000">'
        f"<setup>{q(setup)}</setup><go>go</go><exitCondition>run-complete?</exitCondition>"
        f"<metrics>{''.join(f'<metric>{q(m)}</metric>' for m in METRICS)}</metrics><constants>"
        + values("octopus-strategy-mode", POLICIES, quoted=True)
        + values("cover-amount-category", [cover], quoted=True)
        + values("cover-arrangement", [arrangement], quoted=True)
        + f'<steppedValueSet variable="experiment-seed" first="{SEEDS[0]}" step="1" last="{SEEDS[1]}"></steppedValueSet>'
        + values("experiment-duration", ["2000"]) + values("initial-octopuses", ["40"])
        + values("initial-predators", ["3"]) + values("prey-speed-setting", ["0.6"])
        + values("predator-speed-setting", ["0.8"]) + values("predator-detection-radius-setting", ["10"])
        + values("enable-reproduction?", ["true"]) + values("birth-chance", ["0.005"])
        + values("social-alarm?", ["true" if alarm else "false"])
        + "</constants></experiment>"
    )


xml = "<experiments>" + "".join(
    experiment(label, cmd, alarm, c, a) for label, cmd, alarm in CASES for c, a in ENVIRONMENTS
) + "</experiments>"
out = Path(__file__).with_name("sensitivity.xml")
out.write_text(xml)
print(f"{out}: {len(CASES) * len(ENVIRONMENTS)} experiments, "
      f"{len(CASES) * len(ENVIRONMENTS) * len(POLICIES) * (SEEDS[1] - SEEDS[0] + 1)} runs")
