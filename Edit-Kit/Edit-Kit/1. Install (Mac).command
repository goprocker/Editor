#!/bin/bash
# Double-click to install Edit Kit (first time: right-click > Open > Open).
cd "$(dirname "$0")" && bash ./install.sh
echo ""; read -n 1 -s -r -p "Press any key to close"
