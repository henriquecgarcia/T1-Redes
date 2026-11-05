#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p tools evidencias

if [[ ! -f tools/iperf-3.22.tar.gz ]]; then
	wget -q https://downloads.es.net/pub/iperf/iperf-3.22.tar.gz -O tools/iperf-3.22.tar.gz
fi
sha256sum tools/iperf-3.22.tar.gz | tee evidencias/iperf_source.sha256
tar xzf tools/iperf-3.22.tar.gz -C tools
cd tools/iperf-3.22
./configure --disable-shared --without-openssl
make -j4
cp src/iperf3 ../iperf3
../iperf3 --version
