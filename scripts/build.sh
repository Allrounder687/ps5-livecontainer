#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  Building PS5 LiveContainer via Docker Toolchain"
echo "========================================================"

# Build Docker SDK image
docker build -t ps5-sdk .

# Run build inside Docker
docker run --rm -v "${PWD}:/app" ps5-sdk bash -c "sed -i 's/\r$//' Makefile src/*.c include/*.h test_payloads/*/*.c test_payloads/*/*Makefile 2>/dev/null; make"

echo ""
echo "[SUCCESS] Built ps5_livecontainer.elf and test payloads!"
