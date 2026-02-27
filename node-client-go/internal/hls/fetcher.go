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
	playlistURL := fmt.Sprintf("%s/live/%s/index.m3u8", f.srsURL, f.streamID)
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

	segments := ParseM3U8(string(body))

	for _, seg := range segments {
		if f.buffer.Has(seg.Name) {
			continue
		}

		data, err := f.downloadSegment(ctx, seg.Name)
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

// downloadSegment downloads a single .ts segment from SRS.
func (f *Fetcher) downloadSegment(ctx context.Context, name string) ([]byte, error) {
	segURL := fmt.Sprintf("%s/live/%s/%s", f.srsURL, f.streamID, name)

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
	Name     string
	Duration float64
}

// ParseM3U8 parses an M3U8 playlist string and returns segment entries.
// It looks for #EXTINF: duration lines followed by .ts URLs.
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
		} else if strings.HasSuffix(line, ".ts") && !strings.HasPrefix(line, "#") {
			segments = append(segments, M3U8Segment{
				Name:     line,
				Duration: duration,
			})
			duration = 0
		}
	}

	return segments
}
