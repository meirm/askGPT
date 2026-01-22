#!/bin/bash
# Release script for askGPT
# This script builds and releases the askGPT package

set -e

# Get version from pyproject.toml
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo "Error: Could not determine version from pyproject.toml"
    exit 1
fi

echo "=========================================="
echo "askGPT Release Script"
echo "Version: $VERSION"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Run this script from the project root."
    exit 1
fi

# Check if version matches in __init__.py
INIT_VERSION=$(grep -E '__version__ = ' src/askgpt/__init__.py | sed "s/__version__ = \"\(.*\)\"/\1/")
if [ "$VERSION" != "$INIT_VERSION" ]; then
    echo "Warning: Version mismatch!"
    echo "  pyproject.toml: $VERSION"
    echo "  __init__.py: $INIT_VERSION"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes."
    git status --short
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists"
    exit 1
fi

echo "Step 1: Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/
echo "✓ Cleaned"

echo ""
echo "Step 2: Building package with uv..."
uv build
echo "✓ Built"

echo ""
echo "Step 3: Verifying build..."
# uv build already validates the package, but we can also check with twine if available
if command -v twine &> /dev/null; then
    twine check dist/*
    echo "✓ Verified with twine"
else
    echo "✓ Verified (twine not available, but uv build completed successfully)"
fi

echo ""
echo "Step 4: Creating git tag..."
git tag -a "v$VERSION" -m "Release version $VERSION"
echo "✓ Tagged v$VERSION"

echo ""
echo "=========================================="
echo "Release $VERSION ready!"
echo "=========================================="
echo ""
echo "Built files:"
ls -lh dist/
echo ""
echo "Next steps:"
echo "  1. Review the built files: ls -lh dist/"
echo "  2. Test the package locally: uv tool install dist/askgpt-${VERSION}-py3-none-any.whl"
echo "  3. Push the tag: git push origin v$VERSION"
echo "  4. Upload to PyPI: uv publish"
echo ""
echo "Or run with --upload to automatically upload to PyPI:"
echo "  ./release.sh --upload"
echo ""

# Check if --upload flag is set
if [ "$1" == "--upload" ]; then
    echo "Uploading to PyPI with uv..."
    read -p "Are you sure you want to upload to PyPI? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv publish
        echo ""
        echo "✓ Uploaded to PyPI"
        echo ""
        echo "Release $VERSION is now live on PyPI!"
    else
        echo "Upload cancelled"
    fi
fi
