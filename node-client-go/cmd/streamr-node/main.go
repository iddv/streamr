package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/iddv/streamr/node-client-go/internal/bandwidth"
	"github.com/iddv/streamr/node-client-go/internal/config"
	"github.com/iddv/streamr/node-client-go/internal/coordinator"
	"github.com/iddv/streamr/node-client-go/internal/hls"
	"github.com/iddv/streamr/node-client-go/internal/logging"
	"github.com/iddv/streamr/node-client-go/internal/mesh"
)

var (
	version = "0.1.0"
	commit  = "dev"
)

func main() {
	// Handle -version and -help before config loading (check os.Args directly
	// to avoid conflicting with the config loader's FlagSet)
	for _, arg := range os.Args[1:] {
		switch arg {
		case "-help", "--help":
			printHelp()
			return
		case "-version", "--version":
			fmt.Printf("StreamrP2P Node Client v%s (%s)\n", version, commit)
			return
		}
	}

	// 1. Load config (task 3.1)
	cfg, err := config.Load()
	if err != nil {
		logrus.WithError(err).Fatal("Failed to load configuration")
	}

	// 2. Setup structured logging (task 3.9)
	logging.SetupLogger(cfg.LogLevel)

	// Generate a node ID from node name or hostname
	nodeID := cfg.NodeName
	if nodeID == "" {
		hostname, _ := os.Hostname()
		nodeID = hostname
	}

	log := logging.NewLogger(nodeID, "")

	log.WithFields(logrus.Fields{
		"version":         version,
		"commit":          commit,
		"coordinator_url": cfg.CoordinatorURL,
		"operation":       "startup",
	}).Info("Starting StreamrP2P Node Client")

	// Validate required config
	if cfg.StreamKey == "" {
		log.Fatal("stream_key is required. Set it in ~/.streamr/config.yaml or via -stream-key flag")
	}

	// 3. Register with coordinator (task 3.2)
	client := coordinator.NewClient(cfg.CoordinatorURL, nodeID, cfg.HeartbeatInterval, log)
	regResp, err := client.Register(nodeID, cfg.StreamKey)
	if err != nil {
		log.WithField("operation", "register").WithError(err).Fatal("Failed to register with coordinator")
	}

	// Update logger with stream_id now that we have it
	log = logging.NewLogger(nodeID, regResp.StreamID)
	log.WithField("operation", "startup").Info("Registered with coordinator successfully")

	// Set stats URL for heartbeats
	statsURL := fmt.Sprintf("http://localhost:%d", cfg.ServePort)
	client.SetStatsURL(statsURL)

	// Join VPN mesh if Headscale auth key was provided (task 4.5)
	var meshNode *mesh.MeshNode
	if regResp.HeadscaleAuthKey != "" {
		headscaleURL := regResp.HeadscaleURL
		if cfg.HeadscaleURL != "" {
			headscaleURL = cfg.HeadscaleURL
			log.WithField("operation", "mesh_join").Infof("Using CLI override for Headscale URL: %s", headscaleURL)
		}

		// Fetch and install Headscale TLS cert (self-signed) before joining mesh
		certPEM, err := client.FetchHeadscaleCert()
		if err != nil {
			log.WithField("operation", "mesh_join").WithError(err).Warn("Failed to fetch Headscale TLS cert")
		} else if len(certPEM) > 0 {
			if err := mesh.InstallCert(certPEM, log); err != nil {
				log.WithField("operation", "mesh_join").WithError(err).Warn("Failed to install Headscale TLS cert")
			}
		}

		meshNode = mesh.NewMeshNode(log)
		meshCtx, meshCancel := context.WithTimeout(context.Background(), 60*time.Second)
		err = meshNode.Join(meshCtx, regResp.HeadscaleAuthKey, nodeID, headscaleURL)
		meshCancel()
		if err != nil {
			log.WithField("operation", "mesh_join").WithError(err).Warn("Failed to join VPN mesh — continuing without mesh")
		} else {
			vpnIP := meshNode.VPNIP()
			client.SetVPNIP(vpnIP)
			log.WithFields(logrus.Fields{
				"operation": "mesh_join",
				"vpn_ip":    vpnIP,
			}).Info("VPN mesh joined, IP reported in heartbeats")
		}
	} else {
		log.WithField("operation", "startup").Info("No Headscale auth key — skipping VPN mesh")
	}

	// Create shared segment buffer
	buffer := hls.NewSegmentBuffer(cfg.MaxBufferSegments)

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())

	// 4. Start heartbeat loop in goroutine (task 3.3)
	go client.HeartbeatLoop(ctx)

	// 5. Start HLS fetcher in goroutine (task 3.5)
	srsURL := cfg.SRSURL
	if srsURL == "" {
		// Derive SRS URL from coordinator URL by switching to port 8080
		srsURL = cfg.CoordinatorURL
		// If coordinator is on default port 80 or explicit, replace with 8080
		if strings.Contains(srsURL, ":80/") || strings.HasSuffix(srsURL, ":80") {
			srsURL = strings.Replace(srsURL, ":80", ":8080", 1)
		} else if !strings.Contains(srsURL[8:], ":") {
			// No port specified — append :8080
			srsURL = strings.TrimRight(srsURL, "/") + ":8080"
		}
	}
	fetcher := hls.NewFetcher(srsURL, regResp.StreamID, buffer, log)
	go fetcher.Start(ctx)

	// 6. Start HLS server in goroutine (task 3.6 + 3.8)
	server := hls.NewServer(buffer, cfg.ServePort, regResp.StreamID, cfg.MaxViewers, log)
	go server.Start(ctx)

	// 7. Start bandwidth reporter in goroutine (task 3.7)
	reporter := bandwidth.NewReporter(
		client,
		regResp.StreamID,
		fetcher.BytesFromSRS,
		server.BytesToViewers,
		log,
	)
	go reporter.Start(ctx)

	log.WithFields(logrus.Fields{
		"operation":  "startup",
		"hls_port":   cfg.ServePort,
		"stream_id":  regResp.StreamID,
		"max_viewers": cfg.MaxViewers,
	}).Info("All services started")

	// 8. Wait for SIGINT/SIGTERM (task 3.4)
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh

	log.WithFields(logrus.Fields{
		"operation": "shutdown",
		"signal":    sig.String(),
	}).Info("Shutdown signal received")

	// 9. Cancel context, deregister, drain connections
	cancel()

	// Close VPN mesh if connected
	if meshNode != nil {
		if err := meshNode.Close(); err != nil {
			log.WithField("operation", "shutdown").WithError(err).Warn("Failed to close VPN mesh")
		}
	}

	// Deregister from coordinator
	if err := client.Deregister(); err != nil {
		log.WithField("operation", "shutdown").WithError(err).Warn("Failed to deregister from coordinator")
	}

	// Give 5 seconds for connections to drain
	drainCtx, drainCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer drainCancel()

	<-drainCtx.Done()

	log.WithField("operation", "shutdown").Info("StreamrP2P Node Client stopped")
}

