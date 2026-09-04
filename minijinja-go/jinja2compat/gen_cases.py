#!/usr/bin/env python3
"""Records Jinja2 behaviour for the compatibility corpus.

Run this with a Python that has Jinja2 installed to regenerate
``testdata/cases.json``:

    python3 gen_cases.py

The Go test in this package renders the same templates with MiniJinja and
compares the result against what Jinja2 produced here.
"""

import json
import os

import jinja2
from jinja2 import Environment

CONTEXT = {
    "s": "abc",
    "s_ru": "дом",
    "s_empty": "",
    "s_pad": "  x  ",
    "s_up": "ABC",
    "s_dash": "a-b-c",
    "s_num": "42",
    "s_float": "1.5",
    "i": 7,
    "i_neg": -7,
    "i_zero": 0,
    "f": 2.5,
    "f_neg": -2.5,
    "f_whole": 4.0,
    "f_big": 1e20,
    "t": True,
    "no": False,
    "nil": None,
    "l": [3, 1, 2],
    "l_str": ["b", "A", "c"],
    "l_empty": [],
    "l_dup": [1, 1, 2],
    "d": {"b": 2, "a": 1},
    "d_empty": {},
    "objs": [{"n": 2, "k": "x"}, {"n": 1, "k": "y"}, {"n": 3, "k": "x"}],
}

