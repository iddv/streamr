// Package mesh provides VPN mesh connectivity via embedded tsnet (Tailscale).
package mesh

import (
	"context"
	"crypto/x509"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"tailscale.com/tsnet"
)

// InstallCert installs a PEM certificate into the SYSTEM CA trust store so
// that tsnet's internal tlsdial (which uses x509.SystemCertPool via nil Roots)
// will trust our self-signed Headscale cert. Requires root privileges.
// Must be called before Join().
func InstallCert(certPEM []byte, log *logrus.Entry) error {
	if len(certPEM) == 0 {
		return nil
	}

	// Verify the PEM is actually parseable
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(certPEM) {
		return fmt.Errorf("failed to parse Headscale TLS certificate PEM")
	}

	// Detect OS and install to system CA store
	switch runtime.GOOS {
	case "linux":
		if err := installCertLinux(certPEM, log); err != nil {
			return err
		}
	case "darwin":
		if err := installCertDarwin(certPEM, log); err != nil {
			return err
		}
	default:
		log.Warnf("System CA install not supported on %s, falling back to SSL_CERT_FILE", runtime.GOOS)
		return installCertFallback(certPEM, log)
	}

	log.Info("Installed Headscale TLS certificate into system CA store")
	return nil
}

// installCertLinux writes the cert to the system CA directory and runs update-ca-certificates.
func installCertLinux(certPEM []byte, log *logrus.Entry) error {
	// Debian/Ubuntu path
	debianDir := "/usr/local/share/ca-certificates"
	rhelDir := "/etc/pki/ca-trust/source/anchors"

	var certPath string
	var updateCmd string
	var updateArgs []string

	if _, err := os.Stat("/usr/sbin/update-ca-certificates"); err == nil {
		// Debian/Ubuntu
		if err := os.MkdirAll(debianDir, 0755); err != nil {
			return fmt.Errorf("create CA dir: %w", err)
		}
		certPath = filepath.Join(debianDir, "headscale.crt")
		updateCmd = "/usr/sbin/update-ca-certificates"
	} else if _, err := os.Stat("/etc/pki/ca-trust/source/anchors"); err == nil {
		// RHEL/CentOS/Fedora
		certPath = filepath.Join(rhelDir, "headscale.pem")
		updateCmd = "update-ca-trust"
		updateArgs = []string{"extract"}
	} else {
		log.Warn("No system CA update tool found, falling back to SSL_CERT_FILE")
		return installCertFallback(certPEM, log)
	}

	if err := os.WriteFile(certPath, certPEM, 0644); err != nil {
		return fmt.Errorf("write cert to %s: %w", certPath, err)
	}
	log.WithField("cert_path", certPath).Info("Wrote cert to system CA directory")

	cmd := exec.Command(updateCmd, updateArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("run %s: %w", updateCmd, err)
	}
	log.Infof("Ran %s successfully", updateCmd)
	return nil
}

// installCertDarwin adds the cert to the macOS system keychain.
func installCertDarwin(certPEM []byte, log *logrus.Entry) error {
	tmpFile := filepath.Join(os.TempDir(), "headscale.pem")
	if err := os.WriteFile(tmpFile, certPEM, 0644); err != nil {
		return fmt.Errorf("write temp cert: %w", err)
	}
	defer os.Remove(tmpFile)

	cmd := exec.Command("security", "add-trusted-cert", "-d", "-r", "trustRoot",
		"-k", "/Library/Keychains/System.keychain", tmpFile)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("security add-trusted-cert: %w", err)
	}
	log.Info("Added cert to macOS System keychain")
	return nil
}

// installCertFallback uses SSL_CERT_FILE for unsupported platforms.
func installCertFallback(certPEM []byte, log *logrus.Entry) error {
	homeDir, _ := os.UserHomeDir()
	certPath := filepath.Join(homeDir, ".streamr", "headscale-ca.pem")
	if err := os.MkdirAll(filepath.Dir(certPath), 0700); err != nil {
		return fmt.Errorf("create cert dir: %w", err)
	}

	// Combine system certs + custom cert since SSL_CERT_FILE replaces the pool
	var combined []byte
	for _, path := range []string{
		"/etc/ssl/certs/ca-certificates.crt",
		"/etc/pki/tls/certs/ca-bundle.crt",
	} {
		if data, err := os.ReadFile(path); err == nil {
			combined = append(combined, data...)
			break
		}
	}
	combined = append(combined, certPEM...)

	if err := os.WriteFile(certPath, combined, 0600); err != nil {
		return fmt.Errorf("write cert file: %w", err)
	}
	os.Setenv("SSL_CERT_FILE", certPath)
	log.WithField("cert_path", certPath).Infof("Fallback: set SSL_CERT_FILE")
	return nil
}

