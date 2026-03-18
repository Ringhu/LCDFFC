#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "${repo_root}/.githooks/post-commit"
git -C "${repo_root}" config core.hooksPath .githooks

echo "Installed git hooks from ${repo_root}/.githooks"
echo "post-commit auto-push is now enabled for this local clone"
