package config

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestDefaults(t *testing.T) {
	cfg := Defaults()
	if cfg.CoordinatorURL != "http://localhost:8000" {
		t.Errorf("expected default coordinator URL, got %s", cfg.CoordinatorURL)
	}
	if cfg.HeartbeatInterval != 30*time.Second {
		t.Errorf("expected 30s heartbeat, got %v", cfg.HeartbeatInterval)
	}
	if cfg.ServePort != 8080 {
		t.Errorf("expected port 8080, got %d", cfg.ServePort)
	}
	if cfg.MaxBufferSegments != 30 {
		t.Errorf("expected 30 max segments, got %d", cfg.MaxBufferSegments)
	}
	if cfg.MaxViewers != 10 {
		t.Errorf("expected 10 max viewers, got %d", cfg.MaxViewers)
	}
	if cfg.LogLevel != "info" {
		t.Errorf("expected info log level, got %s", cfg.LogLevel)
	}
}

func TestLoadFromFile_ValidYAML(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	content := `coordinator_url: "http://example.com:8000"
node_name: "test-node"
stream_key: "abc123"
log_level: "debug"
heartbeat_interval: 15
serve_port: 9090
max_buffer_segments: 20
max_concurrent_viewers: 5
`
	if err := os.WriteFile(cfgPath, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, loaded := loadFromFile(cfgPath)
	if !loaded {
		t.Fatal("expected config to load successfully")
	}
	if cfg.CoordinatorURL != "http://example.com:8000" {
		t.Errorf("got coordinator URL %s", cfg.CoordinatorURL)
	}
	if cfg.NodeName != "test-node" {
		t.Errorf("got node name %s", cfg.NodeName)
	}
	if cfg.LogLevel != "debug" {
		t.Errorf("got log level %s", cfg.LogLevel)
	}
	if cfg.HeartbeatInterval != 15*time.Second {
		t.Errorf("got heartbeat interval %v", cfg.HeartbeatInterval)
	}
	if cfg.ServePort != 9090 {
		t.Errorf("got serve port %d", cfg.ServePort)
	}
	if cfg.MaxBufferSegments != 20 {
		t.Errorf("got max segments %d", cfg.MaxBufferSegments)
	}
	if cfg.MaxViewers != 5 {
		t.Errorf("got max viewers %d", cfg.MaxViewers)
	}
}

func TestLoadFromFile_MissingFile(t *testing.T) {
	cfg, loaded := loadFromFile("/nonexistent/path/config.yaml")
	if loaded {
		t.Fatal("expected loaded=false for missing file")
	}
	// Should return defaults
	if cfg.CoordinatorURL != "http://localhost:8000" {
		t.Errorf("expected default coordinator URL, got %s", cfg.CoordinatorURL)
	}
}

func TestLoadFromFile_MalformedYAML(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(cfgPath, []byte("{{{{not yaml"), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, loaded := loadFromFile(cfgPath)
	if loaded {
		t.Fatal("expected loaded=false for malformed YAML")
	}
	// Should return defaults
	if cfg.ServePort != 8080 {
		t.Errorf("expected default port, got %d", cfg.ServePort)
	}
}

func TestLoadFromFile_ZeroValues_GetDefaults(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	// YAML with zero values for numeric fields
	content := `coordinator_url: "http://custom:8000"
serve_port: 0
max_buffer_segments: 0
max_concurrent_viewers: 0
log_level: ""
`
	if err := os.WriteFile(cfgPath, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, loaded := loadFromFile(cfgPath)
	if !loaded {
		t.Fatal("expected config to load")
	}
	if cfg.ServePort != 8080 {
		t.Errorf("zero serve_port should default to 8080, got %d", cfg.ServePort)
	}
	if cfg.MaxBufferSegments != 30 {
		t.Errorf("zero max_segments should default to 30, got %d", cfg.MaxBufferSegments)
	}
	if cfg.MaxViewers != 10 {
		t.Errorf("zero max_viewers should default to 10, got %d", cfg.MaxViewers)
	}
	if cfg.LogLevel != "info" {
		t.Errorf("empty log_level should default to info, got %s", cfg.LogLevel)
	}
}

func TestLoadWithArgs_CLIOverridesDefaults(t *testing.T) {
	cfg, err := LoadWithArgs([]string{
		"-coordinator", "http://override:9000",
		"-name", "cli-node",
		"-stream-key", "key123",
		"-log-level", "debug",
		"-heartbeat", "10",
		"-port", "7070",
		"-max-segments", "15",
		"-max-viewers", "20",
	})
	if err != nil {
		t.Fatal(err)
	}
	if cfg.CoordinatorURL != "http://override:9000" {
		t.Errorf("CLI coordinator not applied: %s", cfg.CoordinatorURL)
	}
	if cfg.NodeName != "cli-node" {
		t.Errorf("CLI name not applied: %s", cfg.NodeName)
	}
	if cfg.StreamKey != "key123" {
		t.Errorf("CLI stream-key not applied: %s", cfg.StreamKey)
	}
	if cfg.HeartbeatSecs != 10 {
		t.Errorf("CLI heartbeat not applied: %d", cfg.HeartbeatSecs)
	}
	if cfg.HeartbeatInterval != 10*time.Second {
		t.Errorf("CLI heartbeat duration not applied: %v", cfg.HeartbeatInterval)
	}
	if cfg.ServePort != 7070 {
		t.Errorf("CLI port not applied: %d", cfg.ServePort)
	}
	if cfg.MaxViewers != 20 {
		t.Errorf("CLI max-viewers not applied: %d", cfg.MaxViewers)
	}
}

func TestLoadWithArgs_EmptyArgs_UsesDefaults(t *testing.T) {
	cfg, err := LoadWithArgs([]string{})
	if err != nil {
		t.Fatal(err)
	}
	if cfg.CoordinatorURL != "http://localhost:8000" {
		t.Errorf("expected default coordinator, got %s", cfg.CoordinatorURL)
	}
	if cfg.ServePort != 8080 {
		t.Errorf("expected default port, got %d", cfg.ServePort)
	}
}
