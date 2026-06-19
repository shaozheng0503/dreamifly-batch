#!/bin/bash
# 一键把本 Skill 安装到 Claude Code / Cursor 的 skills 目录。
# 用法：
#   ./install.sh            # 安装到 ~/.claude/skills/dreamifly-batch（用户级）
#   ./install.sh .claude    # 安装到 当前项目/.claude/skills/dreamifly-batch（项目级）
#   ./install.sh cursor     # 安装到 ~/.cursor/skills/dreamifly-batch（用户级）
#   ./install.sh .cursor    # 安装到 当前项目/.cursor/skills/dreamifly-batch（项目级）
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="dreamifly-batch"

case "$1" in
  ""|"claude")
    DEST_ROOT="$HOME/.claude/skills"
    PLATFORM="Claude Code"
    ;;
  ".claude")
    DEST_ROOT="$(pwd)/.claude/skills"
    PLATFORM="Claude Code"
    ;;
  "cursor")
    DEST_ROOT="$HOME/.cursor/skills"
    PLATFORM="Cursor"
    ;;
  ".cursor")
    DEST_ROOT="$(pwd)/.cursor/skills"
    PLATFORM="Cursor"
    ;;
  *)
    echo "用法："
    echo "  ./install.sh            # Claude Code 用户级"
    echo "  ./install.sh .claude    # Claude Code 项目级"
    echo "  ./install.sh cursor     # Cursor 用户级"
    echo "  ./install.sh .cursor    # Cursor 项目级"
    exit 2
    ;;
esac
DEST="$DEST_ROOT/$NAME"

mkdir -p "$DEST_ROOT"
# 复制源码，排除运行产物与个人登录态
rsync -a --delete \
  --exclude '.git' \
  --exclude '.cursor' \
  --exclude '.claude' \
  --exclude 'config/cookie.txt' \
  --exclude 'prompts.txt' \
  --exclude 'run.log' \
  --exclude 'done.txt' \
  --exclude 'results.jsonl' \
  --exclude 'images/*' \
  --exclude '__pycache__' \
  "$SRC/" "$DEST/"

echo "✅ 已安装到：$DEST（$PLATFORM）"
echo "下一步：复制 config/cookie.txt.example 为 config/cookie.txt 并填入你的登录态。"
echo "之后在 $PLATFORM 里说\"批量生图\"即可触发本 Skill。"
