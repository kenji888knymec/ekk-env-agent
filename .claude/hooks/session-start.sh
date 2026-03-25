#!/bin/bash
set -euo pipefail

# EKK環境管理課 社内規定専門チーム — セッション起動フック
# docs/regulations/ ディレクトリを整備し、社内規定PDFを配置する

REGULATIONS_DIR="${CLAUDE_PROJECT_DIR}/docs/regulations"

# docs/regulations/ ディレクトリが存在しない場合は作成
mkdir -p "$REGULATIONS_DIR"

# リポジトリルートにあるPDFをdocs/regulations/へコピー（未配置のもののみ）
for pdf in "${CLAUDE_PROJECT_DIR}"/*.pdf; do
  [ -f "$pdf" ] || continue
  filename=$(basename "$pdf")
  if [ ! -f "${REGULATIONS_DIR}/${filename}" ]; then
    cp "$pdf" "${REGULATIONS_DIR}/${filename}"
    echo "[session-start] コピー完了: ${filename} → docs/regulations/"
  fi
done

# 配置済みPDF一覧を出力
pdf_count=$(find "$REGULATIONS_DIR" -maxdepth 1 -name "*.pdf" | wc -l)
echo "[session-start] docs/regulations/ に社内規定PDF ${pdf_count} 件を確認しました。"
echo "[session-start] 社内規定専門チームが起動時に自動読み込みを行います。"
