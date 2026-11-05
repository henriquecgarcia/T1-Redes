#!/usr/bin/env python3
import csv
import itertools
import random
from pathlib import Path

root = Path(__file__).resolve().parents[1]
fields = [
	"round_id",
	"network",
	"bandwidth_mbps",
	"one_way_delay_ms",
	"operation",
	"size_bytes",
	"clients",
	"repetition",
]
rng = random.Random(20261105)
rows = []
for rep in range(1, 12):
	configs = list(
		itertools.product(["A", "B"], ["GET", "PUT"], [32768, 262144, 1048576, 4194304], [1, 4, 8])
	)
	rng.shuffle(configs)
	for net, op, size, n in configs:
		rows.append(
			dict(
				zip(
					fields,
					[
						f"r{len(rows)+1:04}",
						net,
						100 if net == "A" else 20,
						5 if net == "A" else 30,
						op,
						size,
						n,
						rep,
					],
				)
			)
		)
with (root / "matriz_experimental.csv").open("w", newline="") as f:
	w = csv.DictWriter(f, fieldnames=fields)
	w.writeheader()
	w.writerows(rows)
print(f'{len(rows)} rounds; {sum(int(r["clients"]) for r in rows)} client observations')
