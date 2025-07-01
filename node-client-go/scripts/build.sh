#!/bin/bash

# StreamrP2P Node Client Build Script
# Builds cross-platform binaries for the Go client

set -e

VERSION="0.1.0"
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
LDFLAGS="-X main.version=${VERSION} -X main.commit=${COMMIT}"

echo "🚀 Building StreamrP2P Node Client v${VERSION} (${COMMIT})"
echo "=================================================="

# Create build directory
mkdir -p build

# Build for current platform
echo "📦 Building for current platform..."
go build -ldflags="${LDFLAGS}" -o build/streamr-node ./cmd/streamr-node
echo "✅ Current platform: build/streamr-node"

# Cross-compile for other platforms
echo ""
echo "🌍 Cross-compiling for other platforms..."

echo "📦 Building for Linux amd64..."
GOOS=linux GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o build/streamr-node-linux-amd64 ./cmd/streamr-node
echo "✅ Linux amd64: build/streamr-node-linux-amd64"

echo "📦 Building for Windows amd64..."
GOOS=windows GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o build/streamr-node-windows-amd64.exe ./cmd/streamr-node
echo "✅ Windows amd64: build/streamr-node-windows-amd64.exe"

echo "📦 Building for macOS amd64..."
GOOS=darwin GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o build/streamr-node-darwin-amd64 ./cmd/streamr-node
echo "✅ macOS amd64: build/streamr-node-darwin-amd64"

echo "📦 Building for macOS arm64 (Apple Silicon)..."
GOOS=darwin GOARCH=arm64 go build -ldflags="${LDFLAGS}" -o build/streamr-node-darwin-arm64 ./cmd/streamr-node
echo "✅ macOS arm64: build/streamr-node-darwin-arm64"

echo ""
echo "📊 Build summary:"
ls -lh build/
echo ""
echo "🎉 All builds complete!"
echo ""
echo "🧪 Quick test of current platform binary:"
./build/streamr-node -version
echo ""
echo "📋 Next steps:"
echo "  1. Test binary: ./build/streamr-node -help"
echo "  2. Test coordinator: ./build/streamr-node -debug"  
echo "  3. Distribute to friends!" 