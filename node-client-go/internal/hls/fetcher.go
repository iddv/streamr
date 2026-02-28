package hls

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/sirupsen/logrus"
)

// Segment represents a single HLS .ts segment.
type Segment struct {
	Name      string
	Data      []byte
	Duration  float64
	FetchedAt time.Time
}

// SegmentBuffer is a thread-safe circular buffer for HLS segments.
type SegmentBuffer struct {
	mu       sync.RWMutex
	segments []Segment
	maxSize  int
}

// NewSegmentBuffer creates a new segment buffer with the given max size.
func NewSegmentBuffer(maxSize int) *SegmentBuffer {
	return &SegmentBuffer{
		segments: make([]Segment, 0, maxSize),
		maxSize:  maxSize,
	}
}

// Add adds a segment to the buffer, evicting the oldest if full.
func (b *SegmentBuffer) Add(seg Segment) {
	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.segments) >= b.maxSize {
		// Evict oldest
		b.segments = b.segments[1:]
	}
	b.segments = append(b.segments, seg)
}

// GetAll returns a copy of all segments in the buffer.
func (b *SegmentBuffer) GetAll() []Segment {
	b.mu.RLock()
	defer b.mu.RUnlock()

	result := make([]Segment, len(b.segments))
	copy(result, b.segments)
	return result
}

// GetByName returns a segment by name, or nil if not found.
func (b *SegmentBuffer) GetByName(name string) *Segment {
	b.mu.RLock()
	defer b.mu.RUnlock()

	for i := range b.segments {
		if b.segments[i].Name == name {
			seg := b.segments[i]
			return &seg
		}
	}
	return nil
}

// Count returns the number of segments in the buffer.
func (b *SegmentBuffer) Count() int {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return len(b.segments)
}

// Has returns true if a segment with the given name exists.
func (b *SegmentBuffer) Has(name string) bool {
	b.mu.RLock()
	defer b.mu.RUnlock()

	for _, s := range b.segments {
		if s.Name == name {
			return true
		}
	}
	return false
}

// Fetcher polls an SRS HLS playlist and downloads new segments into a buffer.
type Fetcher struct {
	srsURL       string
	streamID     string
	buffer       *SegmentBuffer
	BytesFromSRS *atomic.Int64
	httpClient   *http.Client
	log          *logrus.Entry
}

// NewFetcher creates a new HLS fetcher.
func NewFetcher(srsURL, streamID string, buffer *SegmentBuffer, log *logrus.Entry) *Fetcher {
	return &Fetcher{
		srsURL:       srsURL,
		streamID:     streamID,
		buffer:       buffer,
		BytesFromSRS: &atomic.Int64{},
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		log: log,
	}
}

// Start begins polling the SRS playlist and downloading new segments.
func (f *Fetcher) Start(ctx context.Context) {
	// SRS flat HLS layout: /live/{stream}.m3u8 and /live/{stream}-{seq}.ts
	playlistURL := fmt.Sprintf("%s/live/%s.m3u8", f.srsURL, f.streamID)
	pollInterval := 2 * time.Second

	f.log.WithFields(logrus.Fields{
		"operation":    "hls_fetch",
		"playlist_url": playlistURL,
	}).Info("Starting HLS fetcher")

	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			f.log.WithField("operation", "hls_fetch").Info("HLS fetcher stopped")
			return
		case <-ticker.C:
			if err := f.pollPlaylist(ctx, playlistURL); err != nil {
				f.log.WithFields(logrus.Fields{
					"operation": "hls_fetch",
				}).WithError(err).Warn("Failed to poll playlist")
			}
		}
	}
}

// pollPlaylist fetches the M3U8 playlist and downloads any new segments.
// Handles SRS two-level playlists: master → variant → segments.
func (f *Fetcher) pollPlaylist(ctx context.Context, playlistURL string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", playlistURL, nil)
	if err != nil {
		return fmt.Errorf("create playlist request: %w", err)
	}

	resp, err := f.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("fetch playlist: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("playlist returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read playlist body: %w", err)
	}

	content := string(body)

	// Check if this is a master playlist (contains #EXT-X-STREAM-INF)
	// If so, extract the variant URL and fetch that instead
	if strings.Contains(content, "#EXT-X-STREAM-INF") {
		variantURL := extractVariantURL(content, playlistURL)
		if variantURL == "" {
			return fmt.Errorf("master playlist has no variant URL")
		}
		return f.pollPlaylist(ctx, variantURL)
	}

	segments := ParseM3U8(content)

	for _, seg := range segments {
		if f.buffer.Has(seg.Name) {
			continue
		}

		data, err := f.downloadSegment(ctx, seg.RawURL)
		if err != nil {
			f.log.WithFields(logrus.Fields{
				"operation": "hls_fetch",
				"segment":   seg.Name,
			}).WithError(err).Warn("Failed to download segment")
			continue
		}

		f.BytesFromSRS.Add(int64(len(data)))
		f.buffer.Add(Segment{
			Name:      seg.Name,
			Data:      data,
			Duration:  seg.Duration,
			FetchedAt: time.Now(),
		})

		f.log.WithFields(logrus.Fields{
			"operation": "hls_fetch",
			"segment":   seg.Name,
			"bytes":     len(data),
		}).Debug("Downloaded segment")
	}

	return nil
}

