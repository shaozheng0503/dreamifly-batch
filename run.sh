#!/bin/bash
# Dreamifly 生图启动器。手动跑：./run.sh   只跑前 N 条：./run.sh 3
# cron 里也可直接调用本脚本（已自动切到脚本所在目录）。
cd "$(dirname "$0")" || exit 1
/usr/bin/python3 dreamify.py "$@"
