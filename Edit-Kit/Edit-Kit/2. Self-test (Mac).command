#!/bin/bash
# Double-click to check that Edit Kit works on this Mac (renders a 3 s test video).
cd "$(dirname "$0")" && python3 selftest.py
echo ""; read -n 1 -s -r -p "Press any key to close"
