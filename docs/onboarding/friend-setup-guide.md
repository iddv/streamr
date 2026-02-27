# Friend Node Setup Guide

Get your StreamrP2P friend node running in under 10 minutes. You'll download a single binary, create a small config file, and start relaying streams for your friend.

## Prerequisites

- A stream key from the streamer you're supporting (they'll send it to you)
- The coordinator URL (the streamer will provide this too)
- An internet connection with at least 5 Mbps upload

## Step 1: Download the Binary

### macOS

```bash
# Apple Silicon (M1/M2/M3)
curl -L -o streamr-node https://github.com/streamrp2p/node-client-go/releases/latest/download/streamr-node-darwin-arm64
chmod +x streamr-node

# Intel Mac
curl -L -o streamr-node https://github.com/streamrp2p/node-client-go/releases/latest/download/streamr-node-darwin-amd64
chmod +x streamr-node
```

### Windows

Download `streamr-node-windows-amd64.exe` from the [latest release](https://github.com/streamrp2p/node-client-go/releases/latest) and save it somewhere convenient (e.g. `C:\streamr\`).

### Linux

```bash
# x86_64
curl -L -o streamr-node https://github.com/streamrp2p/node-client-go/releases/latest/download/streamr-node-linux-amd64
chmod +x streamr-node

# ARM64 (Raspberry Pi 4, etc.)
curl -L -o streamr-node https://github.com/streamrp2p/node-client-go/releases/latest/download/streamr-node-linux-arm64
chmod +x streamr-node
```

## Step 2: Create Your Config

Create the config directory and file:

### macOS / Linux

```bash
mkdir -p ~/.streamr
cat > ~/.streamr/config.yaml << 'EOF'
coordinator_url: "https://coordinator.example.com"
stream_key: "YOUR_STREAM_KEY_HERE"
node_name: "your-name-node"
serve_port: 8080
log_level: "info"
heartbeat_interval: 30
max_buffer_segments: 30
max_concurrent_viewers: 10
EOF
```

### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.streamr"
@"
coordinator_url: "https://coordinator.example.com"
stream_key: "YOUR_STREAM_KEY_HERE"
node_name: "your-name-node"
serve_port: 8080
log_level: "info"
heartbeat_interval: 30
max_buffer_segments: 30
max_concurrent_viewers: 10
"@ | Out-File -FilePath "$env:USERPROFILE\.streamr\config.yaml" -Encoding utf8
```

Replace `YOUR_STREAM_KEY_HERE` with the key your streamer friend gave you, and update `coordinator_url` to point to their coordinator.

### Config Reference

| Field | Default | Description |
|---|---|---|
| `coordinator_url` | `http://localhost:8000` | Coordinator API address |
| `stream_key` | (required) | Auth key from the streamer |
| `node_name` | (auto) | Display name for your node |
| `serve_port` | `8080` | Local port for serving HLS to viewers |
| `log_level` | `info` | Logging verbosity: debug, info, warn, error |
| `heartbeat_interval` | `30` | Seconds between heartbeats |
| `max_buffer_segments` | `30` | HLS segments to keep in memory |
| `max_concurrent_viewers` | `10` | Max viewers your node will serve |

## Step 3: Run the Node

### macOS / Linux

```bash
./streamr-node
```

### Windows

```powershell
.\streamr-node-windows-amd64.exe
```

You can also override config values with CLI flags:

```bash
./streamr-node -coordinator https://coordinator.example.com -stream-key YOUR_KEY -name my-node
```

## Step 4: Verify Connection

When the node starts successfully, you'll see output like:

```
{"level":"info","msg":"Registered with coordinator","node_id":"your-name-node","stream_id":"..."}
{"level":"info","msg":"Heartbeat loop started","interval":"30s"}
{"level":"info","msg":"HLS fetcher started","stream_id":"..."}
{"level":"info","msg":"HLS server listening","port":8080}
```

You can verify locally by opening `http://localhost:8080/live/{stream_id}/index.m3u8` in VLC or a browser.

Check your node status on the streamer's dashboard — your node should appear as "active" within 30 seconds.

## Step 5: Keep It Running

For long-running support, consider running the node in the background:

### macOS / Linux (systemd)

```bash
# Create a systemd service (Linux)
sudo tee /etc/systemd/system/streamr-node.service << EOF
[Unit]
Description=StreamrP2P Friend Node
After=network.target

[Service]
ExecStart=/path/to/streamr-node
Restart=always
RestartSec=10
User=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable streamr-node
sudo systemctl start streamr-node
```

### macOS (launchd)

```bash
cat > ~/Library/LaunchAgents/com.streamrp2p.node.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.streamrp2p.node</string>
    <key>ProgramArguments</key>
    <array><string>/path/to/streamr-node</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.streamrp2p.node.plist
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task → name it "StreamrP2P Node"
3. Trigger: "When the computer starts"
4. Action: Start a program → browse to `streamr-node-windows-amd64.exe`
5. Finish

## Troubleshooting

### "Connection refused" or "Coordinator unreachable"

- Verify the `coordinator_url` is correct and reachable: `curl https://coordinator.example.com/health`
- Check your internet connection
- If behind a corporate proxy, the node may not be able to reach the coordinator

### "Authentication failed" or "Invalid stream key"

- Double-check the `stream_key` in your config — copy-paste it exactly
- Ask the streamer to regenerate the key if it's expired
- Make sure there are no extra spaces or quotes around the key

### Firewall blocking connections

- The node needs outbound HTTPS (port 443) to reach the coordinator
- Port 8080 (or your configured `serve_port`) needs to be open for incoming viewer connections
- On macOS, allow the binary through the firewall when prompted
- On Windows, allow through Windows Defender Firewall when prompted
- On Linux: `sudo ufw allow 8080/tcp` (if using UFW)

### VPN mesh connection issues

- The node uses WireGuard (UDP port 41641) for the VPN mesh
- Ensure UDP 41641 is not blocked by your router or firewall
- If on a restrictive network, try a different network (mobile hotspot works)

### Node shows "inactive" on dashboard

- Check that the stream is currently LIVE
- Verify heartbeats are being sent (look for heartbeat log messages)
- Restart the node: `Ctrl+C` then run it again

### High CPU or memory usage

- Reduce `max_concurrent_viewers` in your config (try 5)
- Reduce `max_buffer_segments` (try 15)
- Check your upload bandwidth — if saturated, the node will struggle

### Getting help

- Ask the streamer for their Discord/chat link
- Check the logs: run with `-log-level debug` for verbose output
- File an issue at the project repository
