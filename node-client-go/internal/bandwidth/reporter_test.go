package bandwidth

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/iddv/streamr/node-client-go/internal/coordinator"
)

func testLogger() *logrus.Entry {
	l := logrus.New()
	l.SetLevel(logrus.ErrorLevel)
	return l.WithField("test", true)
}

func newTestReporter(baseURL string) *Reporter {
	client := coordinator.NewClient(baseURL, "node-1", 30*time.Second, testLogger())
	client.SetStatsURL("http://10.0.0.1:8080/stats")
	fromSRS := &atomic.Int64{}
	toViewers := &atomic.Int64{}
	return NewReporter(client, "session-1", fromSRS, toViewers, testLogger())
}

func TestNewReporter(t *testing.T) {
	r := newTestReporter("http://localhost")
	if r.sessionID != "session-1" {
		t.Errorf("expected session-1, got %s", r.sessionID)
	}
	if r.QueueSize() != 0 {
		t.Errorf("expected empty queue, got %d", r.QueueSize())
	}
}

func TestSendReport_Success(t *testing.T) {
	var receivedPayload map[string]interface{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/sessions/session-1/bandwidth-report" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewDecoder(r.Body).Decode(&receivedPayload)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	r := newTestReporter(srv.URL)
	report := BandwidthReport{
		BytesTransferred:  1024,
		StartInterval:     time.Now().Add(-60 * time.Second),
		EndInterval:       time.Now(),
		SourceBitrateKbps: 500,
	}

	err := r.sendReport(report)
	if err != nil {
		t.Fatalf("sendReport failed: %v", err)
	}
	if receivedPayload["bytes_transferred"] != float64(1024) {
		t.Errorf("expected 1024 bytes, got %v", receivedPayload["bytes_transferred"])
	}
}

func TestSendReport_ServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	r := newTestReporter(srv.URL)
	err := r.sendReport(BandwidthReport{BytesTransferred: 100})
	if err == nil {
		t.Fatal("expected error for 500 response")
	}
	re, ok := err.(*ReportError)
	if !ok {
		t.Fatalf("expected ReportError, got %T", err)
	}
	if re.StatusCode != 500 {
		t.Errorf("expected status 500, got %d", re.StatusCode)
	}
}

func TestSubmitReport_QueuesOnFailure(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	r := newTestReporter(srv.URL)
	r.submitReport(BandwidthReport{BytesTransferred: 100})

	if r.QueueSize() != 1 {
		t.Errorf("expected 1 queued report, got %d", r.QueueSize())
	}

	// Submit another — both should be queued
	r.submitReport(BandwidthReport{BytesTransferred: 200})
	if r.QueueSize() != 2 {
		t.Errorf("expected 2 queued reports, got %d", r.QueueSize())
	}
}

func TestSubmitReport_DrainQueueOnRecovery(t *testing.T) {
	callCount := 0
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	r := newTestReporter(srv.URL)
	// Manually queue some reports
	r.mu.Lock()
	r.queue = append(r.queue, BandwidthReport{BytesTransferred: 10})
	r.queue = append(r.queue, BandwidthReport{BytesTransferred: 20})
	r.mu.Unlock()

	// Submit a new report — should drain queue + submit new
	r.submitReport(BandwidthReport{BytesTransferred: 30})

	if r.QueueSize() != 0 {
		t.Errorf("expected empty queue after recovery, got %d", r.QueueSize())
	}
	// 2 queued + 1 new = 3 calls
	if callCount != 3 {
		t.Errorf("expected 3 HTTP calls, got %d", callCount)
	}
}

func TestSubmitReport_QueueMaxSize(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	r := newTestReporter(srv.URL)
	// Fill queue to max
	for i := 0; i < maxQueueSize+5; i++ {
		r.submitReport(BandwidthReport{BytesTransferred: int64(i)})
	}

	if r.QueueSize() > maxQueueSize {
		t.Errorf("queue exceeded max size: %d > %d", r.QueueSize(), maxQueueSize)
	}
}

func TestReportError_String(t *testing.T) {
	e := &ReportError{StatusCode: 503}
	s := e.Error()
	if s != "bandwidth report failed with status 503" {
		t.Errorf("unexpected error string: %s", s)
	}
}

func TestBandwidthReport_Fields(t *testing.T) {
	now := time.Now()
	r := BandwidthReport{
		BytesTransferred:  5000,
		StartInterval:     now.Add(-60 * time.Second),
		EndInterval:       now,
		SourceBitrateKbps: 250,
	}
	if r.BytesTransferred != 5000 {
		t.Errorf("expected 5000, got %d", r.BytesTransferred)
	}
	if r.SourceBitrateKbps != 250 {
		t.Errorf("expected 250, got %d", r.SourceBitrateKbps)
	}
}
