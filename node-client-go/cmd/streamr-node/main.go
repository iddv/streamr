package main

import (
	"flag"
	"fmt"
	"net/http"

	"github.com/sirupsen/logrus"
)

var (
	version = "0.1.0"
	commit  = "dev"
)

func main() {
	var (
		coordinatorURL = flag.String("coordinator", "http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com", "Coordinator URL")
		showHelp       = flag.Bool("help", false, "Show help message")
		showVer        = flag.Bool("version", false, "Show version information")
		debug          = flag.Bool("debug", false, "Enable debug logging")
	)
	flag.Parse()

	if *showHelp {
		printHelp()
		return
	}

	if *showVer {
		fmt.Printf("StreamrP2P Node Client v%s (%s)\n", version, commit)
		return
	}

	// Setup logging
	logrus.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
	})
	if *debug {
		logrus.SetLevel(logrus.DebugLevel)
	}

	logrus.WithFields(logrus.Fields{
		"version":         version,
		"commit":          commit,
		"coordinator_url": *coordinatorURL,
	}).Info("Starting StreamrP2P Node Client")

	// Simple health check
	if err := testCoordinatorConnection(*coordinatorURL); err != nil {
		logrus.WithError(err).Fatal("Failed to connect to coordinator")
	}
	logrus.Info("Successfully connected to coordinator")

	logrus.Info("✅ StreamrP2P Go Node Client - Foundation Complete!")
	logrus.Info("🚧 RTMP server integration coming next...")
	logrus.Info("Press Ctrl+C to exit")

	// Simple wait
	fmt.Println("Node client ready! (Press Enter to exit)")
	fmt.Scanln()
}

func testCoordinatorConnection(baseURL string) error {
	resp, err := http.Get(baseURL + "/health")
	if err != nil {
		return fmt.Errorf("health check request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check failed with status %d", resp.StatusCode)
	}

	return nil
}

func printHelp() {
	fmt.Println("StreamrP2P Node Client - Help relay friends' streams and earn rewards!")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  streamr-node [options]")
	fmt.Println()
	fmt.Println("Options:")
	fmt.Println("  -coordinator string  URL of the coordinator service")
	fmt.Println("  -debug              Enable debug logging")
	fmt.Println("  -help               Show this help message")
	fmt.Println("  -version            Show version information")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  streamr-node")
	fmt.Println("  streamr-node -debug")
	fmt.Println("  streamr-node -coordinator http://localhost:8000")
	fmt.Println()
	fmt.Println("🎯 Goal: 24x better friend experience (5% → 85% success rate)")
	fmt.Println("📦 Single binary - no Docker, no Python, no setup complexity")
	fmt.Println()
	fmt.Println("For more information, visit: https://github.com/iddv/streamr")
}