// extractVariantURL parses a master playlist and returns the absolute variant URL.
func extractVariantURL(content, baseURL string) string {
	lines := strings.Split(strings.TrimSpace(content), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// This is the variant URL line (first non-comment, non-empty line after #EXT-X-STREAM-INF)
		if strings.HasPrefix(line, "http://") || strings.HasPrefix(line, "https://") {
			return line
		}
		// Relative URL — resolve against base
		if strings.HasPrefix(line, "/") {
			// Absolute path — extract scheme+host from baseURL
			idx := strings.Index(baseURL[8:], "/") // skip "http://" or "https://"
			if idx >= 0 {
				return baseURL[:idx+8] + line
			}
			return baseURL + line
		}
		// Same-directory relative URL
		lastSlash := strings.LastIndex(baseURL, "/")
		if lastSlash >= 0 {
			return baseURL[:lastSlash+1] + line
		}
		return baseURL + "/" + line
	}
	return ""
}

// downloadSegment downloads a single .ts segment from SRS.
// rawURL may be a relative name like "stream-0.ts?hls_ctx=xxx" or absolute URL.
func (f *Fetcher) downloadSegment(ctx context.Context, rawURL string) ([]byte, error) {
	var segURL string
	if strings.HasPrefix(rawURL, "http://") || strings.HasPrefix(rawURL, "https://") {
		segURL = rawURL
	} else {
		// SRS flat layout: segments are at /live/{name} (same level as playlist)
		segURL = fmt.Sprintf("%s/live/%s", f.srsURL, rawURL)
	}

	req, err := http.NewRequestWithContext(ctx, "GET", segURL, nil)
	if err != nil {
		return nil, fmt.Errorf("create segment request: %w", err)
	}

	resp, err := f.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch segment: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("segment returned status %d", resp.StatusCode)
	}

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read segment body: %w", err)
	}

	return data, nil
}

// M3U8Segment represents a parsed segment entry from an M3U8 playlist.
type M3U8Segment struct {
	Name     string  // Clean name without query params (e.g. "stream-0.ts")
	Duration float64
	RawURL   string // Full URL as it appears in playlist, may include query params
}

// ParseM3U8 parses an M3U8 playlist string and returns segment entries.
// It looks for #EXTINF: duration lines followed by .ts URLs.
// ParseM3U8 parses an M3U8 playlist string and returns segment entries.
// It looks for #EXTINF: duration lines followed by .ts URLs.
// Handles SRS-style query parameters on segment names (e.g. foo.ts?hls_ctx=xxx).
func ParseM3U8(content string) []M3U8Segment {
	var segments []M3U8Segment
	lines := strings.Split(strings.TrimSpace(content), "\n")

	var duration float64
	for _, line := range lines {
		line = strings.TrimSpace(line)

		if strings.HasPrefix(line, "#EXTINF:") {
			// Parse duration: #EXTINF:2.000,
			durStr := strings.TrimPrefix(line, "#EXTINF:")
			durStr = strings.TrimSuffix(durStr, ",")
			// Remove any trailing text after comma
			if idx := strings.Index(durStr, ","); idx >= 0 {
				durStr = durStr[:idx]
			}
			fmt.Sscanf(durStr, "%f", &duration)
		} else if !strings.HasPrefix(line, "#") && line != "" && isSegmentLine(line) {
			// Strip query parameters for the segment name (used as buffer key)
			name := line
			if idx := strings.Index(name, "?"); idx >= 0 {
				name = name[:idx]
			}
			segments = append(segments, M3U8Segment{
				Name:     name,
				Duration: duration,
				RawURL:   line, // preserve full URL with query params for downloading
			})
			duration = 0
		}
	}

	return segments
}

// isSegmentLine returns true if the line looks like a .ts segment reference.
// Handles both plain "foo.ts" and query-param "foo.ts?hls_ctx=xxx" forms.
func isSegmentLine(line string) bool {
	// Strip query params for suffix check
	path := line
	if idx := strings.Index(path, "?"); idx >= 0 {
		path = path[:idx]
	}
	return strings.HasSuffix(path, ".ts")
}
