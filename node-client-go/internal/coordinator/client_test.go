package coordinator

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sirupsen/logrus"
)

func testLogger() *logrus.Entry {
	l := logrus.New()
	l.SetLevel(logrus.ErrorLevel) // quiet during tests
	return l.WithField("test", true)
}

func TestNewClient(t *testing.T) {
	c := NewClient("http://localhost:8000", "node-1", 30*time.Second, testLogger())
	if c.NodeID() != "node-1" {
		t.Errorf("expected node-1, got %s", c.NodeID())
	}
	if c.baseURL != "http://localhost:8000" {
		t.Errorf("expected base URL, got %s", c.baseURL)
	}
}

func TestRegister_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/auth/register" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		if r.Method != "POST" {
			t.Errorf("expected POST, got %s", r.Method)
		}

		var body map[string]string
		json.NewDecoder(r.Body).Decode(&body)
		if body["node_id"] != "node-1" {
			t.Errorf("expected node_id=node-1, got %s", body["node_id"])
		}

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(RegisterResponse{
			Token:    "jwt-token-123",
			StreamID: "stream-abc",
		})
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	resp, err := c.Register("node-1", "key-xyz")
	if err != nil {
		t.Fatalf("register failed: %v", err)
	}
	if resp.Token != "jwt-token-123" {
		t.Errorf("expected token jwt-token-123, got %s", resp.Token)
	}
	if resp.StreamID != "stream-abc" {
		t.Errorf("expected stream-abc, got %s", resp.StreamID)
	}
	if c.StreamID() != "stream-abc" {
		t.Errorf("stream ID not stored on client: %s", c.StreamID())
	}
}

func TestRegister_ServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("internal error"))
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	_, err := c.Register("node-1", "key-xyz")
	if err == nil {
		t.Fatal("expected error for 500 response")
	}
}

func TestRegister_ConnectionRefused(t *testing.T) {
	c := NewClient("http://127.0.0.1:1", "node-1", 30*time.Second, testLogger())
	_, err := c.Register("node-1", "key-xyz")
	if err == nil {
		t.Fatal("expected error for connection refused")
	}
}

func TestSendHeartbeat_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/nodes/heartbeat" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		auth := r.Header.Get("Authorization")
		if auth != "Bearer test-token" {
			t.Errorf("expected Bearer test-token, got %s", auth)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	c.jwtToken = "test-token"
	c.streamID = "stream-1"
	c.statsURL = "http://10.0.0.1:8080/stats"

	err := c.SendHeartbeat()
	if err != nil {
		t.Fatalf("heartbeat failed: %v", err)
	}
}

func TestSendHeartbeat_ServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("error"))
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	c.jwtToken = "token"
	c.streamID = "s1"

	err := c.SendHeartbeat()
	if err == nil {
		t.Fatal("expected error for 500 heartbeat")
	}
}

func TestDeregister_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("expected DELETE, got %s", r.Method)
		}
		if r.URL.Path != "/api/v1/nodes/node-1" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	c.jwtToken = "token"

	err := c.Deregister()
	if err != nil {
		t.Fatalf("deregister failed: %v", err)
	}
}

func TestDeregister_ServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		w.Write([]byte("forbidden"))
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "node-1", 30*time.Second, testLogger())
	c.jwtToken = "token"

	err := c.Deregister()
	if err == nil {
		t.Fatal("expected error for 403 deregister")
	}
}

func TestSetVPNIP(t *testing.T) {
	c := NewClient("http://localhost", "n1", 30*time.Second, testLogger())
	c.SetVPNIP("10.0.0.5")
	if c.vpnIP != "10.0.0.5" {
		t.Errorf("expected 10.0.0.5, got %s", c.vpnIP)
	}
}

func TestSetStatsURL(t *testing.T) {
	c := NewClient("http://localhost", "n1", 30*time.Second, testLogger())
	c.SetStatsURL("http://10.0.0.1:8080/stats")
	if c.statsURL != "http://10.0.0.1:8080/stats" {
		t.Errorf("expected stats URL, got %s", c.statsURL)
	}
}

func TestAuthenticatedRequest_SetsHeaders(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := r.Header.Get("Authorization")
		if auth != "Bearer my-jwt" {
			t.Errorf("expected Bearer my-jwt, got %s", auth)
		}
		ct := r.Header.Get("Content-Type")
		if ct != "application/json" {
			t.Errorf("expected application/json, got %s", ct)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "n1", 30*time.Second, testLogger())
	c.jwtToken = "my-jwt"

	resp, err := c.AuthenticatedRequest("GET", "/test", nil)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}
