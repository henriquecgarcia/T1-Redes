#!/usr/bin/env python3
"""Confere o conteúdo dos fontes funcionais preservados, sem alterar o arquivo."""

import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
	"client/tcp_client.c": "055a52880c44a67ee7e2100410239f652ee0302391b3aeea456cd13465ebc03f",
	"server/tcp_server.c": "71f89c2d14c0ce45061012a407fd398f34447d2cf248a48fd64cee12caf440f4",
}


def main():
	result = []
	with tarfile.open(ROOT / "originais/originais.tar.gz", "r:gz") as archive:
		for name, expected in EXPECTED.items():
			content = archive.extractfile("1_TCPTrasmission/" + name).read()
			actual = hashlib.sha256(content).hexdigest()
			assert actual == expected, name
			result.append({"path": name, "sha256": actual, "status": "unchanged"})

	print(json.dumps(result, indent=2))


if __name__ == "__main__":
	main()
