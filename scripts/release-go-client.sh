#!/bin/bash

# StreamrP2P Go Client Release Script
# Usage: ./scripts/release-go-client.sh v0.1.0

set -e

VERSION="$1"
if [ -z "$VERSION" ]; then
    echo "❌ Usage: $0 <version>"
    echo "   Example: $0 v0.1.0"
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    echo "❌ Invalid version format. Use: v1.2.3 or v1.2.3-beta"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GO_CLIENT_DIR="$PROJECT_ROOT/node-client-go"

echo "🚀 StreamrP2P Go Client Release Script"
echo "======================================="
echo "📦 Version: $VERSION"
echo "📁 Project Root: $PROJECT_ROOT"
echo "🛠️ Go Client Dir: $GO_CLIENT_DIR"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Navigate to Go client directory
cd "$GO_CLIENT_DIR"

# Check if Go module exists
if [ ! -f go.mod ]; then
    echo "❌ go.mod not found in $GO_CLIENT_DIR"
    exit 1
fi

# Get commit hash
COMMIT=$(git rev-parse --short HEAD)
echo "📝 Commit: $COMMIT"

# Check if tag already exists
if git tag -l | grep -q "go-client-$VERSION"; then
    echo "❌ Tag go-client-$VERSION already exists"
    exit 1
fi

# Build binaries
echo ""
echo "🔨 Building cross-platform binaries..."
mkdir -p dist
rm -rf dist/*

LDFLAGS="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT}"

echo "📦 Building for Linux amd64 (static)..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/streamr-node-linux-amd64 ./cmd/streamr-node

echo "📦 Building for Windows amd64 (static)..."
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/streamr-node-windows-amd64.exe ./cmd/streamr-node

echo "📦 Building for macOS Intel (static)..."
CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/streamr-node-macos-intel ./cmd/streamr-node

echo "📦 Building for macOS Apple Silicon (static)..."
CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags="${LDFLAGS}" -o dist/streamr-node-macos-m1 ./cmd/streamr-node

echo ""
echo "📊 Build Results:"
ls -lh dist/

# Generate checksums
echo ""
echo "🔒 Generating SHA256 checksums..."
cd dist
sha256sum * > checksums.txt
echo "✅ Checksums:"
cat checksums.txt

cd ..

# Test binary
echo ""
echo "🧪 Testing Linux binary..."
if ./dist/streamr-node-linux-amd64 -version; then
    echo "✅ Binary test passed!"
else
    echo "❌ Binary test failed!"
    exit 1
fi

# Create release notes
echo ""
echo "📝 Creating release notes..."
cat > release_notes.md << EOF
# StreamrP2P Node Client ${VERSION}

🚀 **Single binary P2P streaming node client** - 24x better friend experience!

## 📥 Downloads

Choose the binary for your operating system:

| Platform | Download | Size |
|----------|----------|------|
| **Windows** | \`streamr-node-windows-amd64.exe\` | ~5MB |
| **macOS Intel** | \`streamr-node-macos-intel\` | ~5MB |
| **macOS Apple Silicon** | \`streamr-node-macos-m1\` | ~5MB |
| **Linux** | \`streamr-node-linux-amd64\` | ~5MB |

## 🎯 Key Benefits

- ✅ **Single binary** - no Docker, no Python, no dependencies
- ✅ **Cross-platform** - native Windows, macOS, Linux support  
- ✅ **Tiny size** - ~5MB vs 200MB+ Docker setup
- ✅ **Instant startup** - no container overhead
- ✅ **Zero config** - connects to coordinator automatically

## 🚀 Quick Start

### Windows
1. Download \`streamr-node-windows-amd64.exe\`
2. Double-click to run, or open Command Prompt and run: \`streamr-node-windows-amd64.exe -help\`

### macOS  
1. Download \`streamr-node-macos-intel\` or \`streamr-node-macos-m1\`
2. Open Terminal and run: \`./streamr-node-macos-intel -help\`

### Linux
1. Download \`streamr-node-linux-amd64\`
2. Make executable: \`chmod +x streamr-node-linux-amd64\`
3. Run: \`./streamr-node-linux-amd64 -help\`

## 🔒 Security

- All binaries are statically linked with no external dependencies
- SHA256 checksums provided in \`checksums.txt\`
- Built from commit \`${COMMIT}\`

## 📋 Next Steps

This is **Phase 0: Foundation**. Coming next:
- 🚧 RTMP server integration  
- 🚧 Node registration/heartbeat system
- 🚧 Stream relay functionality

**Goal**: 24x improvement in friend installation success (5% → 85%+)

---

Built with Go 1.23 • Commit ${COMMIT}
EOF

echo "✅ Release notes created: release_notes.md"

# Summary
echo ""
echo "🎉 Release preparation complete!"
echo "📦 Version: $VERSION"  
echo "📝 Commit: $COMMIT"
echo "📁 Binaries: dist/"
echo "📝 Release notes: release_notes.md"
echo ""

# Prompt for next steps
echo "🔄 Next steps:"
echo "1. Review the binaries and release notes"
echo "2. Test the binaries on different platforms"
echo "3. Tag and push to trigger GitHub release:"
echo "   git tag go-client-$VERSION"
echo "   git push origin go-client-$VERSION"
echo ""
echo "Or create a manual GitHub release and upload files from dist/"
echo ""

read -p "🏷️  Create and push git tag now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏷️  Creating git tag..."
    git tag "go-client-$VERSION"
    
    echo "📤 Pushing tag to origin..."
    git push origin "go-client-$VERSION"
    
    echo ""
    echo "✅ Tag pushed! GitHub Actions will now create the release."
    echo "🔗 Check progress at: https://github.com/iddv/streamr/actions"
    echo "📦 Release will be available at: https://github.com/iddv/streamr/releases/tag/go-client-$VERSION"
else
    echo "ℹ️  Tag not created. Run manually when ready:"
    echo "   git tag go-client-$VERSION && git push origin go-client-$VERSION"
fi 