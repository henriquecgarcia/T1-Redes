#!/usr/bin/env python3
"""Testes em sockets TCP reais, com armazenamento temporário isolado."""
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess as sp
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(os.environ.get("T1_TEST_EVIDENCE_DIR", ROOT / "build/testes"))


def digest(p):
	return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def line(s):
	b = b""
	while not b.endswith(b"\n"):
		c = s.recv(1)
		if not c:
			raise EOFError(b)
		b += c
	return b


class TransferTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.tmp = tempfile.TemporaryDirectory(prefix="redes-t1-")
		cls.d = Path(cls.tmp.name)
		cls.store = cls.d / "server"
		cls.store.mkdir()
		probe = socket.socket()
		probe.bind(("127.0.0.1", 0))
		cls.port = probe.getsockname()[1]
		probe.close()
		EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
		cls.log = open(EVIDENCE_DIR / "server-test.log", "w")
		cls.proc = sp.Popen(
			[str(ROOT / "build/server"), str(cls.port), str(cls.store)],
			stdout=cls.log,
			stderr=sp.STDOUT,
		)
		for _ in range(100):
			try:
				with cls.sock():
					break
			except OSError:
				time.sleep(0.02)
		else:
			raise RuntimeError("server did not start")

	@classmethod
	def tearDownClass(cls):
		cls.proc.terminate()
		cls.proc.wait(timeout=5)
		cls.log.close()
		cls.tmp.cleanup()

	@classmethod
	def sock(cls):
		return socket.create_connection(("127.0.0.1", cls.port), timeout=3)

	def client(self, op, name, path, success=True, port=None):
		r = sp.run(
			[str(ROOT / "build/client"), "127.0.0.1", str(port or self.port), op, name, str(path)],
			capture_output=True,
			text=True,
			timeout=20,
		)
		self.assertEqual(r.returncode, 0 if success else 1, r.stdout + r.stderr)
		v = json.loads(r.stdout)
		self.assertEqual(v["status"], "ok" if success else "error")
		return v

	def test_01_binary_sizes_and_overwrite(self):
		for n in [0, 1, 1023, 1024, 4096, 32768, 262144, 1048576, 4194304]:
			with self.subTest(size=n):
				source = self.d / "source"
				source.write_bytes(os.urandom(n))
				target = self.d / "dest"
				target.write_bytes(b"old destination")
				self.client("PUT", "binary.bin", source)
				self.assertEqual(digest(source), digest(self.store / "binary.bin"))
				self.client("GET", "binary.bin", target)
				self.assertEqual(digest(source), digest(target))
				print(f"SHA256 size={n} {digest(source)}", flush=True)

	def test_02_fragmented_and_pipelined(self):
		data = bytes(range(256)) * 37
		with self.sock() as s:
			for c in b"PUT fragment.bin " + str(len(data)).encode() + b"\n":
				s.sendall(bytes([c]))
			self.assertEqual(line(s), b"READY\n")
			for pos in range(0, len(data), 7):
				s.sendall(data[pos : pos + 7])
			s.sendall(b"GET fragment.bin\nhello\n")
			self.assertEqual(line(s), b"OK\n")
			self.assertEqual(line(s), f"OK {len(data)}\n".encode())
			got = b""
			while len(got) < len(data):
				got += s.recv(min(13, len(data) - len(got)))
			self.assertEqual(got, data)
			self.assertEqual(line(s), b"hello\n")

	def test_03_aborted_put_preserves_old(self):
		p = self.store / "preserve.bin"
		p.write_bytes(b"original")
		with self.sock() as s:
			s.sendall(b"PUT preserve.bin 999\n")
			self.assertEqual(line(s), b"READY\n")
			s.sendall(b"partial")
		time.sleep(0.1)
		self.assertEqual(p.read_bytes(), b"original")

	def test_04_eight_simultaneous_workers(self):
		sockets = []
		try:
			for i in range(8):
				s = self.sock()
				sockets.append(s)
				s.sendall(f"PUT parallel{i}.bin 32\n".encode())
			# As oito respostas READY devem chegar antes do primeiro payload.
			for s in sockets:
				self.assertEqual(line(s), b"READY\n")
			for s in sockets:
				s.sendall(b"X" * 32)
			for s in sockets:
				self.assertEqual(line(s), b"OK\n")
		finally:
			for s in sockets:
				s.close()

	def test_05_concurrent_same_name(self):
		sources = []
		for i in range(8):
			p = self.d / f"collision{i}"
			p.write_bytes(bytes([i]) * 32768)
			sources.append(p)
		barrier = threading.Barrier(8)

		def worker(p):
			barrier.wait()
			self.client("PUT", "collision.bin", p)

		with cf.ThreadPoolExecutor(8) as pool:
			list(pool.map(worker, sources))
		self.assertIn(digest(self.store / "collision.bin"), [digest(p) for p in sources])

	def test_06_invalid_and_missing(self):
		commands = [
			b"GET ../escape\n",
			b"PUT x -1\n",
			b"PUT x +1\n",
			b"PUT x 1073741825\n",
			b"PUT x 1 extra\n",
			b"GET missing.bin\n",
			b"GET\n",
		]
		with self.sock() as s:
			for c in commands:
				s.sendall(c)
				self.assertTrue(line(s).startswith(b"ERR "))
		p = self.d / "missing-dest"
		p.write_bytes(b"keep")
		self.client("GET", "missing.bin", p, False)
		self.assertEqual(p.read_bytes(), b"keep")
		self.client("PUT", "x", self.d / "absent", False)

	def test_07_nonregular_and_symlink(self):
		(self.store / "link").symlink_to("/etc/passwd")
		os.mkfifo(self.store / "fifo")
		with self.sock() as s:
			for n in ["link", "fifo"]:
				s.sendall(f"GET {n}\n".encode())
				self.assertTrue(line(s).startswith(b"ERR "))

	def test_08_get_snapshot_during_put(self):
		p = self.store / "snapshot"
		p.write_bytes(b"old")
		with self.sock() as s:
			s.sendall(b"PUT snapshot 3\n")
			self.assertEqual(line(s), b"READY\n")
			out = self.d / "snapshot"
			self.client("GET", "snapshot", out)
			self.assertEqual(out.read_bytes(), b"old")
			s.sendall(b"new")
			self.assertEqual(line(s), b"OK\n")
		self.assertEqual(p.read_bytes(), b"new")

	def test_09_truncated_get_preserves_destination(self):
		listener = socket.socket()
		listener.bind(("127.0.0.1", 0))
		listener.listen()

		def fake():
			with listener:
				s, _ = listener.accept()
				with s:
					line(s)
					s.sendall(b"OK 100\nshort")

		t = threading.Thread(target=fake)
		t.start()
		p = self.d / "truncated"
		p.write_bytes(b"keep")
		self.client("GET", "x", p, False, listener.getsockname()[1])
		t.join()
		self.assertEqual(p.read_bytes(), b"keep")

	def test_10_long_header_disconnect_and_recovery(self):
		with self.sock() as s:
			s.sendall(b"A" * 1100 + b"\n")
			try:
				self.assertEqual(s.recv(1), b"")
			except ConnectionResetError:
				pass
		with self.sock() as s:
			s.sendall(b"recovery\n")
			self.assertEqual(line(s), b"recovery\n")

	def test_11_idle_timeout_releases_worker(self):
		with self.sock() as s:
			s.settimeout(18)
			start = time.monotonic()
			self.assertEqual(s.recv(1), b"")
			elapsed = time.monotonic() - start
			self.assertGreater(elapsed, 14)
			self.assertLess(elapsed, 18)
			print(f"IDLE_TIMEOUT seconds={elapsed:.3f}", flush=True)


if __name__ == "__main__":
	unittest.main(verbosity=2)
