#!/usr/bin/env python3
"""Gera figuras de impressão usando os CSV existentes, sem recalcular a coleta."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "relatorio/figuras"


def read_csv(path):
	with path.open() as stream:
		return list(csv.DictReader(stream))


def save(figure, name):
	figure.tight_layout()
	figure.savefig(OUTPUT / f"{name}.pdf")
	plt.close(figure)


def main():
	OUTPUT.mkdir(exist_ok=True)
	rows = read_csv(ROOT / "parte2/resultados_brutos.csv")
	summary = read_csv(ROOT / "parte2/resultados_resumidos.csv")
	plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.25})
	sizes = [32768, 262144, 1048576, 4194304]
	labels = ["32 KiB", "256 KiB", "1 MiB", "4 MiB"]
	colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]

	for metric, name, ylabel in [
		("duration_s", "tempo_resposta", "Tempo (s)"),
		("throughput_mbps", "vazao_individual", "Vazão útil (Mbps)"),
		("aggregate_mbps", "vazao_agregada", "Vazão agregada (Mbps)"),
	]:
		figure, axes = plt.subplots(2, 2, figsize=(6.2, 4.9))
		for i, network in enumerate(["A", "B"]):
			for j, operation in enumerate(["GET", "PUT"]):
				axis = axes[i, j]
				for size, label, color in zip(sizes, labels, colors):
					group = sorted(
						[
							row
							for row in summary
							if row["network"] == network
							and row["operation"] == operation
							and int(row["size_bytes"]) == size
						],
						key=lambda row: int(row["clients"]),
					)
					mean = np.array([float(row[metric + "_mean"]) for row in group])
					low = np.array([float(row[metric + "_ci95_low"]) for row in group])
					high = np.array([float(row[metric + "_ci95_high"]) for row in group])
					axis.errorbar(
						[int(row["clients"]) for row in group],
						mean,
						yerr=np.array([mean - low, high - mean]),
						color=color,
						marker="o",
						markersize=3,
						capsize=2,
						label=label,
					)
				axis.set(
					title=f"Perfil {network} / {operation}",
					xlabel="Clientes simultâneos",
					ylabel=ylabel,
					xticks=[1, 4, 8],
				)
				axis.legend(fontsize=7.5)
		save(figure, name)

	figure, axes = plt.subplots(2, 2, figsize=(6.2, 4.7))
	for i, network in enumerate(["A", "B"]):
		for j, operation in enumerate(["GET", "PUT"]):
			values = [
				[
					float(row["duration_s"])
					for row in rows
					if row["network"] == network
					and row["operation"] == operation
					and int(row["clients"]) == count
					and int(row["size_bytes"]) == 4194304
				]
				for count in [1, 4, 8]
			]
			axes[i, j].boxplot(values, labels=["1", "4", "8"], showmeans=True)
			axes[i, j].set(
				title=f"Perfil {network} / {operation}",
				xlabel="Clientes simultâneos",
				ylabel="Tempo (s)",
			)
	save(figure, "distribuicao")

	figure, axes = plt.subplots(1, 2, figsize=(6.2, 2.8))
	for axis, operation in zip(axes, ["GET", "PUT"]):
		for network in ["A", "B"]:
			for count in [1, 8]:
				values = sorted(
					float(row["duration_s"])
					for row in rows
					if row["network"] == network
					and row["operation"] == operation
					and int(row["clients"]) == count
					and int(row["size_bytes"]) == 4194304
				)
				axis.step(
					values,
					np.arange(1, len(values) + 1) / len(values),
					where="post",
					label=f"{network}, N={count}",
				)
		axis.set(title=operation, xlabel="Tempo (s)", ylabel="CDF", ylim=(0, 1.02))
		axis.legend(fontsize=7.5)
	save(figure, "cdf")

	figure, axis = plt.subplots(figsize=(6.2, 2.4))
	axis.set(xlim=(-0.1, 6.3), ylim=(-0.45, 2.3))
	axis.axis("off")
	for x, width, label, color in [
		(-0.08, 2.12, "Acesso cliente\n10.10.0.0/24", "#E8F3FA"),
		(2.08, 2.10, "Núcleo\n10.20.0.0/24", "#FFF2D8"),
		(4.22, 2.05, "Acesso servidor\n10.30.0.0/24", "#E9F6ED"),
	]:
		axis.add_patch(Rectangle((x, 0.22), width, 1.85, facecolor=color, edgecolor="#bbb"))
		axis.text(x + width / 2, 1.85, label, ha="center", va="center", fontsize=9)
	nodes = [
		(0.4, "8 clientes\n.10 a .17"),
		(1.3, "Switch"),
		(2.2, "R1"),
		(3.1, "Switch"),
		(4.0, "R2"),
		(4.9, "Switch"),
		(5.8, "Servidor\n.10:8080"),
	]
	for (x, _), (y, _) in zip(nodes, nodes[1:]):
		axis.plot([x, y], [1, 1], color="#555", linewidth=1.5)
	for x, label in nodes:
		axis.add_patch(
			FancyBboxPatch(
				(x - 0.36, 0.65),
				0.72,
				0.7,
				boxstyle="round,pad=0.02",
				facecolor="white",
				edgecolor="#24536E",
				zorder=2,
			)
		)
		axis.text(x, 1, label, ha="center", va="center", fontsize=8, zorder=3)
	for x, label in [(2.65, "R1:eth1"), (3.55, "R2:eth0")]:
		axis.annotate(
			label,
			xy=(x, 0.98),
			xytext=(x, 0.02),
			ha="center",
			fontsize=8,
			arrowprops={"arrowstyle": "->", "color": "#b45f06"},
		)
	axis.text(3.1, -0.28, "HTB/netem nos dois sentidos; sem perda artificial", ha="center")
	save(figure, "topologia")


if __name__ == "__main__":
	main()
