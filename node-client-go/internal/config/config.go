package config

import (
	"flag"
	"os"
	"path/filepath"
	"time"

	"github.com/sirupsen/logrus"
	"gopkg.in/yaml.v3"
)

// Config holds all node client configuration.
type Config struct {
	CoordinatorURL    string        `yaml:"coordinator_url"`
	NodeName          string        `yaml:"node_name"`
	StreamKey         string        `yaml:"stream_key"`
	LogLevel          string        `yaml:"log_level"`
	HeartbeatInterval time.Duration `yaml:"-"`
	HeartbeatSecs     int           `yaml:"heartbeat_interval"`
	ServePort         int           `yaml:"serve_port"`
	MaxBufferSegments int           `yaml:"max_buffer_segments"`
	MaxViewers        int           `yaml:"max_concurrent_viewers"`
}

// Defaults returns a Config with all default values.
func Defaults() Config {
	return Config{
		CoordinatorURL:    "http://localhost:8000",
		NodeName:          "",
		StreamKey:         "",
		LogLevel:          "info",
		HeartbeatSecs:     30,
		HeartbeatInterval: 30 * time.Second,
		ServePort:         8080,
		MaxBufferSegments: 30,
		MaxViewers:        10,
	}
}

// configFilePath returns the default config file path (~/.streamr/config.yaml).
func configFilePath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	return filepath.Join(home, ".streamr", "config.yaml")
}

// loadFromFile loads config from a YAML file. Returns defaults and false if file
// is missing or malformed.
func loadFromFile(path string) (Config, bool) {
	cfg := Defaults()

	data, err := os.ReadFile(path)
	if err != nil {
		if !os.IsNotExist(err) {
			logrus.WithError(err).Warn("Failed to read config file, using defaults")
		}
		return cfg, false
	}

	if err := yaml.Unmarshal(data, &cfg); err != nil {
		logrus.WithError(err).Warn("Malformed config file, using defaults")
		return Defaults(), false
	}

	// Apply heartbeat duration from seconds
	if cfg.HeartbeatSecs > 0 {
		cfg.HeartbeatInterval = time.Duration(cfg.HeartbeatSecs) * time.Second
	}
	// Ensure non-zero defaults for fields that might be zero in YAML
	if cfg.ServePort == 0 {
		cfg.ServePort = 8080
	}
	if cfg.MaxBufferSegments == 0 {
		cfg.MaxBufferSegments = 30
	}
	if cfg.MaxViewers == 0 {
		cfg.MaxViewers = 10
	}
	if cfg.LogLevel == "" {
		cfg.LogLevel = "info"
	}

	return cfg, true
}

// Load loads configuration with precedence: CLI flags > config file > defaults.
// It defines and parses its own FlagSet so it can be tested independently.
func Load() (*Config, error) {
	return LoadWithArgs(os.Args[1:])
}

// LoadWithArgs loads configuration using the provided CLI arguments.
func LoadWithArgs(args []string) (*Config, error) {
	cfg := Defaults()

	// Load from file first
	fileCfg, fileLoaded := loadFromFile(configFilePath())
	if fileLoaded {
		cfg = fileCfg
	}

	// Define CLI flags
	fs := flag.NewFlagSet("streamr-node", flag.ContinueOnError)
	coordinator := fs.String("coordinator", "", "Coordinator URL")
	nodeName := fs.String("name", "", "Node display name")
	streamKey := fs.String("stream-key", "", "Stream key for registration")
	logLevel := fs.String("log-level", "", "Log level (debug, info, warn, error)")
	heartbeat := fs.Int("heartbeat", 0, "Heartbeat interval in seconds")
	port := fs.Int("port", 0, "HLS serve port")
	maxSegments := fs.Int("max-segments", 0, "Max buffer segments")
	maxViewers := fs.Int("max-viewers", 0, "Max concurrent viewers")

	// Also support legacy flags
	fs.String("help", "", "")
	fs.String("version", "", "")
	fs.Bool("debug", false, "")

	// Parse, ignoring errors for unknown flags handled by main
	_ = fs.Parse(args)

	// Override with CLI flags (only if explicitly set)
	if *coordinator != "" {
		cfg.CoordinatorURL = *coordinator
	}
	if *nodeName != "" {
		cfg.NodeName = *nodeName
	}
	if *streamKey != "" {
		cfg.StreamKey = *streamKey
	}
	if *logLevel != "" {
		cfg.LogLevel = *logLevel
	}
	if *heartbeat > 0 {
		cfg.HeartbeatSecs = *heartbeat
		cfg.HeartbeatInterval = time.Duration(*heartbeat) * time.Second
	}
	if *port > 0 {
		cfg.ServePort = *port
	}
	if *maxSegments > 0 {
		cfg.MaxBufferSegments = *maxSegments
	}
	if *maxViewers > 0 {
		cfg.MaxViewers = *maxViewers
	}

	return &cfg, nil
}
