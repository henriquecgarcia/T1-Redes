#!/usr/bin/env python3
"""Transcreve valores dos CSV para as tabelas do artigo, sem recalcular estatísticas."""

import csv
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "relatorio/tabelas"


def number(value, digits=3):
	return f"{float(value):.{digits}f}".replace(".", ",")


def table(name, caption, label, columns, header, rows):
	lines = [
		"% Valores transcritos dos dados entregues; não editar manualmente.",
		r"\begin{table}[htbp]",
		"\t" + r"\centering",
		textwrap.fill(
			rf"\caption{{{caption}}}", width=92,
			initial_indent="\t", subsequent_indent="\t\t",
		),
		"\t" + rf"\label{{{label}}}",
		"\t" + rf"\begin{{tabular}}{{{columns}}}",
		"\t\t" + r"\toprule",
		"\t\t" + " & ".join(header) + r" \\",
		"\t\t" + r"\midrule",
	]
	for row in rows:
		lines.append("\t\t" + " & ".join(map(str, row)) + r" \\")
	lines.extend(["\t\t" + r"\bottomrule", "\t" + r"\end{tabular}", r"\end{table}"])
	(OUTPUT / f"{name}.tex").write_text("\n".join(lines) + "\n")


def main():
	OUTPUT.mkdir(exist_ok=True)
	with (ROOT / "parte2/resultados_resumidos.csv").open() as stream:
		summary = list(csv.DictReader(stream))

	def find(network, operation, size, clients):
		return next(
			row
			for row in summary
			if row["network"] == network
			and row["operation"] == operation
			and int(row["size_bytes"]) == size
			and int(row["clients"]) == clients
		)

	# A validação usa os valores recebidos do iperf e o RTT médio do ping.
	import json
	import re

	validation = []
	for network in ["A", "B"]:
		ping = (ROOT / f"parte2/evidencias/ping_{network}.log").read_text()
		average = re.search(r"= [\d.]+/([\d.]+)/", ping).group(1)
		rates = []
		for direction in ["forward", "reverse"]:
			path = ROOT / f"parte2/evidencias/iperf_{network}_{direction}.json"
			value = json.loads(path.read_text())["end"]["sum_received"]
			rates.append(number(value["bits_per_second"] / 1e6))
		validation.append([network, number(average), *rates, "0/10"])
	table(
		"validacao",
		"Validação do caminho cliente--servidor nos dois perfis.",
		"tab:validacao",
		"lrrrr",
		["Perfil", "RTT (ms)", "Ida (Mbps)", "Volta (Mbps)", "Perdas"],
		validation,
	)

	latencies = []
	for network in ["A", "B"]:
		for operation in ["GET", "PUT"]:
			for clients in [1, 4, 8]:
				row = find(network, operation, 4194304, clients)
				interval = (
					"["
					+ number(row["duration_s_ci95_low"])
					+ "; "
					+ number(row["duration_s_ci95_high"])
					+ "]"
				)
				latencies.append(
					[
						network,
						operation,
						clients,
						number(row["duration_s_mean"]),
						number(row["duration_s_median"]),
						number(row["duration_s_std_clients"]),
						interval,
					]
				)
	table(
		"tempos_4mib",
		"Tempo de resposta para 4 MiB, em segundos. O IC da média usa "
		"11 rodadas; mediana e desvio padrão (DP) descrevem as observações individuais.",
		"tab:tempos",
		"llcrrrr",
		["Perfil", "Op.", "$N$", "Média", "Mediana", "DP", "IC 95\\%"],
		latencies,
	)

	ratios = []
	for size in [32768, 4194304]:
		for clients in [1, 8]:
			ag = find("A", "GET", size, clients)
			ap = find("A", "PUT", size, clients)
			bg = find("B", "GET", size, clients)
			bp = find("B", "PUT", size, clients)
			ratios.append(
				[
					size // 1024,
					clients,
					number(float(ap["duration_s_mean"]) / float(ag["duration_s_mean"])),
					number(float(bp["duration_s_mean"]) / float(bg["duration_s_mean"])),
					number(float(bg["duration_s_mean"]) / float(ag["duration_s_mean"])),
					number(float(bp["duration_s_mean"]) / float(ap["duration_s_mean"])),
				]
			)
	table(
		"comparacoes",
		"Razões entre médias de tempo de resposta. Valores descritivos, "
		"sem teste de hipótese ou intervalo específico para as razões.",
		"tab:comparacoes",
		"rrrrrr",
		["KiB", "$N$", "PUT/GET A", "PUT/GET B", "B/A GET", "B/A PUT"],
		ratios,
	)


if __name__ == "__main__":
	main()
