#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
DEST=${CORE_EXPORT_DIR:-$ROOT}
CONTAINER=${CORE_CONTAINER:-core}
WORK=${CORE_WORKDIR:-/tmp/redest1-work}
mkdir -p "$DEST/evidencias" "$DEST/core"

if docker exec "$CONTAINER" test -f "$WORK/resultados_brutos.csv"; then
	docker cp "$CONTAINER:$WORK/resultados_brutos.csv" "$DEST/resultados_brutos.csv"
fi
docker cp "$CONTAINER:$WORK/evidencias/." "$DEST/evidencias/"
docker cp "$CONTAINER:$WORK/core/topologia.xml" "$DEST/core/topologia.xml"
