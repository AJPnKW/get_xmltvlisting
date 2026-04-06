#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/repos/get_xmltvlisting.git}"
WORK_TREE="${WORK_TREE:-$HOME/sites/iptv-sync/get_xmltvlisting}"
PUBLISH_DIR="${PUBLISH_DIR:-/srv/my_tv_movie/app/iptv-epg}"
BRANCH="${BRANCH:-main}"
BRANCH_REF="refs/heads/${BRANCH}"

log() {
  printf '[hp920-post-receive] %s\n' "$*"
}

deploy_branch() {
  mkdir -p "$WORK_TREE"
  mkdir -p "$PUBLISH_DIR"

  if [[ ! -d "$WORK_TREE/.git" ]]; then
    log "Cloning bare repo into work tree"
    git clone "$REPO_DIR" "$WORK_TREE"
  fi

  log "Refreshing work tree on ${BRANCH}"
  git -C "$WORK_TREE" fetch origin "$BRANCH"
  git -C "$WORK_TREE" checkout -B "$BRANCH" "origin/$BRANCH"
  git -C "$WORK_TREE" reset --hard "origin/$BRANCH"

  log "Publishing IPTV directory into ${PUBLISH_DIR}"
  rsync -a --delete "$WORK_TREE/IPTV/" "$PUBLISH_DIR/"

  shopt -s nullglob
  for gz_file in "$PUBLISH_DIR"/EPG_*.xml.gz; do
    xml_file="${gz_file%.gz}"
    log "Expanding $(basename "$gz_file") -> $(basename "$xml_file")"
    gzip -dc "$gz_file" > "$xml_file"
  done
  shopt -u nullglob

  local commit
  commit="$(git --git-dir="$REPO_DIR" rev-parse "$BRANCH")"

  cat > "$PUBLISH_DIR/deploy-status.json" <<EOF
{
  "branch": "${BRANCH}",
  "commit": "${commit}",
  "published_at_utc": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_repo": "${REPO_DIR}",
  "work_tree": "${WORK_TREE}",
  "publish_dir": "${PUBLISH_DIR}"
}
EOF

  log "Deployment complete at commit ${commit}"
}

handled=0
while read -r oldrev newrev refname; do
  if [[ "$refname" == "$BRANCH_REF" ]]; then
    handled=1
    deploy_branch
  fi
done

if [[ "$handled" -eq 0 ]]; then
  log "No ${BRANCH_REF} update in this push; skipping deploy"
fi
