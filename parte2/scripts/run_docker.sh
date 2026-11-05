#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
CONTAINER=${CORE_CONTAINER:-core}
WORK=${CORE_WORKDIR:-/tmp/redest1-work}
PHASE=${1:-pilot}

if [[ "$PHASE" != pilot && "$PHASE" != main ]]; then
	echo 'usage: bash parte2/scripts/run_docker.sh pilot|main'
	exit 2
fi

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
	docker run -d --privileged --name "$CONTAINER" "${CORE_IMAGE:-core}"
fi
docker start "$CONTAINER" >/dev/null
if [[ $(docker inspect -f '{{.HostConfig.Privileged}}' "$CONTAINER") != true ]]; then
	echo 'Select a privileged CORE container using CORE_CONTAINER.' >&2
	exit 1
fi

# O container existente é mantido; a execução usa um diretório isolado.
docker exec "$CONTAINER" bash -lc '
	apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
		gcc make ethtool traceroute wget ca-certificates
' >parte2/evidencias/docker_dependencias.log 2>&1

docker exec "$CONTAINER" mkdir -p \
	"$WORK/parte1" "$WORK/parte2" "$WORK/core" "$WORK/evidencias" "$WORK/tools"
tar cf - parte1/src parte1/Makefile parte2/core parte2/scripts \
	parte2/tools/iperf-3.22.tar.gz |
	docker exec -i "$CONTAINER" tar xf - -C "$WORK"
docker exec "$CONTAINER" make -C "$WORK/parte1"
docker exec "$CONTAINER" bash "$WORK/parte2/scripts/build_iperf.sh"
docker cp parte2/matriz_experimental.csv "$CONTAINER:$WORK/matriz_experimental.csv"
docker exec "$CONTAINER" cp "$WORK/parte2/tools/iperf3" "$WORK/tools/iperf3"

# Rodadas confirmadas não são repetidas. Use outro CORE_WORKDIR para uma nova coleta.
set +e
docker exec -e T1_RESULT_ROOT="$WORK" -e T1_BINARY_DIR="$WORK/parte1/build" \
	"$CONTAINER" /opt/core/venv/bin/python \
	"$WORK/parte2/core/run_experiments.py" --phase "$PHASE" 2>&1 |
	tee "parte2/evidencias/reexecucao_${PHASE}.log"
status=${PIPESTATUS[0]}
set -e
bash parte2/scripts/sync_docker.sh
exit "$status"
