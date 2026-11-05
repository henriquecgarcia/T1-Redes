#!/usr/bin/env python3
"""Confere os bytes dos dados e das evidências preservados durante a revisão."""

import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "parte2/evidencias/revisao/preservacao_manifesto.json"


def main():
	entries = json.loads(MANIFEST.read_text())
	for entry in entries:
		if "archive" in entry:
			with tarfile.open(ROOT / entry["archive"], "r:gz") as archive:
				content = archive.extractfile(entry["member"]).read()
		else:
			content = (ROOT / entry["path"]).read_bytes()
		actual = hashlib.sha256(content).hexdigest()
		assert actual == entry["sha256"], entry["path"]

	print(f"Preservação confirmada: {len(entries)} arquivos com os mesmos bytes.")


if __name__ == "__main__":
	main()
