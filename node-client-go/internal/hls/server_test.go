package hls

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/sirupsen/logrus"
)

func testServerLogger() *logrus.Entry {
	l := logrus.New()
	l.SetLevel(logrus.ErrorLevel)
	return l.WithField("test", true)
}

func newTestServer(maxViewers int) *Server {
	buf := NewSegmentBuffer(30)
	return NewServer(buf, 0, "test-stream", maxViewers, testServerLogger())
}

func TestCapacitySaturated(t *testing.T) {
	s := newTestServer(10)
	if s.CapacitySaturated() {
		t.Error("should not be saturated with 0 viewers")
	}
	// Simulate 9 viewers (90% of 10)
	s.activeViewers.Store(9)
	if !s.CapacitySaturated() {
		t.Error("should be saturated at 90%")
	}
	s.activeViewers.Store(8)
	if s.CapacitySaturated() {
		t.Error("should not be saturated at 80%")
	}
}

func TestCapacityPercent(t *testing.T) {
	s := newTestServer(10)
	if s.CapacityPercent() != 0 {
		t.Errorf("expected 0%%, got %d%%", s.CapacityPercent())
	}
	s.activeViewers.Store(5)
	if s.CapacityPercent() != 50 {
		t.Errorf("expected 50%%, got %d%%", s.CapacityPercent())
	}
	s.activeViewers.Store(10)
	if s.CapacityPercent() != 100 {
		t.Errorf("expected 100%%, got %d%%", s.CapacityPercent())
	}
}

func TestCapacityPercent_ZeroMax(t *testing.T) {
	s := newTestServer(0)
	if s.CapacityPercent() != 0 {
		t.Errorf("expected 0%% for zero max, got %d%%", s.CapacityPercent())
	}
}

func TestActiveViewers(t *testing.T) {
	s := newTestServer(10)
	if s.ActiveViewers() != 0 {
		t.Errorf("expected 0, got %d", s.ActiveViewers())
	}
	s.activeViewers.Store(3)
	if s.ActiveViewers() != 3 {
		t.Errorf("expected 3, got %d", s.ActiveViewers())
	}
}

func TestHandlePlaylist_NoSegments(t *testing.T) {
	s := newTestServer(10)
	req := httptest.NewRequest("GET", "/live/test-stream/index.m3u8", nil)
	w := httptest.NewRecorder()
	s.handlePlaylist(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 for empty buffer, got %d", w.Code)
	}
}

func TestHandlePlaylist_WithSegments(t *testing.T) {
	s := newTestServer(10)
	s.buffer.Add(Segment{Name: "seg0.ts", Data: []byte("data0"), Duration: 2.0})
	s.buffer.Add(Segment{Name: "seg1.ts", Data: []byte("data1"), Duration: 2.5})

	req := httptest.NewRequest("GET", "/live/test-stream/index.m3u8", nil)
	w := httptest.NewRecorder()
	s.handlePlaylist(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "#EXTM3U") {
		t.Error("missing #EXTM3U header")
	}
	if !strings.Contains(body, "seg0.ts") {
		t.Error("missing seg0.ts in playlist")
	}
	if !strings.Contains(body, "seg1.ts") {
		t.Error("missing seg1.ts in playlist")
	}
	ct := w.Header().Get("Content-Type")
	if ct != "application/vnd.apple.mpegurl" {
		t.Errorf("expected mpegurl content type, got %s", ct)
	}
}

func TestHandlePlaylist_BytesCounted(t *testing.T) {
	s := newTestServer(10)
	s.buffer.Add(Segment{Name: "s.ts", Data: []byte("x"), Duration: 1.0})

	before := s.BytesToViewers.Load()
	req := httptest.NewRequest("GET", "/live/test-stream/index.m3u8", nil)
	w := httptest.NewRecorder()
	s.handlePlaylist(w, req)

	after := s.BytesToViewers.Load()
	if after <= before {
		t.Error("BytesToViewers should have increased")
	}
}

func TestHandleSegment_Found(t *testing.T) {
	s := newTestServer(10)
	s.buffer.Add(Segment{Name: "seg42.ts", Data: []byte("segment-data")})

	req := httptest.NewRequest("GET", fmt.Sprintf("/live/%s/seg42.ts", s.streamID), nil)
	w := httptest.NewRecorder()
	s.handleSegment(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if w.Body.String() != "segment-data" {
		t.Errorf("unexpected body: %s", w.Body.String())
	}
	ct := w.Header().Get("Content-Type")
	if ct != "video/mp2t" {
		t.Errorf("expected video/mp2t, got %s", ct)
	}
}

func TestHandleSegment_NotFound(t *testing.T) {
	s := newTestServer(10)
	req := httptest.NewRequest("GET", fmt.Sprintf("/live/%s/missing.ts", s.streamID), nil)
	w := httptest.NewRecorder()
	s.handleSegment(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", w.Code)
	}
}

func TestHandleSegment_EmptyName(t *testing.T) {
	s := newTestServer(10)
	req := httptest.NewRequest("GET", fmt.Sprintf("/live/%s/", s.streamID), nil)
	w := httptest.NewRecorder()
	s.handleSegment(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 for empty segment name, got %d", w.Code)
	}
}

func TestViewerMiddleware_RejectsAtCapacity(t *testing.T) {
	s := newTestServer(2)
	s.activeViewers.Store(2) // at max

	handler := s.viewerMiddleware(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("GET", "/test", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", w.Code)
	}
}

func TestViewerMiddleware_AllowsBelowCapacity(t *testing.T) {
	s := newTestServer(10)
	called := false
	handler := s.viewerMiddleware(func(w http.ResponseWriter, r *http.Request) {
		called = true
		// Verify viewer count incremented during request
		if s.ActiveViewers() < 1 {
			t.Error("expected active viewers >= 1 during request")
		}
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("GET", "/test", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if !called {
		t.Error("handler was not called")
	}
	// After request, viewer count should be decremented
	if s.ActiveViewers() != 0 {
		t.Errorf("expected 0 active viewers after request, got %d", s.ActiveViewers())
	}
}

func TestSegmentBytesCounted(t *testing.T) {
	s := newTestServer(10)
	s.BytesToViewers = &atomic.Int64{}
	s.buffer.Add(Segment{Name: "count.ts", Data: []byte("12345")})

	req := httptest.NewRequest("GET", fmt.Sprintf("/live/%s/count.ts", s.streamID), nil)
	w := httptest.NewRecorder()
	s.handleSegment(w, req)

	if s.BytesToViewers.Load() != 5 {
		t.Errorf("expected 5 bytes counted, got %d", s.BytesToViewers.Load())
	}
}
