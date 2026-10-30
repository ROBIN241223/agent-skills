#!/usr/bin/env bash
# Cài bộ skill vào thư mục skill của agent.
#
# Dùng:
#   ./install.sh                          # mặc định ~/.agents/skills, tạo symlink
#   ./install.sh ~/.config/opencode/skills
#   ./install.sh --copy ~/.claude/skills
set -euo pipefail

MODE="link"
TARGET="${HOME}/.agents/skills"

for arg in "$@"; do
  case "$arg" in
    --copy) MODE="copy" ;;
    --link) MODE="link" ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    -*)
      echo "Tham số không hợp lệ: $arg" >&2
      exit 1
      ;;
    *)
      TARGET="$arg"
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SCRIPT_DIR}/../skills"

if [ ! -d "$SOURCE" ]; then
  echo "Không tìm thấy thư mục skills tại: $SOURCE" >&2
  exit 1
fi

mkdir -p "$TARGET"

echo "Nguồn : $SOURCE"
echo "Đích  : $TARGET"
echo "Mode  : $MODE"
echo

installed=0
skipped=0
failed=0

for skill_path in "$SOURCE"/*/; do
  name="$(basename "$skill_path")"
  dest="${TARGET}/${name}"

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ -L "$dest" ]; then
      rm -f "$dest"
    else
      echo "  [bỏ qua] ${name} đã tồn tại và không phải symlink"
      skipped=$((skipped + 1))
      continue
    fi
  fi

  if [ "$MODE" = "copy" ]; then
    cp -R "$skill_path" "$dest"
  else
    if ! ln -s "$(cd "$skill_path" && pwd)" "$dest" 2>/dev/null; then
      echo "  [copy]   ${name} (không tạo được symlink)"
      cp -R "$skill_path" "$dest"
    fi
  fi

  echo "  [ok]     ${name}"
  installed=$((installed + 1))
done

echo
echo "Hoàn tất: ${installed} cài đặt, ${skipped} bỏ qua, ${failed} lỗi."
echo "Khởi động lại agent để nạp skill mới."
