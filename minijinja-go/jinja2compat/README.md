# Jinja2 compatibility corpus

`testdata/cases.json` holds a set of templates together with the output Jinja2
produces for them. `compat_test.go` renders the same templates with MiniJinja
and compares the results.

Every case that does not match Jinja2 must be listed in `knownDivergences` with
the reason. The test fails in both directions:

* a new mismatch that is not listed is a regression;
* a listed case that starts matching means the divergence is gone and the entry
  has to be removed.

To regenerate the corpus after adding cases to `gen_cases.py`, run it with a
Python that has Jinja2 installed:

```sh
python3 gen_cases.py
```

The Go test never shells out to Python; it only reads the recorded outputs, so
Python is needed for regeneration only.
