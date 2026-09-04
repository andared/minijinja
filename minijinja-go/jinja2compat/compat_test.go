// Package jinja2compat compares MiniJinja's rendering against Jinja2's.
//
// The corpus in testdata/cases.json holds templates together with the output
// Jinja2 produced for them (see gen_cases.py). This test renders the same
// templates with MiniJinja and fails on any difference that is not recorded in
// knownDivergences, so both new regressions and fixed divergences are noticed.
package jinja2compat

import (
	"encoding/json"
	"os"
	"testing"

	minijinja "github.com/mitsuhiko/minijinja/minijinja-go/v2"
)

type testCase struct {
	Name     string `json:"name"`
	Template string `json:"template"`
	Jinja2   string `json:"jinja2"`
	Error    bool   `json:"error"`
}

type corpus struct {
	Jinja2Version string         `json:"jinja2_version"`
	Context       map[string]any `json:"context"`
	Cases         []testCase     `json:"cases"`
}

// knownDivergences lists every case where MiniJinja does not match Jinja2,
// with the reason. A case that starts matching must be removed from this map.
var knownDivergences = map[string]string{
	"args/too-many-positional":       "unexpected filter arguments are ignored instead of raising",
	"args/unknown-kwarg-on-join":     "unexpected filter arguments are ignored instead of raising",
	"args/unknown-kwarg-on-length":   "unexpected filter arguments are ignored instead of raising",
	"bool/abs":                       "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"bool/add-int":                   "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"bool/compare-with-int":          "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"bool/is-number":                 "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"bool/is-odd":                    "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"bool/multiply-int":              "booleans are not numbers in MiniJinja: no arithmetic, no numeric comparison, not a number for tests",
	"flow/crlf":                      "Jinja2 normalises CRLF to LF in the lexer",
	"flow/loop-changed":              "loop.changed() always reports a change: the loop object is rebuilt on every iteration",
	"map/dict-function-order":        "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/dictsort":                   "pairs render as lists, Jinja2 renders Python tuples",
	"map/first":                      "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/items":                      "pairs render as lists and are ordered by key",
	"map/iterate-order":              "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/list":                       "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/literal-order":              "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/render":                     "mappings render JSON-ish and are ordered by key, Jinja2 uses Python repr and insertion order",
	"map/tojson":                     "tojson prints without spaces after the separators",
	"map/tojson-cyrillic":            "tojson keeps non-ASCII characters where Jinja2 escapes them",
	"map/unpack-in-loop":             "mappings are ordered by key, Jinja2 keeps insertion order",
	"map/urlencode":                  "mappings are ordered by key, Jinja2 keeps insertion order",
	"missing/callable-test":          "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/center":                 "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/filesizeformat":         "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/forceescape":            "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/pprint":                 "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/striptags":              "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/truncate":               "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/urlize":                 "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/wordcount":              "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/wordwrap":               "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"missing/xmlattr":                "filter or test that exists only in Jinja2, some of them in minijinja-contrib, which the Go port lacks",
	"none/length":                    "Jinja2 raises for len(none) because default does not replace none; MiniJinja returns 0",
	"num/float-from-word":            "float errors on input it cannot parse instead of falling back to 0.0",
	"num/int-from-empty-string":      "int errors on input it cannot parse instead of falling back to 0, and takes no default or base argument",
	"num/int-from-list":              "int errors on input it cannot parse instead of falling back to 0, and takes no default or base argument",
	"num/int-from-word":              "int errors on input it cannot parse instead of falling back to 0, and takes no default or base argument",
	"num/int-overflow":               "int saturates at the i64 maximum where Jinja2 keeps arbitrary precision",
	"num/int-with-base":              "int errors on input it cannot parse instead of falling back to 0, and takes no default or base argument",
	"num/int-with-default":           "int errors on input it cannot parse instead of falling back to 0, and takes no default or base argument",
	"num/modulo-negative-dividend":   "Go remainder instead of the euclidean remainder Rust MiniJinja computes",
	"num/modulo-negative-divisor":    "euclidean remainder differs from the sign-of-divisor rule Python uses",
	"num/round-ceil":                 "round is half-away-from-zero where Python is half-to-even, and takes no method argument",
	"num/round-floor":                "round is half-away-from-zero where Python is half-to-even, and takes no method argument",
	"num/round-half-down":            "round is half-away-from-zero where Python is half-to-even, and takes no method argument",
	"num/round-half-up":              "round is half-away-from-zero where Python is half-to-even, and takes no method argument",
	"num/round-negative-half":        "round is half-away-from-zero where Python is half-to-even, and takes no method argument",
	"num/whole-float-arithmetic":     "floats from the Go context lose their fractional part (fromReflectValue turns 4.0 into 4)",
	"num/whole-float-render":         "floats from the Go context lose their fractional part (fromReflectValue turns 4.0 into 4)",
	"pymethod/dict-get":              "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/dict-get-default":      "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/dict-items":            "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/dict-keys":             "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-format-positional": "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-format-spec":       "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-replace":           "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-split":             "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-startswith":        "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-strip":             "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"pymethod/str-upper":             "Python methods on plain values need the pycompat shim from minijinja-contrib, which the Go port lacks",
	"seq/groupby":                    "sequences render JSON-ish rather than as Python repr",
	"seq/join-attribute":             "the attribute argument of min, max, sum and join is ignored instead of honoured",
	"seq/map-attribute":              "sequences render JSON-ish rather than as Python repr",
	"seq/map-filter":                 "sequences render JSON-ish rather than as Python repr",
	"seq/max-attribute":              "the attribute argument of min, max, sum and join is ignored instead of honoured",
	"seq/min-attribute":              "the attribute argument of min, max, sum and join is ignored instead of honoured",
	"seq/repeat-negative":            "Jinja2 yields an empty sequence for a negative repeat count, MiniJinja errors",
	"seq/selectattr":                 "sequences render JSON-ish rather than as Python repr",
	"seq/sort-attribute":             "sequences render JSON-ish rather than as Python repr",
	"seq/sort-strings":               "sequences render JSON-ish rather than as Python repr",
	"seq/string-is-sequence":         "strings are not sequences in MiniJinja",
	"seq/sum-attribute":              "the attribute argument of min, max, sum and join is ignored instead of honoured",
	"seq/unique-attribute":           "sequences render JSON-ish rather than as Python repr",
	"str/escape":                     "Jinja2 escapes quotes as &#34; / &#39;, MiniJinja uses &quot; / &#x27;",
	"str/escape-quote":               "Jinja2 escapes quotes as &#34; / &#39;, MiniJinja uses &quot; / &#x27;",
	"str/printf-named":               "the format filter does not accept keyword arguments for %(name)s specs",
	"str/printf-operator":            "the % operator is not implemented for strings (Jinja2 formats printf-style)",
	"str/repeat-negative":            "Jinja2 yields an empty string for a negative repeat count, MiniJinja errors",
	"str/string-of-whole-float":      "floats from the Go context lose their fractional part (fromReflectValue turns 4.0 into 4)",
	"test/lower-empty":               "is lower is vacuously true for strings without cased characters",
	"test/lower-no-cased-chars":      "is lower is vacuously true for strings without cased characters",
	"test/upper-empty":               "is upper is vacuously true for strings without cased characters",
	"test/upper-no-cased-chars":      "is upper is vacuously true for strings without cased characters",
	"test/whole-float-is-float":      "floats from the Go context lose their fractional part, so they test as integers",
	"test/whole-float-is-integer":    "floats from the Go context lose their fractional part, so they test as integers",
}

