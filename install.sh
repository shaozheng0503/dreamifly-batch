#!/bin/bash
# 一键把本 Skill 安装到 Claude Code 的 skills 目录。
# 用法：
#   ./install.sh            # 安装到 ~/.claude/skills/dreamifly-batch（用户级）
#   ./install.sh .claude    # 安装到 当前项目/.claude/skills/dreamifly-batch（项目级）
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="dreamifly-batch"

if [ "$1" = ".claude" ]; then
  DEST_ROOT="$(pwd)/.claude/skills"
else
  DEST_ROOT="$HOME/.claude/skills"
fi
DEST="$DEST_ROOT/$NAME"

mkdir -p "$DEST_ROOT"
# 复制源码，排除运行产物与个人登录态
rsync -a --delete \
  --exclude '.git' \
  --exclude 'config/cookie.txt' \
  --exclude 'run.log' \
  --exclude 'done.txt' \
  --exclude 'images/*' \
  --exclude '__pycache__' \
  "$SRC/" "$DEST/"

echo "✅ 已安装到：$DEST"
echo "下一步：复制 config/cookie.txt.example 为 config/cookie.txt 并填入你的登录态。"
echo "之后在 Claude Code 里说\"批量生图\"即可触发本 Skill。"
