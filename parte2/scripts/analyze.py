#!/usr/bin/env python3
"""Estatísticas e gráficos de rodadas completas confirmadas no journal."""
import csv
import io
import json
import math
import os
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from scipy.stats import t
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(os.environ.get("T1_RESULT_ROOT", Path(__file__).resolve().parents[1]))
KEY = ["network", "operation", "size_bytes", "clients"]


def readcsv(p):
	return list(csv.DictReader(io.StringIO(Path(p).read_text())))


def selected_rows():
	committed = {}
	for line in (ROOT / "evidencias/rodadas_concluidas.jsonl").read_text().splitlines():
		try:
			r = json.loads(line)
			committed[r["round_id"]] = r["attempt"]
		except json.JSONDecodeError:
			pass
	grouped = defaultdict(list)
	for r in readcsv(ROOT / "resultados_brutos.csv"):
		if r.get("phase") == "main":
			grouped[(r["round_id"], r["attempt"])].append(r)
	accepted = []
	excluded = []
	for (rid, attempt), part in grouped.items():
		try:
			n = int(part[0]["clients"])
			valid = (
				committed.get(rid) == attempt
				and len(part) == n
				and {int(r["client_id"]) for r in part} == set(range(1, n + 1))
			)
		except (ValueError, TypeError):
			valid = False
		(accepted if valid else excluded).extend(part)
	return accepted, excluded


def avg_ci(values):
	x = np.asarray(values, dtype=float)
	n = len(x)
	if not n:
		return (math.nan,) * 3
	mean = float(x.mean())
	if n < 2:
		return mean, math.nan, math.nan
	half = float(t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n))
	return mean, mean - half, mean + half


def analyze(rows):
	groups = defaultdict(list)
	planned = Counter()
	for r in rows:
		groups[tuple(r[k] for k in KEY)].append(r)
	for r in readcsv(ROOT / "matriz_experimental.csv"):
		planned[tuple(r[k] for k in KEY)] += 1
	result = []
	rng = np.random.default_rng(20261105)
	for key, planned_n in sorted(
		planned.items(), key=lambda p: (p[0][0], p[0][1], int(p[0][2]), int(p[0][3]))
	):
		group = groups[key]
		byround = defaultdict(list)
		for r in group:
			byround[r["round_id"]].append(r)
		ok = [r for r in group if r["status"] == "ok"]
		nr = len(byround)
		out = dict(zip(KEY, key))
		out.update(
			planned_rounds=planned_n,
			completed_rounds=nr,
			observations=len(group),
			successes=len(ok),
			failures=len(group) - len(ok),
			success_rate=len(ok) / len(group) if group else "",
			failure_rate=(len(group) - len(ok)) / len(group) if group else "",
			completion="complete" if nr == planned_n else "pending",
		)
		for metric in ["duration_s", "throughput_mbps"]:
			vals = [float(r[metric]) for r in ok]
			clusters = [
				np.asarray([float(r[metric]) for r in part if r["status"] == "ok"])
				for part in byround.values()
				if any(r["status"] == "ok" for r in part)
			]
			means = [float(v.mean()) for v in clusters]
			mean, lo, hi = avg_ci(means)
			out.update(
				{
					metric + "_mean": mean,
					metric + "_median": float(np.median(vals)) if vals else math.nan,
					metric + "_std_clients": float(np.std(vals, ddof=1))
					if len(vals) > 1
					else math.nan,
					metric + "_std_round_means": float(np.std(means, ddof=1))
					if len(means) > 1
					else math.nan,
					metric + "_ci95_low": lo,
					metric + "_ci95_high": hi,
				}
			)
			ml = mh = math.nan
			if len(clusters) > 1:
				boot = [
					np.median(
						np.concatenate(
							[clusters[i] for i in rng.integers(len(clusters), size=len(clusters))]
						)
					)
					for _ in range(3000)
				]
				ml, mh = np.quantile(boot, [0.025, 0.975])
			out[metric + "_median_ci95_low"] = float(ml)
			out[metric + "_median_ci95_high"] = float(mh)
		ag = [
			float(part[0]["aggregate_mbps"])
			for part in byround.values()
			if all(r["status"] == "ok" for r in part)
		]
		mean, lo, hi = avg_ci(ag)
		out.update(
			aggregate_mbps_mean=mean,
			aggregate_mbps_ci95_low=lo,
			aggregate_mbps_ci95_high=hi,
			round_success_rate=sum(
				all(r["status"] == "ok" for r in part) for part in byround.values()
			)
			/ nr
			if nr
			else "",
			round_failure_rate=sum(
				any(r["status"] != "ok" for r in part) for part in byround.values()
			)
			/ nr
			if nr
			else "",
			launch_skew_ms_max=max((float(r["launch_skew_ms"]) for r in group), default=math.nan),
		)
		result.append(out)
	with (ROOT / "resultados_resumidos.csv").open("w", newline="") as f:
		w = csv.DictWriter(f, list(result[0]))
		w.writeheader()
		w.writerows(result)
	return result


