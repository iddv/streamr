# 🚀 StreamrP2P Node Client (Go)

**Single binary P2P streaming node client** - 24x better friend experience!

## 🎯 Key Benefits

- ✅ **Single binary** - no Docker, no Python, no dependencies
- ✅ **Cross-platform** - native Windows, macOS, Linux support  
- ✅ **Tiny size** - ~5MB vs 200MB+ Docker setup
- ✅ **Instant startup** - no container overhead
- ✅ **Zero config** - connects to coordinator automatically

## 📥 Downloads

### Option 1: GitHub Releases (Recommended)

**Latest Release**: [Download Here](https://github.com/iddv/streamr/releases/latest)

Choose the binary for your operating system:

| Platform | Download File | Size |
|----------|---------------|------|
| **Windows** | `streamr-node-windows-amd64.exe` | ~5MB |
| **macOS Intel** | `streamr-node-macos-intel` | ~5MB |
| **macOS Apple Silicon** | `streamr-node-macos-m1` | ~5MB |
| **Linux** | `streamr-node-linux-amd64` | ~5MB |

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/iddv/streamr.git
cd streamr/node-client-go

# Build for your platform
go build -o streamr-node ./cmd/streamr-node

# Or build for all platforms
./scripts/build.sh
```

## 🚀 Quick Start

### Windows
1. **Download**: Get `streamr-node-windows-amd64.exe` from the [latest release](https://github.com/iddv/streamr/releases/latest)
2. **Run**: Double-click the `.exe` file, or open Command Prompt and run:
   ```cmd
   streamr-node-windows-amd64.exe -help
   ```

### macOS
1. **Download**: Get `streamr-node-macos-intel` or `streamr-node-macos-m1` from the [latest release](https://github.com/iddv/streamr/releases/latest)
2. **Allow execution**: macOS may block the binary. Go to System Preferences → Security & Privacy and click "Allow"
3. **Run**: Open Terminal and run:
   ```bash
   ./streamr-node-macos-intel -help
   ```

### Linux
1. **Download**: Get `streamr-node-linux-amd64` from the [latest release](https://github.com/iddv/streamr/releases/latest)
2. **Make executable**:
   ```bash
   chmod +x streamr-node-linux-amd64
   ```
3. **Run**:
   ```bash
   ./streamr-node-linux-amd64 -help
   ```

## 📋 Usage

### Basic Commands

```bash
# Show help
./streamr-node -help

# Show version info
./streamr-node -version

# Test coordinator connection
./streamr-node -debug

# Connect to custom coordinator
./streamr-node -coordinator http://your-coordinator.com
```

### Available Flags

- `-help` - Show help message
- `-version` - Show version and build info
- `-debug` - Enable debug logging
- `-coordinator <url>` - Custom coordinator URL (default: production)

## 🔒 Security

### Verifying Downloads

Each release includes a `checksums.txt` file with SHA256 hashes:

```bash
# Linux/macOS: Verify checksum
sha256sum streamr-node-linux-amd64
# Compare with checksums.txt

# Windows: Verify checksum (PowerShell)
Get-FileHash streamr-node-windows-amd64.exe -Algorithm SHA256
# Compare with checksums.txt
```

### Binary Safety
- All binaries are **statically linked** with no external dependencies
- Built from **verified source code** with reproducible builds
- No network access required except to coordinator API
- **No elevated permissions** needed to run

## 🏗️ Development

### Project Structure

```
node-client-go/
├── cmd/streamr-node/        # Main application entry point
├── internal/
│   ├── coordinator/         # Coordinator API client
│   ├── config/             # Configuration management
│   └── logging/            # Structured logging
├── go.mod                  # Go module definition
├── go.sum                  # Dependency lock file
└── README.md               # This file
```

### Building

```bash
# Development build
go build -o streamr-node ./cmd/streamr-node

# Production build (optimized)
go build -ldflags="-s -w" -o streamr-node ./cmd/streamr-node

# Cross-compile for all platforms
./scripts/build.sh
```

### Testing

```bash
# Run all tests
go test ./...

# Test with coverage
go test -cover ./...

# Test specific package
go test ./internal/coordinator
```

## 📦 Release Process

### For Maintainers

#### Creating a Release

```bash
# Tag the release
git tag go-client-v0.1.0
git push origin go-client-v0.1.0

# GitHub Actions will automatically:
# 1. Build cross-platform binaries
# 2. Generate checksums
# 3. Create GitHub release
# 4. Upload all assets
```

#### Manual Release (if needed)

```bash
# Build all platforms
./scripts/build.sh

# Create release manually through GitHub UI
# Upload files from dist/ directory
```

### Versioning

We use semantic versioning with a `go-client-` prefix:
- `go-client-v0.1.0` - Initial release
- `go-client-v0.1.1` - Patch release  
- `go-client-v0.2.0` - Minor release
- `go-client-v1.0.0` - Major release

## 🌟 Roadmap

### Phase 0: Foundation ✅
- [x] CLI interface and flags
- [x] Coordinator health check
- [x] Cross-platform builds
- [x] GitHub releases automation

### Phase 1: Core RTMP 🚧
- [ ] RTMP server integration
- [ ] Node registration/heartbeat
- [ ] Stream relay functionality
- [ ] End-to-end coordinator integration

### Phase 2: P2P Features 🔮
- [ ] Peer discovery and connection
- [ ] Chunk distribution algorithm
- [ ] Bandwidth optimization
- [ ] Economic incentives integration

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Code Standards
- Follow Go conventions and `go fmt`
- Add tests for new functionality
- Update documentation for user-facing changes
- Keep commits atomic and well-described

## 📞 Support

- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check the [main project docs](../README.md)
- **Status Updates**: See [CURRENT_STATUS.md](../CURRENT_STATUS.md)

---

**Goal**: 24x improvement in friend installation success (5% → 85%+)

*Built with Go 1.23 • Powered by StreamrP2P* 