// ClearStaleState removes old tsnet state to force a fresh login.
// Call this before Join() when re-authenticating with a new auth key.
func ClearStaleState(log *logrus.Entry) error {
	homeDir, _ := os.UserHomeDir()
	stateDir := filepath.Join(homeDir, ".streamr", "tailscale")
	if _, err := os.Stat(stateDir); os.IsNotExist(err) {
		return nil
	}
	log.WithField("state_dir", stateDir).Info("Clearing stale tsnet state for fresh login")
	return os.RemoveAll(stateDir)
}

// MeshNode manages the embedded Tailscale/tsnet VPN connection.
type MeshNode struct {
	tsServer *tsnet.Server
	vpnIP    string
	listener net.Listener
	mu       sync.RWMutex
	log      *logrus.Entry
}

// NewMeshNode creates a new MeshNode.
func NewMeshNode(log *logrus.Entry) *MeshNode {
	return &MeshNode{log: log}
}

// Join authenticates with the Headscale coordination server and joins the
// VPN mesh.  It uses exponential backoff (5s → 120s) on failure.
func (m *MeshNode) Join(ctx context.Context, authKey, nodeName, controlURL string) error {
	homeDir, _ := os.UserHomeDir()
	stateDir := filepath.Join(homeDir, ".streamr", "tailscale")
	if err := os.MkdirAll(stateDir, 0700); err != nil {
		return fmt.Errorf("create state dir: %w", err)
	}

	retryDelay := 5 * time.Second
	maxRetry := 120 * time.Second

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		srv := &tsnet.Server{
			Hostname:  nodeName,
			AuthKey:   authKey,
			Dir:       stateDir,
			Ephemeral: false,
		}

		// Set control URL if provided (Headscale server)
		if controlURL != "" {
			srv.ControlURL = controlURL
		}

		m.log.WithField("operation", "mesh_join").Info("Connecting to VPN mesh...")

		// Start blocks until the node is connected or fails
		if err := srv.Start(); err != nil {
			m.log.WithFields(logrus.Fields{
				"operation":   "mesh_join",
				"retry_delay": retryDelay.String(),
			}).WithError(err).Warn("VPN mesh connection failed, retrying")

			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(retryDelay):
			}

			retryDelay *= 2
			if retryDelay > maxRetry {
				retryDelay = maxRetry
			}
			continue
		}

		// Connected — wait for VPN IP assignment (auth may still be in progress)
		lc, err := srv.LocalClient()
		if err != nil {
			srv.Close()
			return fmt.Errorf("get local client: %w", err)
		}

		var vpnIP string
		pollInterval := 500 * time.Millisecond
		for vpnIP == "" {
			select {
			case <-ctx.Done():
				srv.Close()
				return ctx.Err()
			case <-time.After(pollInterval):
			}

			status, err := lc.Status(ctx)
			if err != nil {
				m.log.WithField("operation", "mesh_join").WithError(err).Debug("Waiting for VPN IP...")
				continue
			}
			if len(status.TailscaleIPs) > 0 {
				vpnIP = status.TailscaleIPs[0].String()
			}
		}

		m.mu.Lock()
		m.tsServer = srv
		m.vpnIP = vpnIP
		m.mu.Unlock()

		m.log.WithFields(logrus.Fields{
			"operation": "mesh_join",
			"vpn_ip":    m.vpnIP,
		}).Info("Joined VPN mesh")

		return nil
	}
}

// Listen starts a TCP listener on the mesh IP at the given port.
func (m *MeshNode) Listen(port int) (net.Listener, error) {
	m.mu.RLock()
	srv := m.tsServer
	m.mu.RUnlock()

	if srv == nil {
		return nil, fmt.Errorf("not connected to VPN mesh")
	}

	ln, err := srv.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return nil, fmt.Errorf("tsnet listen on port %d: %w", port, err)
	}

	m.mu.Lock()
	m.listener = ln
	m.mu.Unlock()

	m.log.WithFields(logrus.Fields{
		"operation": "mesh_listen",
		"port":      port,
		"vpn_ip":    m.VPNIP(),
	}).Info("Listening on VPN mesh")

	return ln, nil
}

// VPNIP returns the assigned VPN IP address.
func (m *MeshNode) VPNIP() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.vpnIP
}

// Close shuts down the tsnet server and listener.
func (m *MeshNode) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.listener != nil {
		m.listener.Close()
		m.listener = nil
	}
	if m.tsServer != nil {
		err := m.tsServer.Close()
		m.tsServer = nil
		return err
	}
	return nil
}