func TestJinja2Compatibility(t *testing.T) {
	raw, err := os.ReadFile("testdata/cases.json")
	if err != nil {
		t.Fatalf("read corpus: %v", err)
	}
	var c corpus
	if err := json.Unmarshal(raw, &c); err != nil {
		t.Fatalf("parse corpus: %v", err)
	}
	if len(c.Cases) == 0 {
		t.Fatal("corpus is empty")
	}

	seen := make(map[string]bool, len(c.Cases))
	for _, tc := range c.Cases {
		if seen[tc.Name] {
			t.Fatalf("duplicate case name %q", tc.Name)
		}
		seen[tc.Name] = true

		rendered, renderErr := render(&c, tc.Template)
		matches := renderErr == nil && !tc.Error && rendered == tc.Jinja2
		if tc.Error && renderErr != nil {
			matches = true
		}
		reason, listed := knownDivergences[tc.Name]

		switch {
		case matches && listed:
			t.Errorf("%s: matches Jinja2 now, drop it from knownDivergences (was: %s)", tc.Name, reason)
		case !matches && !listed:
			t.Errorf("%s: %s\n  template:  %q\n  jinja2:    %s\n  minijinja: %s",
				tc.Name, "differs from Jinja2 and is not in knownDivergences",
				tc.Template, describe(tc.Jinja2, tc.Error, nil), describe(rendered, false, renderErr))
		}
	}

	for name := range knownDivergences {
		if !seen[name] {
			t.Errorf("knownDivergences has %q, which is not in the corpus", name)
		}
	}
}

func render(c *corpus, source string) (string, error) {
	env := minijinja.NewEnvironment()
	if err := env.AddTemplate("case", source); err != nil {
		return "", err
	}
	tmpl, err := env.GetTemplate("case")
	if err != nil {
		return "", err
	}
	return tmpl.Render(c.Context)
}

func describe(out string, isError bool, err error) string {
	if err != nil {
		return "error: " + err.Error()
	}
	if isError {
		return "error: " + out
	}
	return "output: " + quote(out)
}

func quote(s string) string {
	quoted, _ := json.Marshal(s)
	return string(quoted)
}
