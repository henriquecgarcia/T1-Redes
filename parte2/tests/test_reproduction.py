#!/usr/bin/env python3
"""Executa o piloto em outro diretório e mantém a coleta original intacta."""

import csv
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "parte2/build/revisao" / f"piloto-{time.time_ns()}"
OUTPUT.mkdir(parents=True)
environment = dict(os.environ)
environment["CORE_WORKDIR"] = f"/tmp/redest1-revisao-{time.time_ns()}"
environment["CORE_EXPORT_DIR"] = str(OUTPUT)

# O script registra logs locais: uma cópia evita sobrescrever evidências existentes.
import shutil

project = OUTPUT / "projeto"
project.mkdir()
for part in ["parte1", "parte2"]:
	shutil.copytree(
		ROOT / part,
		project / part,
		ignore=shutil.ignore_patterns("build", "__pycache__", "evidencias", "iperf3"),
	)
(project / "parte2/evidencias").mkdir()

with (OUTPUT / "execucao.log").open("w") as log:
	subprocess.run(
		["bash", str(project / "parte2/scripts/run_docker.sh"), "pilot"],
		cwd=project,
		env=environment,
		stdout=log,
		stderr=subprocess.STDOUT,
		check=True,
	)

with (OUTPUT / "evidencias/piloto.csv").open() as stream:
	rows = list(csv.DictReader(stream))
assert len(rows) == 16
assert len({row["round_id"] for row in rows}) == 4
assert all(
	row["status"] == "ok" and row["sha256_expected"] == row["sha256_actual"]
	for row in rows
)
print(f"Piloto reproduzido: 4 rodadas, 16 transferências corretas. Logs: {OUTPUT}")
