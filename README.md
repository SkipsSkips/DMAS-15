# Hide or Flee?

DMAS group 15, University of Groningen.

A NetLogo model of octopuses on a reef. When a predator shows up, each octopus follows one policy: stay still, hide, flee, move to better cover, or an adaptive mix. We test which policy gives the largest and most stable population, how this depends on the amount and arrangement of cover, and whether a social alarm between octopuses helps.

The report is in `report/main.tex`.

## Files

```
octoplus-v3.nlogox      the model, with the Interface and BehaviorSpace experiments
src/                    model code, loaded by the .nlogox file
docs/PARAMETERS.md      all parameter values
experiments/            sensitivity runs
results/v3/             raw output of all runs
analysis/               statistics, figures and tables
report/                 LNCS report
```

## Run the model

1. Install NetLogo 7.0.4 and open `octoplus-v3.nlogox`.
2. Pick the cover amount, the arrangement and the policy, then press `setup` and `go`.
3. To check the model, type `run-self-test` in the Command Center. It should print `RESULT: PASS`.

## Reproduce the results

You need NetLogo 7.0.4 and Python 3 with NumPy, SciPy, pandas and Matplotlib.

```
java -Xmx4g -cp "NetLogo 7.0.4/lib/app/*" org.nlogo.headless.Main \
  --model octoplus-v3.nlogox --experiment environment-sweep \
  --table results/v3/environment-sweep.csv --threads 2

java -Xmx4g -cp "NetLogo 7.0.4/lib/app/*" org.nlogo.headless.Main \
  --model octoplus-v3.nlogox --experiment social-alarm \
  --table results/v3/social-alarm.csv --threads 2

experiments/run_sensitivity.sh "<path to NetLogo 7.0.4>"

python3 analysis/v3_analysis.py
python3 analysis/v3_tables.py
```

The two main experiments take about 6 minutes each and the sensitivity runs about 40 minutes.

To build the report, upload `report/` to Overleaf with Springer's LNCS template, or run `pdflatex main && bibtex main && pdflatex main && pdflatex main` with `llncs.cls` and `splncs04.bst` next to `main.tex`.
