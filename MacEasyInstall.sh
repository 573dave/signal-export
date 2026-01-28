#!/bin/bash
# Easy installation and execution script for macOS
# This script installs dependencies, exports Signal chats, and generates PDFs
# Run at your own risk. For Apple Silicon Macs, run under x86_64 architecture first:
# arch -x86_64 /bin/zsh --login

set -e  # Exit on any error

echo "===================================="
echo "Signal Export - macOS Easy Install"
echo "===================================="
echo ""

# Check if we're already in the signal-export directory
if [ ! -f "sigexport.py" ]; then
    echo "Error: sigexport.py not found. Please run this script from the signal-export directory."
    exit 1
fi

# Check for Apple Silicon and warn
if [[ $(uname -m) == 'arm64' ]]; then
    echo "⚠️  Warning: You're on Apple Silicon (M1/M2/M3)."
    echo "    If you encounter issues, run under x86_64 emulation:"
    echo "    arch -x86_64 /bin/zsh --login"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if ! pip3 install -r requirements.txt --user; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi
echo "✅ Python dependencies installed"
echo ""

# Install system dependencies via Homebrew
echo "🍺 Installing system dependencies (openssl, sqlcipher, wkhtmltopdf)..."
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install from https://brew.sh"
    exit 1
fi

if ! brew install openssl sqlcipher wkhtmltopdf; then
    echo "❌ Failed to install system dependencies"
    exit 1
fi
echo "✅ System dependencies installed"
echo ""

# Run the export
echo "📤 Exporting Signal chats to EXPORT directory..."
if ! python3 sigexport.py EXPORT; then
    echo "❌ Export failed"
    exit 1
fi
echo "✅ Export completed"
echo ""

# Generate PDFs
echo "📄 Generating PDF files..."
cd EXPORT || exit 1
mkdir -p pdf

if ! find . -maxdepth 2 -name '*.html' -exec sh -c 'for f; do echo "  Converting: $f"; wkhtmltopdf --enable-local-file-access "$f" "./pdf/$(basename "$(dirname "$f")").pdf" 2>/dev/null || echo "  ⚠️  Failed: $f"; done' _ {} +; then
    echo "⚠️  Some PDFs may have failed to generate"
else
    echo "✅ PDFs generated in EXPORT/pdf/"
fi
echo ""

# Open in Finder
echo "🎉 Done! Opening export directory..."
open . -a Finder

echo ""
echo "Export location: $(pwd)"
echo "PDFs location: $(pwd)/pdf"
