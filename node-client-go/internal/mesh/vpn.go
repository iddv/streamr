// Package mesh provides VPN mesh connectivity via embedded tsnet (Tailscale).
package mesh

import (
	"context"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"tailscale.com/tsnet"
)

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
