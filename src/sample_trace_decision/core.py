from __future__ import annotations

import hashlib
import struct
from typing import Optional


class TraceDecisionSampler:
    """Deterministic per-trace keep/drop sampler.

    Given a trace_id, the decision to keep or drop is stable: the same trace_id
    always yields the same decision for a given rate. This is useful when
    multiple services participate in a trace and must agree on whether to
    record it without coordinating with each other.

    The trace_id is hashed with blake2b and reduced to a uniform float in
    [0, 1) via the first 8 bytes interpreted as a big-endian unsigned 64-bit
    integer divided by 2**64. Blake2b is chosen because it is fast, available
    in the standard library, and produces a well-distributed digest whose
    high bits behave uniformly for our purposes.
    """

    def __init__(self, rate: float):
        """Initialize the sampler.

        Args:
            rate: Fraction of traces to keep, in [0.0, 1.0].
                0.0 keeps none, 1.0 keeps all.

        Raises:
            TypeError: If rate is not a float or int.
            ValueError: If rate is outside [0.0, 1.0].
        """
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise TypeError("rate must be a real number (int or float), got %r" % (type(rate).__name__,))
        if isinstance(rate, float):
            if rate != rate or rate in (float("inf"), float("-inf")):
                raise ValueError("rate must be a finite number, got %r" % (rate,))
        if rate < 0.0 or rate > 1.0:
            raise ValueError("rate must be within [0.0, 1.0], got %r" % (rate,))
        self._rate = float(rate)

    @property
    def rate(self) -> float:
        """Return the configured sampling rate in [0.0, 1.0]."""
        return self._rate

    def _threshold(self, trace_id: str) -> float:
        """Compute the sampling threshold in [0.0, 1.0) for a trace_id.

        We hash with blake2b (64-byte digest) and read the first 8 bytes as a
        big-endian unsigned 64-bit integer. Dividing by 2**64 maps that integer
        into [0.0, 1.0). Using the leading bytes rather than the trailing ones
        avoids any subtle bias from the digest tail in short digests; for
        blake2b-512 either end is fine, but leading bytes keep the convention
        stable if the digest size is ever reduced.
        """
        digest = hashlib.blake2b(trace_id.encode("utf-8")).digest()
        value = struct.unpack(">Q", digest[:8])[0]
        return value / (2**64)

    def should_keep(self, trace_id: str) -> bool:
        """Decide whether to keep the trace with the given trace_id.

        Args:
            trace_id: A non-empty string identifying the trace.

        Returns:
            True if the trace should be kept, False if it should be dropped.

        Raises:
            TypeError: If trace_id is not a str.
            ValueError: If trace_id is empty.
        """
        if not isinstance(trace_id, str):
            raise TypeError("trace_id must be a str, got %r" % (type(trace_id).__name__,))
        if not trace_id:
            raise ValueError("trace_id must not be empty")
        return self._threshold(trace_id) < self._rate
