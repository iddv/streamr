package bandwidth

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/iddv/streamr/node-client-go/internal/coordinator"
)

const (
	reportInterval = 60 * time.Second
	maxQueueSize   = 100
)

// BandwidthReport represents a single bandwidth measurement report.
type BandwidthReport struct {
	BytesTransferred  int64     `json:"bytes_transferred"`
	StartInterval     time.Time `json:"start_interval"`
	EndInterval       time.Time `json:"end_interval"`
	SourceBitrateKbps int       `json:"source_bitrate_kbps"`
}

// Reporter periodically measures and reports bandwidth to the coordinator.
type Reporter struct {
	client         *coordinator.Client
	sessionID      string
	bytesFromSRS   *atomic.Int64
	bytesToViewers *atomic.Int64
	queue          []BandwidthReport
	mu             sync.Mutex
	log            *logrus.Entry
}

// NewReporter creates a new bandwidth reporter.
func NewReporter(
	client *coordinator.Client,
	sessionID string,
	bytesFromSRS *atomic.Int64,
	bytesToViewers *atomic.Int64,
	log *logrus.Entry,
) *Reporter {
	return &Reporter{
		client:         client,
		sessionID:      sessionID,
		bytesFromSRS:   bytesFromSRS,
		bytesToViewers: bytesToViewers,
		queue:          make([]BandwidthReport, 0),
		log:            log,
	}
}

// Start begins the bandwidth reporting loop.
func (r *Reporter) Start(ctx context.Context) {
	ticker := time.NewTicker(reportInterval)
	defer ticker.Stop()

	intervalStart := time.Now().UTC()

	r.log.WithField("operation", "bandwidth_report").Info("Starting bandwidth reporter")

	for {
		select {
		case <-ctx.Done():
			r.log.WithField("operation", "bandwidth_report").Info("Bandwidth reporter stopped")
			return
		case <-ticker.C:
			now := time.Now().UTC()

			// Read and reset counters
			bytesFromSRS := r.bytesFromSRS.Swap(0)
			bytesToViewers := r.bytesToViewers.Swap(0)
			totalBytes := bytesFromSRS + bytesToViewers

			// Calculate source bitrate in kbps
			elapsed := now.Sub(intervalStart).Seconds()
			bitrateKbps := 0
			if elapsed > 0 {
				bitrateKbps = int((float64(bytesFromSRS) * 8) / (elapsed * 1000))
			}

			report := BandwidthReport{
				BytesTransferred:  totalBytes,
				StartInterval:     intervalStart,
				EndInterval:       now,
				SourceBitrateKbps: bitrateKbps,
			}

			intervalStart = now

			r.submitReport(report)
		}
	}
}

// submitReport attempts to submit a report and any queued reports.
func (r *Reporter) submitReport(report BandwidthReport) {
	r.mu.Lock()
	defer r.mu.Unlock()

	// Try to submit queued reports first
	if len(r.queue) > 0 {
		remaining := make([]BandwidthReport, 0)
		for _, queued := range r.queue {
			if err := r.sendReport(queued); err != nil {
				remaining = append(remaining, queued)
			}
		}
		r.queue = remaining
	}

	// Submit current report
	if err := r.sendReport(report); err != nil {
		r.log.WithFields(logrus.Fields{
			"operation":   "bandwidth_report",
			"queue_size":  len(r.queue),
			"bytes":       report.BytesTransferred,
		}).WithError(err).Warn("Failed to submit bandwidth report, queuing")

		if len(r.queue) < maxQueueSize {
			r.queue = append(r.queue, report)
		} else {
			r.log.WithField("operation", "bandwidth_report").Warn("Report queue full, dropping oldest report")
			r.queue = r.queue[1:]
			r.queue = append(r.queue, report)
		}
	} else {
		r.log.WithFields(logrus.Fields{
			"operation": "bandwidth_report",
			"bytes":     report.BytesTransferred,
		}).Debug("Bandwidth report submitted")
	}
}

// sendReport sends a single bandwidth report to the coordinator.
func (r *Reporter) sendReport(report BandwidthReport) error {
	payload := map[string]interface{}{
		"bytes_transferred":   report.BytesTransferred,
		"start_interval":      report.StartInterval.Format(time.RFC3339),
		"end_interval":        report.EndInterval.Format(time.RFC3339),
		"source_bitrate_kbps": report.SourceBitrateKbps,
	}

	resp, err := r.client.AuthenticatedRequest(
		"POST",
		"/api/v1/sessions/"+r.sessionID+"/bandwidth-report",
		payload,
	)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return &ReportError{StatusCode: resp.StatusCode}
	}

	return nil
}

// QueueSize returns the current number of queued reports.
func (r *Reporter) QueueSize() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return len(r.queue)
}

// ReportError represents a failed report submission.
type ReportError struct {
	StatusCode int
}

func (e *ReportError) Error() string {
	return fmt.Sprintf("bandwidth report failed with status %d", e.StatusCode)
}
