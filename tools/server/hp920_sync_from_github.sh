#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/AJPnKW/get_xmltvlisting.git}"
WORK_TREE="${WORK_TREE:-$HOME/sites/iptv-sync/get_xmltvlisting}"
PUBLISH_DIR="${PUBLISH_DIR:-/srv/my_tv_movie/app/iptv-epg}"
BRANCH="${BRANCH:-main}"

log() {
  printf '[hp920-sync] %s\n' "$*"
}

mkdir -p "$(dirname "$WORK_TREE")"
mkdir -p "$PUBLISH_DIR"

if [[ ! -d "$WORK_TREE/.git" ]]; then
  log "Cloning ${REPO_URL} into ${WORK_TREE}"
  git clone --branch "$BRANCH" "$REPO_URL" "$WORK_TREE"
fi

log "Refreshing ${WORK_TREE} on ${BRANCH}"
git -C "$WORK_TREE" fetch origin "$BRANCH"
git -C "$WORK_TREE" checkout -B "$BRANCH" "origin/$BRANCH"
git -C "$WORK_TREE" reset --hard "origin/$BRANCH"

log "Publishing IPTV assets to ${PUBLISH_DIR}"
rsync -a --delete "$WORK_TREE/IPTV/" "$PUBLISH_DIR/"

shopt -s nullglob
for gz_file in "$PUBLISH_DIR"/EPG_*.xml.gz; do
  xml_file="${gz_file%.gz}"
  log "Expanding $(basename "$gz_file") -> $(basename "$xml_file")"
  gzip -dc "$gz_file" > "$xml_file"
done
shopt -u nullglob

cat > "$PUBLISH_DIR/deploy-status.json" <<EOF
{
  "branch": "${BRANCH}",
  "published_at_utc": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "repo_url": "${REPO_URL}",
  "work_tree": "${WORK_TREE}",
  "publish_dir": "${PUBLISH_DIR}",
  "commit": "$(git -C "$WORK_TREE" rev-parse HEAD)"
}
EOF

log "Sync complete"
