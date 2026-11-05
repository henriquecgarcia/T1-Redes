#!/usr/bin/env python3
"""Topologia CORE 9.2 e execução concorrente com retomada por rodada."""
import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import random
import shlex
import subprocess as sp
import time
import uuid
from pathlib import Path
from core.emulator.coreemu import CoreEmu
from core.emulator.data import InterfaceData
from core.emulator.enumerations import EventTypes
from core.nodes.base import CoreNode, Position
from core.nodes.network import SwitchNode

ROOT = Path(os.environ.get("T1_RESULT_ROOT", Path(__file__).resolve().parents[1]))
BIN = Path(os.environ.get("T1_BINARY_DIR", Path(__file__).resolve().parents[2] / "parte1/build"))
SERVER = "10.30.0.10"
FIELDS = [
	"experiment_id",
	"phase",
	"round_id",
	"attempt",
	"network",
	"operation",
	"size_bytes",
	"clients",
	"repetition",
	"client_id",
	"start_s",
	"duration_s",
	"throughput_mbps",
	"bytes",
	"status",
	"sha256_expected",
	"sha256_actual",
	"error",
	"launch_skew_ms",
	"overlap_ms",
	"round_duration_s",
	"aggregate_mbps",
	"timestamp_utc",
]


def sha(p):
	return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def q(x):
	return shlex.quote(str(x))


class Lab:
	def __init__(self):
		self.emu = CoreEmu()
		self.session = self.emu.create_session()
		self.nodes = []
		self.pid = None
		self.iperf_pid = None

	def setup(self):
		s = self.session
		s.set_state(EventTypes.CONFIGURATION_STATE)
		a = s.add_node(SwitchNode, name="acesso_cliente", position=Position(x=180, y=250))
		core = s.add_node(SwitchNode, name="nucleo", position=Position(x=500, y=250))
		b = s.add_node(SwitchNode, name="acesso_servidor", position=Position(x=820, y=250))

		def host(name, x, y):
			opt = CoreNode.create_options()
			opt.services = []
			n = s.add_node(CoreNode, name=name, options=opt, position=Position(x=x, y=y))
			self.nodes.append(n)
			return n

		def link(n, sw, idx, ip):
			s.add_link(n.id, sw.id, InterfaceData(id=idx, name=f"eth{idx}", ip4=ip, ip4_mask=24))

		self.clients = [host(f"cliente{i+1}", 40, 50 + i * 65) for i in range(8)]
		for i, n in enumerate(self.clients):
			link(n, a, 0, f"10.10.0.{10+i}")
		self.r1 = host("roteador1", 350, 250)
		self.r2 = host("roteador2", 650, 250)
		self.server = host("servidor", 980, 250)
		link(self.r1, a, 0, "10.10.0.1")
		link(self.r1, core, 1, "10.20.0.1")
		link(self.r2, core, 0, "10.20.0.2")
		link(self.r2, b, 1, "10.30.0.1")
		link(self.server, b, 0, SERVER)
		s.instantiate()
		for n in self.clients:
			n.cmd("ip route replace default via 10.10.0.1")
		self.server.cmd("ip route replace default via 10.30.0.1")
		self.r1.cmd("sysctl -qw net.ipv4.ip_forward=1")
		self.r2.cmd("sysctl -qw net.ipv4.ip_forward=1")
		self.r1.cmd("ip route replace 10.30.0.0/24 via 10.20.0.2")
		self.r2.cmd("ip route replace 10.10.0.0/24 via 10.20.0.1")
		for n in self.nodes:
			n.cmd("sysctl -qw net.ipv4.tcp_congestion_control=cubic")
			# Desativa offloads para que a fila trate os pacotes de forma consistente.
			for idx in range(2 if n in [self.r1, self.r2] else 1):
				n.cmd(f"ethtool -K eth{idx} tso off gso off gro off", shell=True)
		(ROOT / "core").mkdir(exist_ok=True)
		s.save_xml(ROOT / "core/topologia.xml")
		config = {
			n.name: n.cmd(
				"ip -br address; ip route; sysctl net.ipv4.tcp_congestion_control", shell=True
			)
			for n in self.nodes
		}
		(ROOT / "evidencias/topologia_real.json").write_text(json.dumps(config, indent=2))
		data = ROOT / "data"
		data.mkdir(exist_ok=True)
		self.storage = data / "server"
		self.storage.mkdir(exist_ok=True)
		for size in [32768, 262144, 1048576, 4194304]:
			p = data / f"input_{size}.bin"
			if not p.exists():
				p.write_bytes(random.Random(size).randbytes(size))
			(self.storage / f"input_{size}.bin").write_bytes(p.read_bytes())
		log = ROOT / "evidencias/server-core.log"
		self.pid = int(
			self.server.cmd(
				f'{q(BIN/"server")} 8080 {q(self.storage)} >{q(log)} 2>&1 & echo $!', shell=True
			).strip()
		)
		self.iperf_pid = int(
			self.server.cmd(
				f'{q(ROOT/"tools/iperf3")} -s '
				f'>{q(ROOT/"evidencias/iperf-server.log")} 2>&1 & echo $!',
				shell=True,
			).strip()
		)
		time.sleep(0.2)

	def profile(self, net):
		rate, delay = (100, 5) if net == "A" else (20, 30)
		for node, iface in [(self.r1, "eth1"), (self.r2, "eth0")]:
			node.cmd(f"tc qdisc del dev {iface} root 2>/dev/null || true", shell=True)
			node.cmd(f"tc qdisc add dev {iface} root handle 1: htb default 10")
			node.cmd(
				f"tc class replace dev {iface} parent 1: classid 1:10 htb "
				f"rate {rate}mbit ceil {rate}mbit burst 16k cburst 16k"
			)
			node.cmd(
				f"tc qdisc replace dev {iface} parent 1:10 handle 10: "
				f"netem limit 10000 delay {delay}ms"
			)
		return rate, delay

	def validate(self, net):
		self.profile(net)
		out = {}
		out["ping"] = self.clients[0].cmd(f"ping -n -c 10 -i 0.1 -W 2 {SERVER}")
		out["traceroute"] = self.clients[0].cmd(f"traceroute -n -I -w 2 -q 1 {SERVER}")
		for name, value in out.items():
			(ROOT / f"evidencias/{name}_{net}.log").write_text(value)
		for direction, flags in [("forward", ""), ("reverse", "-R")]:
			raw = self.clients[0].cmd(
				f'{q(ROOT/"tools/iperf3")} -c {SERVER} -t 5 -O 1 -w 256K -J {flags}'
			)
			(ROOT / f"evidencias/iperf_{net}_{direction}.json").write_text(raw)
			value = json.loads(raw)
			if "error" in value:
				raise RuntimeError(value["error"])
			mbps = value["end"]["sum_received"]["bits_per_second"] / 1e6
			rate = 100 if net == "A" else 20
			if not 0.65 * rate < mbps < 1.2 * rate:
				raise RuntimeError(f"iperf out of range {net} {direction} {mbps}")
		for name, value in out.items():
			(ROOT / f"evidencias/{name}_{net}.log").write_text(value)
		import re

		avg = float(re.search(r"= [\d.]+/([\d.]+)/", out["ping"]).group(1))
		expected = 10 if net == "A" else 60
		if not expected * 0.8 < avg < expected + 15:
			raise RuntimeError(f"RTT out of range {avg}")
		if "0% packet loss" not in out["ping"]:
			raise RuntimeError("ping loss")
		self.snapshot(net, "validation")

	def snapshot(self, net, suffix):
		out = {
			n.name: n.cmd(f"tc -s qdisc show dev {iface}")
			for n, iface in [(self.r1, "eth1"), (self.r2, "eth0")]
		}
		(ROOT / f"evidencias/tc_{net}_{suffix}.json").write_text(json.dumps(out, indent=2))

	def shutdown(self):
		for pid in [self.pid, self.iperf_pid]:
			if pid:
				try:
					self.server.cmd(f"kill {pid}")
				except Exception:
					pass
		self.emu.shutdown()


