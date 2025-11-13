#!/bin/bash
# Build script for Derpy

set -e  # Exit on error

echo "🔨 Building Derpy package..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Install build dependencies
echo "Installing build dependencies..."
pip install --upgrade build wheel

# Build the package
echo "Building package..."
python -m build

echo "✅ Build complete! Package files are in dist/"
echo ""
echo "To install locally:"
echo "  pip install dist/derpy-0.1.0-py3-none-any.whl"
echo ""
echo "Or install in development mode:"
echo "  pip install -e ."
