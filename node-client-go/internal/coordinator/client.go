package coordinator

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
)

// RegisterResponse holds the response from the coordinator registration endpoint.
type RegisterResponse struct {
	Token            string `json:"token"`
	StreamID         string `json:"stream_id"`
	HeadscaleAuthKey string `json:"headscale_auth_key"`
	HeadscaleURL     string `json:"headscale_url"`
}

// Client communicates with the coordinator API.
type Client struct {
	baseURL           string
	jwtToken          string
	nodeID            string
	streamID          string
	vpnIP             string
	httpClient        *http.Client
	heartbeatInterval time.Duration
	statsURL          string
	mu                sync.RWMutex
	log               *logrus.Entry
}

// NewClient creates a new coordinator client.
func NewClient(baseURL, nodeID string, heartbeatInterval time.Duration, log *logrus.Entry) *Client {
	return &Client{
		baseURL:           baseURL,
		nodeID:            nodeID,
		heartbeatInterval: heartbeatInterval,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		log: log,
	}
}

// NodeID returns the client's node ID.
func (c *Client) NodeID() string {
	return c.nodeID
}

// StreamID returns the stream ID received during registration.
func (c *Client) StreamID() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.streamID
}

// SetStatsURL sets the stats URL reported in heartbeats.
func (c *Client) SetStatsURL(url string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.statsURL = url
}

// SetVPNIP sets the VPN mesh IP reported in heartbeats.
func (c *Client) SetVPNIP(ip string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.vpnIP = ip
}

// Register registers this node with the coordinator using a stream key.
func (c *Client) Register(nodeID, streamKey string) (*RegisterResponse, error) {
	payload := map[string]string{
		"node_id":    nodeID,
		"stream_key": streamKey,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal register payload: %w", err)
	}

	resp, err := c.httpClient.Post(
		c.baseURL+"/api/v1/auth/register",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("register request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("register failed with status %d: %s", resp.StatusCode, string(respBody))
	}

	var regResp RegisterResponse
	if err := json.NewDecoder(resp.Body).Decode(&regResp); err != nil {
		return nil, fmt.Errorf("decode register response: %w", err)
	}

	c.mu.Lock()
	c.jwtToken = regResp.Token
	c.streamID = regResp.StreamID
	c.nodeID = nodeID
	c.mu.Unlock()

	c.log.WithFields(logrus.Fields{
		"stream_id": regResp.StreamID,
		"operation": "register",
	}).Info("Registered with coordinator")

	return &regResp, nil
}

// AuthenticatedRequest sends an HTTP request with the JWT Authorization header.
func (c *Client) AuthenticatedRequest(method, path string, body interface{}) (*http.Response, error) {
	var reqBody io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal request body: %w", err)
		}
		reqBody = bytes.NewReader(data)
	}

	req, err := http.NewRequest(method, c.baseURL+path, reqBody)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	c.mu.RLock()
	token := c.jwtToken
	c.mu.RUnlock()

	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	return c.httpClient.Do(req)
}

// SendHeartbeat sends a heartbeat to the coordinator.
func (c *Client) SendHeartbeat() error {
	c.mu.RLock()
	payload := map[string]interface{}{
		"node_id":   c.nodeID,
		"stream_id": c.streamID,
		"stats_url": c.statsURL,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}
	if c.vpnIP != "" {
		payload["vpn_ip"] = c.vpnIP
	}
	c.mu.RUnlock()

	resp, err := c.AuthenticatedRequest("POST", "/nodes/heartbeat", payload)
	if err != nil {
		return fmt.Errorf("heartbeat request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("heartbeat failed with status %d: %s", resp.StatusCode, string(respBody))
	}

	return nil
}

// HeartbeatLoop runs the heartbeat loop until the context is cancelled.
// It uses exponential backoff on failure (2s initial → 60s max) and logs
// a warning after 5 minutes of consecutive failures.
func (c *Client) HeartbeatLoop(ctx context.Context) {
	ticker := time.NewTicker(c.heartbeatInterval)
	defer ticker.Stop()

	retryDelay := 2 * time.Second
	maxRetry := 60 * time.Second
	consecutiveFailures := 0

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			err := c.SendHeartbeat()
			if err != nil {
				consecutiveFailures++
				c.log.WithFields(logrus.Fields{
					"operation":            "heartbeat",
					"consecutive_failures": consecutiveFailures,
					"retry_delay":          retryDelay.String(),
				}).WithError(err).Error("Heartbeat failed")

				// Log warning after ~5 minutes of failures (based on heartbeat interval)
				failureDuration := time.Duration(consecutiveFailures) * c.heartbeatInterval
				if failureDuration >= 5*time.Minute {
					c.log.WithField("operation", "heartbeat").Warn("Coordinator unreachable for 5+ minutes, continuing retries")
				}

				// Sleep with backoff (interruptible by context)
				select {
				case <-ctx.Done():
					return
				case <-time.After(retryDelay):
				}

				retryDelay *= 2
				if retryDelay > maxRetry {
					retryDelay = maxRetry
				}
			} else {
				if consecutiveFailures > 0 {
					c.log.WithField("operation", "heartbeat").Info("Heartbeat recovered after failures")
				}
				retryDelay = 2 * time.Second
				consecutiveFailures = 0
			}
		}
	}
}

// Deregister sends a deregistration request to the coordinator.
func (c *Client) Deregister() error {
	c.mu.RLock()
	nodeID := c.nodeID
	c.mu.RUnlock()

	resp, err := c.AuthenticatedRequest("DELETE", "/api/v1/nodes/"+nodeID, nil)
	if err != nil {
		return fmt.Errorf("deregister request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("deregister failed with status %d: %s", resp.StatusCode, string(respBody))
	}

	c.log.WithField("operation", "deregister").Info("Deregistered from coordinator")
	return nil
}
// FetchHeadscaleCert downloads the Headscale TLS certificate PEM from the
// coordinator so the Go node can trust the self-signed cert.
func (c *Client) FetchHeadscaleCert() ([]byte, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/api/v1/auth/headscale-cert")
	if err != nil {
		return nil, fmt.Errorf("fetch headscale cert: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, nil // No cert configured — not an error
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("fetch headscale cert: status %d", resp.StatusCode)
	}

	pem, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read headscale cert body: %w", err)
	}
	return pem, nil
}