func printHelp() {
	fmt.Println("StreamrP2P Node Client - Help relay friends' streams and earn rewards!")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  streamr-node [options]")
	fmt.Println()
	fmt.Println("Options:")
	fmt.Println("  -coordinator string  URL of the coordinator service")
	fmt.Println("  -name string         Node display name")
	fmt.Println("  -stream-key string   Stream key for registration")
	fmt.Println("  -log-level string    Log level (debug, info, warn, error)")
	fmt.Println("  -heartbeat int       Heartbeat interval in seconds")
	fmt.Println("  -port int            HLS serve port")
	fmt.Println("  -max-segments int    Max buffer segments")
	fmt.Println("  -max-viewers int     Max concurrent viewers")
	fmt.Println("  -srs-url string      SRS streaming server URL (defaults to coordinator:8080)")
	fmt.Println("  -help                Show this help message")
	fmt.Println("  -version             Show version information")
	fmt.Println()
	fmt.Println("Configuration:")
	fmt.Println("  Config file: ~/.streamr/config.yaml")
	fmt.Println("  Precedence: CLI flags > config file > defaults")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  streamr-node -stream-key sk_abc123")
	fmt.Println("  streamr-node -coordinator http://localhost:8000 -stream-key sk_abc123")
	fmt.Println("  streamr-node -log-level debug -port 9090")
}
