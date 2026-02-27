package logging

import (
	"strings"

	"github.com/sirupsen/logrus"
)

// SetupLogger configures the global logrus logger with JSON formatting and the given level.
func SetupLogger(level string) {
	logrus.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: "2006-01-02T15:04:05.000Z07:00",
	})

	lvl, err := logrus.ParseLevel(strings.ToLower(level))
	if err != nil {
		logrus.WithError(err).Warn("Invalid log level, defaulting to info")
		lvl = logrus.InfoLevel
	}
	logrus.SetLevel(lvl)
}

// NewLogger creates a logrus entry with node_id and stream_id fields pre-set.
func NewLogger(nodeID, streamID string) *logrus.Entry {
	return logrus.WithFields(logrus.Fields{
		"node_id":   nodeID,
		"stream_id": streamID,
	})
}
