# Sample Trace Decision

A small, dependency-free Python library that makes a deterministic keep-or-drop
sampling decision for a trace id. The same trace id always yields the same
decision for a given rate, so services that share a trace can agree on whether
to record it without talking to each other.

```python
from sample_trace_decision import TraceDecisionSampler

sampler = TraceDecisionSampler(rate=0.1)
if sampler.should_keep("4a3b2c1d0e9f8a7b"):
    # record this trace
    ...
```

`TraceDecisionSampler(rate)` takes a float in `[0.0, 1.0]` and exposes:

- `rate` — the configured sampling rate, as a `float`.
- `should_keep(trace_id: str) -> bool` — `True` if the trace should be kept,
  `False` if it should be dropped. `trace_id` must be a non-empty `str`.

## Why this exists

Distributed traces cross service boundaries. If every service samples
independently using a random coin flip, the pieces of a single trace get
shredded: some spans survive, others vanish, and the trace becomes useless.
A deterministic sampler hashes the trace id so every service makes the same
keep-or-drop decision for the same trace, preserving complete traces for the
ones that are kept.

The trade-off: the decision is fixed by the trace id, so you cannot re-sample
on a per-request basis. If you need to bias sampling by request properties
(latency, error status), wrap this sampler with whatever upstream logic makes
that decision and only hand it the trace id once the decision is made.

## Edge cases worth knowing

- `rate=0.0` drops everything; `rate=1.0` keeps everything. Both are allowed.
- `bool` is explicitly rejected for `rate` even though it is an `int` subclass
  in Python, because `True`/`False` almost always indicates a misuse rather
  than an intended `1.0`/`0.0`.
- `NaN` and infinities are rejected for `rate`.
- `trace_id` must be a non-empty `str`. Bytes and numbers are rejected to
  avoid silently hashing a different representation than the caller expected.
- The internal hash is blake2b over the UTF-8 bytes of `trace_id`, and the
  decision threshold is the first 8 bytes interpreted as a big-endian unsigned
  64-bit integer divided by `2**64`, giving a value in `[0.0, 1.0)`. A trace is
  kept when `threshold < rate`.
