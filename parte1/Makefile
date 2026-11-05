CC = gcc
CFLAGS = -O2 -g -std=c11 -Wall -Wextra -Wpedantic -Werror -D_FILE_OFFSET_BITS=64
.PHONY: all test
all: build/server build/client
build:
	mkdir -p build
build/server: src/tcp_server.c src/protocol.h | build
	$(CC) $(CFLAGS) -fopenmp $< -o $@
build/client: src/tcp_client.c src/protocol.h | build
	$(CC) $(CFLAGS) $< -o $@
test: all
	python3 tests/test_transfer.py
