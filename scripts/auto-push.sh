#!/bin/bash
# Auto-push script for Git - commits and pushes changes automatically
# Usage: ./scripts/auto-push.sh "Your commit message"

MESSAGE="${1:-Auto-commit: $(date +'%Y-%m-%d %H:%M:%S')}"
BRANCH="${2:-main}"

REPO_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_PATH"

echo "📁 Working in: $REPO_PATH"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed"
    exit 1
fi

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "❌ Not a git repository"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
echo "🌿 Current branch: $CURRENT_BRANCH"

# Check for changes
if git diff-index --quiet HEAD --; then
    echo "✅ No changes to commit"
    exit 0
fi

echo "📝 Changes detected:"
git status --short

# Stage all changes
echo "📦 Staging changes..."
git add .

# Commit
echo "💾 Committing with message: '$MESSAGE'"
git commit -m "$MESSAGE"

if [ $? -ne 0 ]; then
    echo "❌ Commit failed"
    exit 1
fi

# Push
echo "🚀 Pushing to origin/$CURRENT_BRANCH..."
git push origin "$CURRENT_BRANCH"

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
else
    echo "❌ Push failed"
    exit 1
fi
