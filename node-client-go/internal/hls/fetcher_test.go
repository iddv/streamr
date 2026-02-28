package hls

import (
	"testing"
)

// ---------------------------------------------------------------------------
// SegmentBuffer tests
// ---------------------------------------------------------------------------

func TestSegmentBuffer_Add_And_GetAll(t *testing.T) {
	buf := NewSegmentBuffer(3)
	buf.Add(Segment{Name: "seg0.ts", Data: []byte("a")})
	buf.Add(Segment{Name: "seg1.ts", Data: []byte("bb")})

	all := buf.GetAll()
	if len(all) != 2 {
		t.Fatalf("expected 2 segments, got %d", len(all))
	}
	if all[0].Name != "seg0.ts" || all[1].Name != "seg1.ts" {
		t.Error("segment order incorrect")
	}
}

func TestSegmentBuffer_RingEviction(t *testing.T) {
	buf := NewSegmentBuffer(3)
	for i := 0; i < 5; i++ {
		buf.Add(Segment{Name: segName(i), Data: []byte("x")})
	}
	if buf.Count() != 3 {
		t.Fatalf("expected 3 segments after overflow, got %d", buf.Count())
	}
	all := buf.GetAll()
	// Oldest two (seg0, seg1) should be evicted
	if all[0].Name != "seg2.ts" {
		t.Errorf("expected seg2.ts as oldest, got %s", all[0].Name)
	}
	if all[2].Name != "seg4.ts" {
		t.Errorf("expected seg4.ts as newest, got %s", all[2].Name)
	}
}

func TestSegmentBuffer_MaxSize_Invariant(t *testing.T) {
	buf := NewSegmentBuffer(30)
	for i := 0; i < 50; i++ {
		buf.Add(Segment{Name: segName(i), Data: make([]byte, 100)})
	}
	if buf.Count() > 30 {
		t.Errorf("buffer exceeded max size: %d", buf.Count())
	}
}

func TestSegmentBuffer_GetByName(t *testing.T) {
	buf := NewSegmentBuffer(5)
	buf.Add(Segment{Name: "a.ts", Data: []byte("aaa")})
	buf.Add(Segment{Name: "b.ts", Data: []byte("bbb")})

	seg := buf.GetByName("b.ts")
	if seg == nil {
		t.Fatal("expected to find b.ts")
	}
	if string(seg.Data) != "bbb" {
		t.Errorf("expected data bbb, got %s", string(seg.Data))
	}

	missing := buf.GetByName("c.ts")
	if missing != nil {
		t.Error("expected nil for missing segment")
	}
}

func TestSegmentBuffer_Has(t *testing.T) {
	buf := NewSegmentBuffer(5)
	buf.Add(Segment{Name: "x.ts"})
	if !buf.Has("x.ts") {
		t.Error("expected Has to return true")
	}
	if buf.Has("y.ts") {
		t.Error("expected Has to return false for missing")
	}
}

// ---------------------------------------------------------------------------
// ParseM3U8 tests
// ---------------------------------------------------------------------------

func TestParseM3U8_Standard(t *testing.T) {
	playlist := `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:2.000,
seg100.ts
#EXTINF:2.500,
seg101.ts
#EXTINF:1.800,
seg102.ts
`
	segments := ParseM3U8(playlist)
	if len(segments) != 3 {
		t.Fatalf("expected 3 segments, got %d", len(segments))
	}
	if segments[0].Name != "seg100.ts" {
		t.Errorf("expected seg100.ts, got %s", segments[0].Name)
	}
	if segments[0].Duration != 2.0 {
		t.Errorf("expected duration 2.0, got %f", segments[0].Duration)
	}
	if segments[2].Name != "seg102.ts" {
		t.Errorf("expected seg102.ts, got %s", segments[2].Name)
	}
}

func TestParseM3U8_Empty(t *testing.T) {
	segments := ParseM3U8("")
	if len(segments) != 0 {
		t.Errorf("expected 0 segments for empty playlist, got %d", len(segments))
	}
}

func TestParseM3U8_NoSegments(t *testing.T) {
	playlist := `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3
`
	segments := ParseM3U8(playlist)
	if len(segments) != 0 {
		t.Errorf("expected 0 segments, got %d", len(segments))
	}
}

func TestParseM3U8_DurationWithTrailingText(t *testing.T) {
	playlist := `#EXTM3U
#EXTINF:3.500,title
clip.ts
`
	segments := ParseM3U8(playlist)
	if len(segments) != 1 {
		t.Fatalf("expected 1 segment, got %d", len(segments))
	}
	if segments[0].Duration != 3.5 {
		t.Errorf("expected 3.5, got %f", segments[0].Duration)
	}
}

// helper
func segName(i int) string {
	return "seg" + string(rune('0'+i%10)) + ".ts"
}

func TestParseM3U8_SRSQueryParams(t *testing.T) {
	// SRS appends ?hls_ctx=xxx to segment names in variant playlists
	playlist := `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:31
#EXT-X-TARGETDURATION:2
#EXTINF:2.000, no desc
e2e-phase8-restream-31.ts?hls_ctx=1lfwew84
#EXTINF:2.000, no desc
e2e-phase8-restream-32.ts?hls_ctx=1lfwew84
`
	segments := ParseM3U8(playlist)
	if len(segments) != 2 {
		t.Fatalf("expected 2 segments, got %d", len(segments))
	}
	// Name should be clean (no query params)
	if segments[0].Name != "e2e-phase8-restream-31.ts" {
		t.Errorf("expected clean name, got %s", segments[0].Name)
	}
	// RawURL should preserve query params
	if segments[0].RawURL != "e2e-phase8-restream-31.ts?hls_ctx=1lfwew84" {
		t.Errorf("expected raw URL with query params, got %s", segments[0].RawURL)
	}
	if segments[0].Duration != 2.0 {
		t.Errorf("expected duration 2.0, got %f", segments[0].Duration)
	}
}

func TestParseM3U8_StandardHasRawURL(t *testing.T) {
	// Without query params, RawURL should equal Name
	playlist := `#EXTM3U
#EXTINF:2.000,
seg100.ts
`
	segments := ParseM3U8(playlist)
	if len(segments) != 1 {
		t.Fatalf("expected 1 segment, got %d", len(segments))
	}
	if segments[0].Name != "seg100.ts" {
		t.Errorf("expected seg100.ts, got %s", segments[0].Name)
	}
	if segments[0].RawURL != "seg100.ts" {
		t.Errorf("expected RawURL=seg100.ts, got %s", segments[0].RawURL)
	}
}
