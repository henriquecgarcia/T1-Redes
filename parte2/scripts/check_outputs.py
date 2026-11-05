#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(p):
	return list(csv.DictReader(io.StringIO(p.read_text())))


plan = read(ROOT / "matriz_experimental.csv")
rows = read(ROOT / "resultados_brutos.csv")
assert len(plan) == 528 and len({r["round_id"] for r in plan}) == 528
matrix = {r["round_id"]: r for r in plan}
groups = defaultdict(list)
for r in rows:
	c = matrix[r["round_id"]]
	for key in ["network", "operation", "size_bytes", "clients", "repetition"]:
		assert r[key] == c[key]
	assert r["status"] == "ok" and int(r["bytes"]) == int(r["size_bytes"])
	assert r["sha256_expected"] == r["sha256_actual"] and len(r["sha256_actual"]) == 64
	assert float(r["duration_s"]) > 0
	assert math.isclose(
		float(r["throughput_mbps"]),
		int(r["bytes"]) * 8 / float(r["duration_s"]) / 1e6,
		rel_tol=1e-5,
	)
	groups[r["round_id"]].append(r)
assert len(groups) == 528 and len(rows) == 2288
markers = {}
for line in (ROOT / "evidencias/rodadas_concluidas.jsonl").read_text().splitlines():
	m = json.loads(line)
	markers[m["round_id"]] = m
for rid, part in groups.items():
	n = int(matrix[rid]["clients"])
	assert len(part) == n and {int(r["client_id"]) for r in part} == set(range(1, n + 1))
	assert len({r["attempt"] for r in part}) == 1 and part[0]["attempt"] == markers[rid]["attempt"]
	if n > 1:
		assert all(float(r["overlap_ms"]) > 0 for r in part)
counts = Counter((r["network"], r["operation"], r["size_bytes"], r["clients"]) for r in plan)
assert len(counts) == 48 and set(counts.values()) == {11}
original_campaign = groups["r0001"][0]["attempt"] == "ed8393b2ed98"
if original_campaign:
	assert groups["r0002"][0]["attempt"] == "6833dbccb620"
# Tentativas registradas antes da retomada após a segunda rodada.
result = dict(
	rounds=528,
	observations=2288,
	configs=48,
	repetitions=11,
	status="all ok",
	integrity="all SHA-256 match",
	concurrency="all simultaneous intervals overlap",
	resume="original first two attempts appear exactly once"
	if original_campaign
	else "new campaign; original checkpoint not applicable",
)
print(json.dumps(result, indent=2))
