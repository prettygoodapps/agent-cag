#!/usr/bin/env bash
#
# gh_project_gist_hook.sh
#
# Sets up a post‑commit Git hook that keeps the repository’s README.md
# mirrored to a GitHub Gist.  The script is *generic*: it uses the name
# of the repo’s root directory for the Gist description and stores the
# resulting Gist ID in `git config` under `gist.sync-id`.
#
# Requirements
# ------------
# * GitHub CLI (`gh`) logged‑in to GitHub.com
# * `jq` for JSON construction
# * curl
#
# Usage
# -----
#   bash gh_project_gist_hook.sh
#
# After it runs:
#   • A personal‑access token with `gist` scope is generated (if missing)
#     and exported to your shell profile as $GITHUB_GIST_TOKEN.
#   • A Gist is created (or reused) and its ID stored in git config.
#   • A post‑commit hook `.git/hooks/post-commit` is written that
#     updates the Gist whenever README.md is committed.
#
# ----------------------------------------------------------------------

set -euo pipefail

# ---------- helpers ---------------------------------------------------
die() { echo "[ERROR] $*" >&2; exit 1; }

need_bin() { command -v "$1" >/dev/null 2>&1 || die "$1 is required"; }

# ---------- prerequisites --------------------------------------------
need_bin git
need_bin gh
need_bin jq
need_bin curl

# Validate we are inside a git repository
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "Not inside a git repo"
cd "$REPO_ROOT"

REPO_NAME=$(basename "$REPO_ROOT")
README_PATH="$REPO_ROOT/README.md"

[[ -f "$README_PATH" ]] || die "README.md not found in repo root"

echo "[*] Repository: $REPO_NAME"
echo "[*] README path: $README_PATH"

# ---------- GitHub authentication ------------------------------------
if ! gh auth status -h github.com &>/dev/null; then
    echo "[*] gh CLI not authenticated – launching interactive login..."
    gh auth login -h github.com
fi

# Ensure we have a gist‑scoped token
if [[ -z "${GITHUB_GIST_TOKEN:-}" ]]; then
    echo "[*] No GITHUB_GIST_TOKEN present – loading from .auth_token"
    if [[ -f ".auth_token" ]]; then
        TOKEN=$(<".auth_token")
        export GITHUB_GIST_TOKEN="$TOKEN"
        
        # Add to shell profile for persistence
        SHELL_PROFILE=""
        if [[ -f "$HOME/.bashrc" ]]; then
            SHELL_PROFILE="$HOME/.bashrc"
        elif [[ -f "$HOME/.zshrc" ]]; then
            SHELL_PROFILE="$HOME/.zshrc"
        fi
        
        if [[ -n "$SHELL_PROFILE" ]] && ! grep -q "GITHUB_GIST_TOKEN" "$SHELL_PROFILE"; then
            echo "export GITHUB_GIST_TOKEN=$TOKEN" >> "$SHELL_PROFILE"
            echo "[*] Token added to $SHELL_PROFILE (reload your shell to persist)"
        fi
        echo "[*] Using token from .auth_token file"
    else
        die "No GITHUB_GIST_TOKEN env var and no .auth_token file found"
    fi
else
    echo "[*] Using existing GITHUB_GIST_TOKEN from environment"
fi

# ---------- Gist creation / retrieval --------------------------------
GIST_ID=$(git config --get gist.sync-id || true)

if [[ -z "$GIST_ID" ]]; then
    echo "[*] Creating new Gist for README.md"
    GIST_ID=$(gh gist create "$README_PATH" --public \
              --desc "Auto-synced README for $REPO_NAME" | grep -o 'https://gist.github.com/[^/]*/[a-f0-9]*' | sed 's|.*/||')
    
    if [[ -n "$GIST_ID" ]]; then
        git config gist.sync-id "$GIST_ID"
        echo "[*] Gist created with ID: $GIST_ID"
    else
        die "Failed to create gist"
    fi
else
    echo "[*] Existing Gist ID found in git config: $GIST_ID"
    # Verify the gist still exists
    if ! gh gist view "$GIST_ID" &>/dev/null; then
        echo "[*] Existing gist no longer accessible, creating new one..."
        GIST_ID=$(gh gist create "$README_PATH" --public \
                  --desc "Auto-synced README for $REPO_NAME" | grep -o 'https://gist.github.com/[^/]*/[a-f0-9]*' | sed 's|.*/||')
        git config gist.sync-id "$GIST_ID"
        echo "[*] New Gist created with ID: $GIST_ID"
    fi
fi

# ---------- Hook installation ----------------------------------------
HOOK_PATH="$REPO_ROOT/.git/hooks/post-commit"

cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
# Post-commit hook: update Gist when README.md changes

set -euo pipefail

README_FILE="README.md"
GIST_ID=$(git config --get gist.sync-id 2>/dev/null || true)

# Skip if prerequisites are missing
command -v gh >/dev/null 2>&1 || { echo "[HOOK] gh CLI missing – skip"; exit 0; }

# Only proceed if README.md was part of the last commit
if git diff-tree --no-commit-id --name-only -r HEAD | grep -q "^${README_FILE}$"; then
    if [[ -z "$GIST_ID" ]]; then
        echo "[HOOK] No gist.sync-id in git config – abort"
        exit 0
    fi

    if [[ ! -f "$README_FILE" ]]; then
        echo "[HOOK] README.md not found – skip"
        exit 0
    fi

    # Use GitHub CLI to update the gist - more reliable than curl
    if gh gist edit "$GIST_ID" "$README_FILE" 2>/dev/null; then
        echo "[HOOK] README.md synced to Gist $GIST_ID"
    else
        echo "[HOOK] Failed to sync README.md to Gist $GIST_ID"
    fi
fi
HOOK

chmod +x "$HOOK_PATH"
echo "[*] Post‑commit hook installed at .git/hooks/post-commit"

echo "[DONE] README will now auto‑sync to Gist on every commit."