CASES = [
    # --- string filters ---
    ("str/upper", "{{ s|upper }}"),
    ("str/upper-cyrillic", "{{ s_ru|upper }}"),
    ("str/lower", "{{ s_up|lower }}"),
    ("str/capitalize", "{{ 'hello world'|capitalize }}"),
    ("str/capitalize-cyrillic", "{{ 'дом мой'|capitalize }}"),
    ("str/title", "{{ 'hello world'|title }}"),
    ("str/trim", "{{ s_pad|trim }}"),
    ("str/trim-chars", "{{ '/x/'|trim('/') }}"),
    ("str/replace", "{{ s_dash|replace('-', '_') }}"),
    ("str/length", "{{ s_ru|length }}"),
    ("str/index", "{{ s[1] }}"),
    ("str/index-negative", "{{ s[-1] }}"),
    ("str/slice", "{{ s_dash[0:3] }}"),
    ("str/slice-open-end", "{{ s_dash[2:] }}"),
    ("str/slice-negative", "{{ s_dash[:-2] }}"),
    ("str/slice-cyrillic", "{{ s_ru[0:1] }}"),
    ("str/join", "{{ l|join('-') }}"),
    ("str/join-empty", "{{ l_empty|join('-') }}"),
    ("str/indent", "{{ 'a\\nb'|indent(2) }}"),
    ("str/escape", "{{ '<a href=\"x\">'|e }}"),
    ("str/escape-quote", "{{ \"it's\"|e }}"),
    ("str/string-of-int", "{{ i|string }}"),
    ("str/string-of-float", "{{ f|string }}"),
    ("str/string-of-whole-float", "{{ f_whole|string }}"),
    ("str/string-of-none", "{{ nil|string }}"),
    ("str/string-of-bool", "{{ t|string }}"),
    ("str/urlencode", "{{ 'a b'|urlencode }}"),
    ("str/repeat", "{{ 'ab' * 2 }}"),
    ("str/repeat-zero", "[{{ 'ab' * 0 }}]"),
    ("str/repeat-negative", "[{{ 'ab' * -1 }}]"),
    ("str/concat-plus", "{{ 'a' + s }}"),
    ("str/concat-tilde", "{{ s ~ i }}"),
    ("str/concat-tilde-none", "{{ s ~ nil }}"),
    ("str/printf-operator", "{{ '%s-%s' % (1, 2) }}"),
    ("str/printf-filter", "{{ '%s-%s'|format(1, 2) }}"),
    ("str/printf-named", "{{ '%(a)s'|format(a=1) }}"),
    # --- numbers ---
    ("num/int-from-numeric-string", "{{ s_num|int }}"),
    ("num/int-from-float-string", "{{ s_float|int }}"),
    ("num/int-from-empty-string", "[{{ s_empty|int }}]"),
    ("num/int-from-word", "[{{ s|int }}]"),
    ("num/int-from-list", "[{{ l|int }}]"),
    ("num/int-with-default", "{{ s|int(5) }}"),
    ("num/int-with-base", "{{ 'ff'|int(0, 16) }}"),
    ("num/int-overflow", "{{ f_big|int }}"),
    ("num/float-from-word", "[{{ s|float }}]"),
    ("num/float-from-numeric-string", "{{ s_float|float }}"),
    ("num/abs", "{{ i_neg|abs }}"),
    ("num/abs-float", "{{ f_neg|abs }}"),
    ("num/round-half-up", "{{ 2.5|round }}"),
    ("num/round-half-down", "{{ 0.5|round }}"),
    ("num/round-negative-half", "{{ -2.5|round }}"),
    ("num/round-precision", "{{ 1.2345|round(2) }}"),
    ("num/round-ceil", "{{ 1.1|round(0, 'ceil') }}"),
    ("num/round-floor", "{{ 1.9|round(0, 'floor') }}"),
    ("num/div", "{{ 1/3 }}"),
    ("num/div-whole", "{{ 4/2 }}"),
    ("num/floordiv-negative-dividend", "{{ -7 // 2 }}"),
    ("num/floordiv-negative-divisor", "{{ 7 // -2 }}"),
    ("num/modulo", "{{ 7 % 3 }}"),
    ("num/modulo-negative-dividend", "{{ -7 % 3 }}"),
    ("num/modulo-negative-divisor", "{{ 7 % -3 }}"),
    ("num/modulo-float", "{{ 7.5 % 2 }}"),
    ("num/pow", "{{ 2 ** 3 }}"),
    ("num/pow-negative-exponent", "{{ 2 ** -1 }}"),
    ("num/whole-float-render", "{{ f_whole }}"),
    ("num/whole-float-arithmetic", "{{ f_whole + 1 }}"),
    ("num/big-float-render", "{{ f_big }}"),
    ("num/sum", "{{ l|sum }}"),
    ("num/sum-empty", "{{ l_empty|sum }}"),
    ("num/min", "{{ l|min }}"),
    ("num/max", "{{ l|max }}"),
    # --- booleans and none ---
    ("bool/render-true", "{{ t }}"),
    ("bool/render-false", "{{ no }}"),
    ("bool/add-int", "{{ t + 1 }}"),
    ("bool/multiply-int", "{{ t * 3 }}"),
    ("bool/compare-with-int", "{{ 1 > t }}"),
    ("bool/equal-to-int", "{{ t == 1 }}"),
    ("bool/abs", "{{ t|abs }}"),
    ("bool/is-number", "{{ t is number }}"),
    ("bool/is-odd", "{{ t is odd }}"),
    ("bool/is-boolean", "{{ t is boolean }}"),
    ("none/render", "[{{ nil }}]"),
    ("none/is-none", "{{ nil is none }}"),
    ("none/default", "{{ nil|default('D') }}"),
    ("none/default-boolean", "{{ nil|default('D', true) }}"),
    ("none/length", "{{ nil|default('')|length }}"),
    # --- sequences ---
    ("seq/render", "{{ l }}"),
    ("seq/first", "{{ l|first }}"),
    ("seq/last", "{{ l|last }}"),
    ("seq/length", "{{ l|length }}"),
    ("seq/sort", "{{ l|sort }}"),
    ("seq/sort-strings", "{{ l_str|sort }}"),
    ("seq/sort-reverse", "{{ l|sort(reverse=true) }}"),
    ("seq/sort-attribute", "{{ objs|sort(attribute='n') }}"),
    ("seq/reverse", "{{ l|reverse|list }}"),
    ("seq/unique", "{{ l_dup|unique|list }}"),
    ("seq/unique-attribute", "{{ objs|unique(attribute='k')|list }}"),
    ("seq/slice-filter", "{{ l|slice(2)|list }}"),
    ("seq/batch", "{{ l|batch(2)|list }}"),
    ("seq/map-filter", "{{ l_str|map('upper')|list }}"),
    ("seq/map-attribute", "{{ objs|map(attribute='k')|list }}"),
    ("seq/select", "{{ l|select('odd')|list }}"),
    ("seq/reject", "{{ l|reject('odd')|list }}"),
    ("seq/selectattr", "{{ objs|selectattr('k', 'eq', 'x')|list }}"),
    ("seq/min-attribute", "{{ objs|min(attribute='n') }}"),
    ("seq/max-attribute", "{{ objs|max(attribute='n') }}"),
    ("seq/sum-attribute", "{{ objs|sum(attribute='n') }}"),
    ("seq/join-attribute", "{{ objs|join(',', attribute='n') }}"),
    ("seq/groupby", "{{ objs|groupby('k')|list }}"),
    ("seq/index-negative", "{{ l[-1] }}"),
    ("seq/slice-negative", "{{ l[:-1] }}"),
    ("seq/repeat-negative", "{{ [1] * -1 }}"),
    ("seq/in", "{{ 1 in l }}"),
    ("seq/is-sequence", "{{ l is sequence }}"),
    ("seq/string-is-sequence", "{{ s is sequence }}"),
    ("seq/iterate", "{% for x in l %}[{{ x }}]{% endfor %}"),
    ("seq/iterate-string", "{% for c in 'аб' %}[{{ c }}]{% endfor %}"),
    # --- mappings ---
    ("map/render", "{{ d }}"),
    ("map/literal-order", "{{ {'b': 2, 'a': 1} }}"),
    ("map/dict-function-order", "{{ dict(b=2, a=1) }}"),
    ("map/iterate-order", "{% for k in d %}[{{ k }}]{% endfor %}"),
    ("map/first", "{{ d|first }}"),
    ("map/list", "{{ d|list }}"),
    ("map/length", "{{ d|length }}"),
    ("map/dictsort", "{{ d|dictsort }}"),
    ("map/items", "{{ d|items|list }}"),
    ("map/attribute-access", "{{ d.a }}"),
    ("map/item-access", "{{ d['a'] }}"),
    ("map/in", "{{ 'a' in d }}"),
    ("map/is-mapping", "{{ d is mapping }}"),
    ("map/tojson", "{{ d|tojson }}"),
    ("map/tojson-cyrillic", "{{ {'k': 'дом'}|tojson }}"),
    ("map/urlencode", "{{ d|urlencode }}"),
    ("map/unpack-in-loop", "{% for k, v in d|items %}[{{ k }}={{ v }}]{% endfor %}"),
    # --- tests ---
    ("test/defined", "{{ s is defined }}"),
    ("test/undefined", "{{ nope is undefined }}"),
    ("test/string", "{{ s is string }}"),
    ("test/number-int", "{{ i is number }}"),
    ("test/integer", "{{ i is integer }}"),
    ("test/float", "{{ f is float }}"),
    ("test/whole-float-is-float", "{{ f_whole is float }}"),
    ("test/whole-float-is-integer", "{{ f_whole is integer }}"),
    ("test/even", "{{ i is even }}"),
    ("test/odd", "{{ i is odd }}"),
    ("test/divisibleby", "{{ 9 is divisibleby(3) }}"),
    ("test/lower", "{{ 'abc' is lower }}"),
    ("test/lower-empty", "{{ s_empty is lower }}"),
    ("test/lower-no-cased-chars", "{{ s_float is lower }}"),
    ("test/upper", "{{ s_up is upper }}"),
    ("test/upper-empty", "{{ s_empty is upper }}"),
    ("test/upper-no-cased-chars", "{{ s_num is upper }}"),
    ("test/in", "{{ 1 is in(l) }}"),
    ("test/eq", "{{ 1 is eq(1) }}"),
    ("test/iterable", "{{ l is iterable }}"),
    ("test/string-is-iterable", "{{ s is iterable }}"),
    # --- filter argument handling ---
    ("args/unknown-kwarg-on-length", "{{ l|length(nonsense=1) }}"),
    ("args/unknown-kwarg-on-join", "{{ l|join(',', nonsense=1) }}"),
    ("args/too-many-positional", "{{ l|length(1) }}"),
    ("args/default-two-args", "{{ s_empty|default('D', true) }}"),
    ("args/replace-count", "{{ 'aaa'|replace('a', 'b', 2) }}"),
    # --- control flow and scoping ---
    ("flow/with", "{% with a = 1 %}{{ a }}{% endwith %}"),
    ("flow/namespace", "{% set ns = namespace(x=0) %}{% for i in l %}{% set ns.x = ns.x + i %}{% endfor %}{{ ns.x }}"),
    ("flow/block-set", "{% set v %}text{% endset %}{{ v }}"),
    ("flow/tuple-assign", "{% set a, b = 1, 2 %}{{ a }}{{ b }}"),
    ("flow/macro-default", "{% macro m(a, b='B') %}{{ a }}{{ b }}{% endmacro %}{{ m(1) }}"),
    ("flow/macro-kwargs", "{% macro m(a, b='B') %}{{ a }}{{ b }}{% endmacro %}{{ m(1, b='C') }}"),
    ("flow/loop-index", "{% for x in l %}{{ loop.index }}{% endfor %}"),
    ("flow/loop-cycle", "{% for x in l %}{{ loop.cycle('a', 'b') }}{% endfor %}"),
    ("flow/loop-changed", "{% for x in l_dup %}{{ loop.changed(x) }}{% endfor %}"),
    ("flow/loop-previtem", "{% for x in l %}[{{ loop.previtem|default('-') }}]{% endfor %}"),
    ("flow/loop-else", "{% for x in l_empty %}x{% else %}empty{% endfor %}"),
    ("flow/if-without-else", "{{ 'y' if i }}"),
    ("flow/chained-compare", "{{ 1 < i < 10 }}"),
    ("flow/raw", "{% raw %}{{ x }}{% endraw %}"),
    ("flow/comment", "a{# comment #}b"),
    ("flow/whitespace-control", "{% for x in l -%}  {{ x }}{%- endfor %}"),
    ("flow/trailing-newline", "text\n"),
    ("flow/crlf", "a\r\nb"),
    # --- undefined handling ---
    ("undef/render", "[{{ nope }}]"),
    ("undef/attribute-of-undefined-root", "{{ nope.attr }}"),
    ("undef/attribute-of-known-mapping", "{{ d.nope }}"),
    ("undef/chained-attribute", "{{ d.nope.deep }}"),
    ("undef/default", "{{ nope|default('D') }}"),
    ("undef/in-condition", "{{ 'y' if nope else 'n' }}"),
    ("undef/concat", "[{{ 'a' ~ nope }}]"),
    ("undef/filter", "[{{ nope|upper }}]"),
    # --- python methods on plain values (pycompat territory) ---
    ("pymethod/str-split", "{{ s_dash.split('-')[0] }}"),
    ("pymethod/str-replace", "{{ s.replace('a', 'b') }}"),
    ("pymethod/str-upper", "{{ s.upper() }}"),
    ("pymethod/str-startswith", "{{ s.startswith('a') }}"),
    ("pymethod/str-strip", "{{ s_pad.strip() }}"),
    ("pymethod/str-format-spec", "{{ '{:.2f}'.format(f) }}"),
    ("pymethod/str-format-positional", "{{ '{}-{}'.format(1, 2) }}"),
    ("pymethod/dict-get", "{{ d.get('a') }}"),
    ("pymethod/dict-get-default", "{{ d.get('zz', 7) }}"),
    ("pymethod/dict-items", "{% for k, v in d.items() %}[{{ k }}]{% endfor %}"),
    ("pymethod/dict-keys", "{{ d.keys()|list }}"),
    # --- filters Jinja2 has and MiniJinja does not ---
    ("missing/truncate", "{{ 'hello world, how are you'|truncate(12) }}"),
    ("missing/striptags", "{{ '<b>x</b> y'|striptags }}"),
    ("missing/wordwrap", "{{ 'aaa bbb ccc ddd'|wordwrap(7) }}"),
    ("missing/wordcount", "{{ 'a b c'|wordcount }}"),
    ("missing/filesizeformat", "{{ 1024|filesizeformat }}"),
    ("missing/center", "[{{ 'x'|center(5) }}]"),
    ("missing/forceescape", "{{ '<b>'|forceescape }}"),
    ("missing/xmlattr", "{{ d|xmlattr }}"),
    ("missing/urlize", "{{ 'see example.com'|urlize }}"),
    ("missing/pprint", "{{ s|pprint }}"),
    ("missing/callable-test", "{{ i is callable }}"),
]


def main() -> None:
    env = Environment()
    cases = []
    for name, template in CASES:
        entry = {"name": name, "template": template}
        try:
            entry["jinja2"] = env.from_string(template).render(**json.loads(json.dumps(CONTEXT)))
        except Exception as exc:  # noqa: BLE001 - the error kind is the interesting part
            entry["error"] = True
            entry["jinja2"] = f"{type(exc).__name__}"
        cases.append(entry)

    corpus = {
        "jinja2_version": jinja2.__version__,
        "context": CONTEXT,
        "cases": cases,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "cases.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(corpus, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print(f"wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