def plots(rows, summary):
	out = ROOT / "graficos"
	out.mkdir(exist_ok=True)
	plt.rcParams.update({"font.size": 12, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 180})
	sizes = [32768, 262144, 1048576, 4194304]
	labels = ["32 KiB", "256 KiB", "1 MiB", "4 MiB"]
	colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]

	def save(fig, name):
		fig.tight_layout()
		fig.savefig(out / f"{name}.png")
		fig.savefig(out / f"{name}.pdf")
		plt.close(fig)

	for metric, title, ylabel in [
		("duration_s", "Tempo de resposta", "Tempo (s)"),
		("throughput_mbps", "Vazao por cliente", "Vazao util (Mbps)"),
		("aggregate_mbps", "Vazao agregada por rodada", "Vazao util agregada (Mbps)"),
	]:
		fig, axs = plt.subplots(2, 2, figsize=(11, 8))
		for i, net in enumerate(["A", "B"]):
			for j, op in enumerate(["GET", "PUT"]):
				ax = axs[i, j]
				for size, label, color in zip(sizes, labels, colors):
					sub = sorted(
						[
							r
							for r in summary
							if r["network"] == net
							and r["operation"] == op
							and int(r["size_bytes"]) == size
							and r["completed_rounds"]
						],
						key=lambda r: int(r["clients"]),
					)
					if not sub:
						continue
					y = np.array([r[metric + "_mean"] for r in sub])
					lo = np.array([r[metric + "_ci95_low"] for r in sub])
					hi = np.array([r[metric + "_ci95_high"] for r in sub])
					err = np.maximum(0, np.nan_to_num(np.array([y - lo, hi - y]), nan=0))
					ax.errorbar(
						[int(r["clients"]) for r in sub],
						y,
						yerr=err,
						color=color,
						marker="o",
						capsize=3,
						label=label,
					)
				ax.set(
					title=f"Perfil {net} - {op}",
					xlabel="Clientes simultaneos",
					ylabel=ylabel,
					xticks=[1, 4, 8],
				)
				ax.legend(fontsize=9)
		fig.suptitle(title + " (IC 95% entre rodadas)")
		save(fig, metric)
	fig, axs = plt.subplots(2, 2, figsize=(11, 8))
	for i, net in enumerate(["A", "B"]):
		for j, op in enumerate(["GET", "PUT"]):
			data = [
				[
					float(r["duration_s"])
					for r in rows
					if r["status"] == "ok"
					and r["network"] == net
					and r["operation"] == op
					and int(r["size_bytes"]) == 4194304
					and int(r["clients"]) == n
				]
				for n in [1, 4, 8]
			]
			if all(data):
				axs[i, j].boxplot(data, labels=["1", "4", "8"], showmeans=True)
			axs[i, j].set(
				title=f"Perfil {net} - {op} - 4 MiB",
				xlabel="Clientes simultaneos",
				ylabel="Tempo (s)",
			)
	fig.suptitle("Distribuicao descritiva das observacoes individuais")
	save(fig, "distribuicao")
	fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
	for ax, op in zip(axs, ["GET", "PUT"]):
		for net in ["A", "B"]:
			for n in [1, 8]:
				data = sorted(
					float(r["duration_s"])
					for r in rows
					if r["status"] == "ok"
					and r["network"] == net
					and r["operation"] == op
					and int(r["size_bytes"]) == 4194304
					and int(r["clients"]) == n
				)
				if data:
					ax.step(
						data,
						np.arange(1, len(data) + 1) / len(data),
						where="post",
						label=f"{net}, N={n}",
					)
		ax.set(title=f"{op} - 4 MiB", xlabel="Tempo (s)", ylabel="CDF empirica", ylim=(0, 1.02))
		ax.legend(fontsize=9)
	save(fig, "cdf")


def main():
	rows, excluded = selected_rows()
	summary = analyze(rows)
	plots(rows, summary)
	report = dict(
		planned_rounds=528,
		completed_rounds=len({r["round_id"] for r in rows}),
		observations=len(rows),
		successes=sum(r["status"] == "ok" for r in rows),
		statuses=dict(Counter(r["status"] for r in rows)),
		excluded_rows=len(excluded),
		complete_configs=sum(r["completion"] == "complete" for r in summary),
		max_launch_skew_ms=max(float(r["launch_skew_ms"]) for r in rows),
		min_concurrent_overlap_ms=min(
			float(r["overlap_ms"]) for r in rows if int(r["clients"]) > 1
		),
	)
	(ROOT / "evidencias/analise_integridade.json").write_text(json.dumps(report, indent=2))
	print(json.dumps(report, indent=2))


if __name__ == "__main__":
	main()
