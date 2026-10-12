#!/usr/bin/env bash
# Restore committed data snapshots into data/raw/ (decisions.md D15), so a fresh container does not
# need hours of re-scraping. Run from the repo root, then (optionally) resume unfinished downloads.
set -euo pipefail
mkdir -p data/raw/telegram/air_alert_ua data/raw/telegram/kpszsu data/raw/telegram/UkraineAlarmSignal data/processed
gunzip -c data/telegram/war_monitor.jsonl.gz > data/raw/telegram/war_monitor.jsonl
for i in 0 1 2 3; do gunzip -c data/telegram/air_alert_ua_part$i.jsonl.gz > data/raw/telegram/air_alert_ua/part$i.jsonl; done
for ch in kpszsu UkraineAlarmSignal; do
  for f in data/telegram/${ch}_part*.jsonl.gz; do i=${f##*_part}; i=${i%%.jsonl.gz}; gunzip -c "$f" > data/raw/telegram/$ch/part$i.jsonl; done
done
cp data/labels/official_labels.parquet data/processed/
echo "restored. Next: python scripts/download_data.py --pin, then the build scripts (see Project-State.md)."
