#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# Novas verificações ficam separadas dos logs da coleta original.
TEST_DIR=${T1_TEST_EVIDENCE_DIR:-$PWD/build/testes/$(date +%Y%m%d-%H%M%S)}
mkdir -p "$TEST_DIR" build
export T1_TEST_EVIDENCE_DIR="$TEST_DIR"

make -B 2>&1 | tee "$TEST_DIR/compilacao.log"
python3 tests/test_transfer.py 2>&1 | tee "$TEST_DIR/testes.log"
gcc -shared -fPIC -O2 -Wall -Wextra tests/short_io.c -ldl -o build/short_io.so
LD_PRELOAD="$PWD/build/short_io.so" python3 tests/test_transfer.py \
	2>&1 | tee "$TEST_DIR/testes_io_parcial.log"
python3 scripts/audit_originals.py | tee "$TEST_DIR/originais.log"
