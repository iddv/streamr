package hls

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"strings"
	"sync/atomic"
	"time"

	"github.com/sirupsen/logrus"
)

// Server serves HLS content from the segment buffer to viewers.
type Server struct {
	buffer         *SegmentBuffer
	port           int
	streamID       string
	BytesToViewers *atomic.Int64
	activeViewers  *atomic.Int32
	maxViewers     int
	httpServer     *http.Server
	mux            *http.ServeMux
	log            *logrus.Entry
}

// NewServer creates a new HLS server.
func NewServer(buffer *SegmentBuffer, port int, streamID string, maxViewers int, log *logrus.Entry) *Server {
	return &Server{
		buffer:         buffer,
		port:           port,
		streamID:       streamID,
		BytesToViewers: &atomic.Int64{},
		activeViewers:  &atomic.Int32{},
		maxViewers:     maxViewers,
		log:            log,
	}
}

// ActiveViewers returns the current number of active viewers.
func (s *Server) ActiveViewers() int32 {
	return s.activeViewers.Load()
}

// CapacitySaturated returns true when at 90%+ capacity.
func (s *Server) CapacitySaturated() bool {
	current := s.activeViewers.Load()
	threshold := int32(float64(s.maxViewers) * 0.9)
	return current >= threshold
}

// CapacityPercent returns the current capacity percentage (0-100).
func (s *Server) CapacityPercent() int {
	current := int(s.activeViewers.Load())
	if s.maxViewers == 0 {
		return 0
	}
	pct := (current * 100) / s.maxViewers
	if pct > 100 {
		pct = 100
	}
	return pct
}

// Start starts the HLS HTTP server. It blocks until the context is cancelled.
func (s *Server) Start(ctx context.Context) {
	s.buildMux()

	s.httpServer = &http.Server{
		Addr:    fmt.Sprintf(":%d", s.port),
		Handler: s.mux,
	}

	s.log.WithFields(logrus.Fields{
		"operation": "hls_server",
		"port":      s.port,
		"stream_id": s.streamID,
	}).Info("Starting HLS server")

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := s.httpServer.Shutdown(shutdownCtx); err != nil {
			s.log.WithField("operation", "hls_server").WithError(err).Warn("HLS server shutdown error")
		}
	}()

	if err := s.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		s.log.WithField("operation", "hls_server").WithError(err).Error("HLS server error")
	}
}

// StartOnListener serves HLS on an existing net.Listener (e.g. tsnet VPN listener).
// Runs in the background — does not block.
func (s *Server) StartOnListener(ctx context.Context, ln net.Listener) {
	s.buildMux()

	vpnServer := &http.Server{Handler: s.mux}

	s.log.WithFields(logrus.Fields{
		"operation": "hls_server_vpn",
		"addr":      ln.Addr().String(),
		"stream_id": s.streamID,
	}).Info("Starting HLS server on VPN listener")

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		vpnServer.Shutdown(shutdownCtx)
	}()

	go func() {
		if err := vpnServer.Serve(ln); err != nil && err != http.ErrServerClosed {
			s.log.WithField("operation", "hls_server_vpn").WithError(err).Error("VPN HLS server error")
		}
	}()
}

// buildMux creates the shared HTTP mux if not already built.
func (s *Server) buildMux() {
	if s.mux != nil {
		return
	}
	s.mux = http.NewServeMux()

	playlistPattern := fmt.Sprintf("/live/%s/index.m3u8", s.streamID)
	s.mux.HandleFunc(playlistPattern, s.viewerMiddleware(s.handlePlaylist))

	segmentPattern := fmt.Sprintf("/live/%s/", s.streamID)
	s.mux.HandleFunc(segmentPattern, s.viewerMiddleware(s.handleSegment))
}

// viewerMiddleware wraps a handler with concurrent viewer tracking and capacity limiting.
func (s *Server) viewerMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		current := s.activeViewers.Load()
		if int(current) >= s.maxViewers {
			http.Error(w, "Service at capacity", http.StatusServiceUnavailable)
			s.log.WithFields(logrus.Fields{
				"operation": "hls_server",
				"remote":    r.RemoteAddr,
			}).Warn("Rejected viewer: at max capacity")
			return
		}

		s.activeViewers.Add(1)
		defer s.activeViewers.Add(-1)

		next(w, r)
	}
}

// handlePlaylist generates and serves the M3U8 playlist from buffered segments.
func (s *Server) handlePlaylist(w http.ResponseWriter, r *http.Request) {
	segments := s.buffer.GetAll()
	if len(segments) == 0 {
		http.Error(w, "No segments available", http.StatusNotFound)
		return
	}

	var b strings.Builder
	b.WriteString("#EXTM3U\n")
	b.WriteString("#EXT-X-VERSION:3\n")

	// Calculate target duration from max segment duration
	maxDur := 0.0
	for _, seg := range segments {
		if seg.Duration > maxDur {
			maxDur = seg.Duration
		}
	}
	if maxDur == 0 {
		maxDur = 2.0
	}
	b.WriteString(fmt.Sprintf("#EXT-X-TARGETDURATION:%d\n", int(maxDur)+1))

	// Media sequence based on first segment
	b.WriteString("#EXT-X-MEDIA-SEQUENCE:0\n")

	for _, seg := range segments {
		dur := seg.Duration
		if dur == 0 {
			dur = 2.0
		}
		b.WriteString(fmt.Sprintf("#EXTINF:%.3f,\n", dur))
		b.WriteString(seg.Name + "\n")
	}

	playlist := b.String()
	w.Header().Set("Content-Type", "application/vnd.apple.mpegurl")
	w.Header().Set("Cache-Control", "no-cache")
	n, _ := w.Write([]byte(playlist))
	s.BytesToViewers.Add(int64(n))
}

// handleSegment serves a .ts segment from the buffer.
func (s *Server) handleSegment(w http.ResponseWriter, r *http.Request) {
	// Extract segment name from path: /live/{stream_id}/{segment}.ts
	path := r.URL.Path
	prefix := fmt.Sprintf("/live/%s/", s.streamID)
	segName := strings.TrimPrefix(path, prefix)

	if segName == "" || segName == "index.m3u8" {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}

	seg := s.buffer.GetByName(segName)
	if seg == nil {
		http.Error(w, "Segment not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "video/mp2t")
	w.Header().Set("Cache-Control", "max-age=3600")
	n, _ := w.Write(seg.Data)
	s.BytesToViewers.Add(int64(n))
}