def run_round(lab, cfg, phase, experiment_id):
	count = int(cfg["clients"])
	size = int(cfg["size_bytes"])
	op = cfg["operation"]
	net = cfg["network"]
	source = ROOT / f"data/input_{size}.bin"
	expected = sha(source)
	attempt = uuid.uuid4().hex[:12]
	gate = time.monotonic_ns() + 150_000_000

	def worker(i):
		remote = f"input_{size}.bin" if op == "GET" else f"put_{size}_{i}.bin"
		local = ROOT / f"data/download_{i}.bin" if op == "GET" else source
		if op == "GET":
			local.unlink(missing_ok=True)
		start = time.monotonic()
		v = {}
		error = ""
		status = "error"
		actual = ""
		command = (
			f'timeout --signal=KILL 55s env T1_START_NS={gate} {q(BIN/"client")} '
			f"{SERVER} 8080 {op} {remote} {q(local)}"
		)
		try:
			p = sp.run(
				shlex.split(lab.clients[i].create_cmd(command)),
				capture_output=True,
				text=True,
				timeout=60,
			)
			v = json.loads(p.stdout.strip().splitlines()[-1])
			if p.returncode or v["status"] != "ok":
				raise RuntimeError(p.stdout + p.stderr)
			actual = sha(local if op == "GET" else lab.storage / remote)
			status = "ok" if actual == expected and int(v["bytes"]) == size else "integrity_error"
		except sp.TimeoutExpired:
			error = "operation timeout (60 s)"
			status = "timeout"
		except Exception as e:
			error = str(e)[:500]
		return dict(
			experiment_id=experiment_id,
			phase=phase,
			round_id=cfg["round_id"],
			attempt=attempt,
			network=net,
			operation=op,
			size_bytes=size,
			clients=count,
			repetition=cfg["repetition"],
			client_id=i + 1,
			start_s=v.get("start_s", start),
			duration_s=v.get("duration_s", time.monotonic() - start),
			throughput_mbps=v.get("throughput_mbps", 0),
			bytes=v.get("bytes", 0),
			status=status,
			sha256_expected=expected,
			sha256_actual=actual,
			error=error,
			timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
		)

	with cf.ThreadPoolExecutor(count) as pool:
		rows = list(pool.map(worker, range(count)))
	begins = [float(r["start_s"]) for r in rows]
	end = max(float(r["start_s"]) + float(r["duration_s"]) for r in rows)
	span = end - min(begins)
	skew = (max(begins) - min(begins)) * 1000
	overlap = (min(float(r["start_s"]) + float(r["duration_s"]) for r in rows) - max(begins)) * 1000
	if count > 1 and overlap <= 0:
		for r in rows:
			r.update(
				status="concurrency_error", error="no simultaneous overlap in monotonic intervals"
			)
	for r in rows:
		r.update(
			launch_skew_ms=skew,
			overlap_ms=overlap,
			round_duration_s=span,
			aggregate_mbps=sum(int(x["bytes"]) for x in rows if x["status"] == "ok")
			* 8
			/ span
			/ 1e6,
		)
	return rows


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--phase", choices=["pilot", "main"], default="pilot")
	ap.add_argument("--limit", type=int)
	args = ap.parse_args()
	(ROOT / "evidencias").mkdir(exist_ok=True)
	experiment_id = "core-20261105-v1"
	raw = ROOT / ("resultados_brutos.csv" if args.phase == "main" else "evidencias/piloto.csv")
	journal = ROOT / (
		"evidencias/rodadas_concluidas.jsonl"
		if args.phase == "main"
		else "evidencias/piloto_concluido.jsonl"
	)
	completed = {}
	if journal.exists():
		for text in journal.read_text().splitlines():
			try:
				r = json.loads(text)
				completed[r["round_id"]] = r["attempt"]
			except json.JSONDecodeError:
				pass
	if completed:
		observed = {}
		if raw.exists():
			for r in csv.DictReader(raw.open()):
				observed.setdefault((r["round_id"], r["attempt"]), set()).add(int(r["client_id"]))
		completed = {k: v for k, v in completed.items() if observed.get((k, v))}
	matrix = list(csv.DictReader((ROOT / "matriz_experimental.csv").open()))
	if args.phase == "pilot":
		matrix = [
			dict(
				round_id=f"pilot-{net}-{op}",
				network=net,
				operation=op,
				size_bytes=262144,
				clients=4,
				repetition=0,
			)
			for net in ["A", "B"]
			for op in ["GET", "PUT"]
		]
	# Só retoma após confirmar a presença de todos os clientes da rodada.
	completed = {
		r["round_id"]: completed[r["round_id"]]
		for r in matrix
		if r["round_id"] in completed
		and observed.get((r["round_id"], completed[r["round_id"]]))
		== set(range(1, int(r["clients"]) + 1))
	}
	todo = [r for r in matrix if r["round_id"] not in completed]
	if args.limit:
		todo = todo[: args.limit]
	if not todo:
		print("No pending rounds", flush=True)
		return
	lab = Lab()
	try:
		lab.setup()
		for net in ["A", "B"]:
			lab.validate(net)
		current = None
		with raw.open("a", newline="") as f, journal.open("a") as j:
			writer = csv.DictWriter(f, fieldnames=FIELDS)
			if f.tell() == 0:
				writer.writeheader()
				f.flush()
				os.fsync(f.fileno())
			for cfg in todo:
				if cfg["network"] != current:
					lab.profile(cfg["network"])
					current = cfg["network"]
				rows = run_round(lab, cfg, args.phase, experiment_id)
				writer.writerows(rows)
				f.flush()
				os.fsync(f.fileno())
				marker = dict(
					round_id=cfg["round_id"],
					attempt=rows[0]["attempt"],
					clients=len(rows),
					all_ok=all(r["status"] == "ok" for r in rows),
				)
				j.write(json.dumps(marker) + "\n")
				j.flush()
				os.fsync(j.fileno())
				print(
					json.dumps(
						dict(
							**marker,
							network=current,
							operation=cfg["operation"],
							size=cfg["size_bytes"],
							duration=rows[0]["round_duration_s"],
							skew_ms=rows[0]["launch_skew_ms"],
						)
					),
					flush=True,
				)
				if args.phase == "pilot" and not marker["all_ok"]:
					raise RuntimeError("pilot failed")
			for net in ["A", "B"]:
				if current == net:
					lab.snapshot(net, "final")
	finally:
		lab.shutdown()


if __name__ == "__main__":
	main()
