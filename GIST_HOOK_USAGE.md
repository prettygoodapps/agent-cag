# Git Hook for Gist README Synchronization

This repository contains a git hook script that automatically maintains a GitHub Gist mirror of your repository's README.md file. This allows you to have a public directory of your projects while keeping the actual repositories private.

## What it does

- Creates a public GitHub Gist containing your README.md content
- Installs a post-commit git hook that automatically updates the gist whenever README.md is modified
- Stores the gist ID in your git configuration for persistence
- Uses GitHub CLI for reliable gist updates

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- A GitHub account with gist permissions
- Git repository with a README.md file

## Setup

1. Copy `gh_project_gist_hook.sh` to your repository
2. Ensure you have a GitHub personal access token with gist scope in `.auth_token` file
3. Run the setup script:
   ```bash
   chmod +x gh_project_gist_hook.sh
   ./gh_project_gist_hook.sh
   ```

## What happens during setup

1. **Authentication Check**: Verifies GitHub CLI is authenticated
2. **Token Setup**: Loads GitHub token from `.auth_token` file or environment
3. **Gist Creation**: Creates a new public gist or reuses existing one
4. **Hook Installation**: Installs post-commit hook in `.git/hooks/post-commit`
5. **Configuration**: Stores gist ID in `git config gist.sync-id`

## How it works

After setup, every time you commit changes to README.md:

1. The post-commit hook detects README.md was modified
2. Uses GitHub CLI to update the corresponding gist
3. Your gist now reflects the latest README content

## Gist Information

- **Current Gist ID**: `954b925669e8d7a5dcea902fd7049d2a`
- **Gist URL**: https://gist.github.com/954b925669e8d7a5dcea902fd7049d2a
- **Description**: "Auto-synced README for [repository-name]"

## Manual Operations

View your gist:
```bash
gh gist view $(git config --get gist.sync-id)
```

Edit gist manually:
```bash
gh gist edit $(git config --get gist.sync-id) README.md
```

Check gist ID:
```bash
git config --get gist.sync-id
```

## Troubleshooting

If the hook isn't working:

1. Check if GitHub CLI is authenticated: `gh auth status`
2. Verify gist ID is stored: `git config --get gist.sync-id`
3. Test manual gist update: `gh gist edit [gist-id] README.md`
4. Check hook permissions: `ls -la .git/hooks/post-commit`

## Using in Other Repositories

To use this hook in other repositories:

1. Copy `gh_project_gist_hook.sh` to the new repository
2. Copy your `.auth_token` file (or ensure `GITHUB_GIST_TOKEN` is set)
3. Run `./gh_project_gist_hook.sh` in the new repository

Each repository will get its own unique gist with the repository name in the description.