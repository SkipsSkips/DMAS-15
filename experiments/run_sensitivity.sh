#!/usr/bin/env bash
# Runs every experiment in experiments/sensitivity.xml, one table per experiment.
# Usage: experiments/run_sensitivity.sh "/path/to/NetLogo 7.0.4"
set -euo pipefail
NL="${1:?path to the NetLogo 7.0.4 folder}"
cd "$(dirname "$0")/.."
python3 experiments/make_sensitivity.py
mkdir -p results/v3/sensitivity
python3 - <<'PY' > /tmp/sensitivity-names.txt
import re; print("\n".join(re.findall(r'<experiment name="([^"]+)"', open("experiments/sensitivity.xml").read())))
PY
while IFS= read -r name; do
  out="results/v3/sensitivity/$(echo "$name" | tr '|=' '__').csv"
  [ -s "$out" ] && continue
  echo "$(date +%T) $name"
  java -Xmx4g -cp "$NL/lib/app/*" org.nlogo.headless.Main --model octoplus-v3.nlogox \
    --setup-file experiments/sensitivity.xml --experiment "$name" --table "$out" --threads 2 > /dev/null
done < /tmp/sensitivity-names.txt
