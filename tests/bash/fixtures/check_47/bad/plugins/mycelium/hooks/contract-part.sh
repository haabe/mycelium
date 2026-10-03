#!/bin/bash
# Fixture contract-part handler
python3 "$(dirname "$0")/../scripts/contract_parts.py" --part "${1:-1}"
