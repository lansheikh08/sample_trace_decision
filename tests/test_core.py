import math
import unittest

from sample_trace_decision import TraceDecisionSampler


class TestConstruction(unittest.TestCase):
    def test_default_rate_attribute(self):
        sampler = TraceDecisionSampler(0.5)
        self.assertEqual(sampler.rate, 0.5)

    def test_int_rate_accepted(self):
        sampler = TraceDecisionSampler(1)
        self.assertEqual(sampler.rate, 1.0)
        self.assertIsInstance(sampler.rate, float)

    def test_zero_rate_accepted(self):
        sampler = TraceDecisionSampler(0.0)
        self.assertEqual(sampler.rate, 0.0)

    def test_rate_clamped_to_unit_interval(self):
        with self.assertRaises(ValueError):
            TraceDecisionSampler(-0.01)
        with self.assertRaises(ValueError):
            TraceDecisionSampler(1.01)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            TraceDecisionSampler(float("nan"))

    def test_inf_rejected(self):
        with self.assertRaises(ValueError):
            TraceDecisionSampler(float("inf"))
        with self.assertRaises(ValueError):
            TraceDecisionSampler(float("-inf"))

    def test_bool_rejected(self):
        # bool is a subclass of int but is almost certainly a misuse here.
        with self.assertRaises(TypeError):
            TraceDecisionSampler(True)
        with self.assertRaises(TypeError):
            TraceDecisionSampler(False)

    def test_non_number_rejected(self):
        with self.assertRaises(TypeError):
            TraceDecisionSampler("0.5")
        with self.assertRaises(TypeError):
            TraceDecisionSampler(None)


class TestShouldKeep(unittest.TestCase):
    def test_rate_zero_drops_all(self):
        sampler = TraceDecisionSampler(0.0)
        self.assertFalse(sampler.should_keep("abc123"))
        self.assertFalse(sampler.should_keep("0000000000000000"))
        self.assertFalse(sampler.should_keep("deadbeef"))

    def test_rate_one_keeps_all(self):
        sampler = TraceDecisionSampler(1.0)
        self.assertTrue(sampler.should_keep("abc123"))
        self.assertTrue(sampler.should_keep("0000000000000000"))
        self.assertTrue(sampler.should_keep("deadbeef"))

    def test_decision_is_deterministic(self):
        sampler = TraceDecisionSampler(0.3)
        # Same trace_id, many calls, same answer.
        decisions = [sampler.should_keep("trace-xyz-123") for _ in range(5)]
        self.assertEqual(len(set(decisions)), 1)

    def test_decision_stable_across_sampler_instances(self):
        # Two samplers with the same rate agree on every trace_id.
        a = TraceDecisionSampler(0.25)
        b = TraceDecisionSampler(0.25)
        ids = ["%016x" % i for i in range(100)]
        for tid in ids:
            self.assertEqual(a.should_keep(tid), b.should_keep(tid))

    def test_monotonicity_higher_rate_never_drops_more(self):
        # A strictly higher rate can never turn a keep into a drop for the
        # same trace_id. We compare rate=0.0 to a range of higher rates.
        ids = ["%016x" % i for i in range(200)]
        low = TraceDecisionSampler(0.1)
        high = TraceDecisionSampler(0.9)
        for tid in ids:
            if low.should_keep(tid):
                self.assertTrue(high.should_keep(tid), "higher rate dropped a kept trace")

    def test_effective_rate_close_to_configured(self):
        # With 4000 trace_ids, the fraction kept should be within a generous
        # band of the configured rate. We do not assert exact equality.
        rate = 0.25
        sampler = TraceDecisionSampler(rate)
        ids = ["trace-%04d" % i for i in range(4000)]
        kept = sum(1 for tid in ids if sampler.should_keep(tid))
        fraction = kept / len(ids)
        self.assertLess(abs(fraction - rate), 0.05)

    def test_empty_trace_id_rejected(self):
        sampler = TraceDecisionSampler(0.5)
        with self.assertRaises(ValueError):
            sampler.should_keep("")

    def test_non_string_trace_id_rejected(self):
        sampler = TraceDecisionSampler(0.5)
        with self.assertRaises(TypeError):
            sampler.should_keep(123)
        with self.assertRaises(TypeError):
            sampler.should_keep(None)
        with self.assertRaises(TypeError):
            sampler.should_keep(b"abc123")


class TestThresholdInternals(unittest.TestCase):
    def test_threshold_in_unit_interval(self):
        sampler = TraceDecisionSampler(0.5)
        for i in range(200):
            t = sampler._threshold("trace-%03d" % i)
            self.assertGreaterEqual(t, 0.0)
            self.assertLess(t, 1.0)

    def test_threshold_is_float(self):
        sampler = TraceDecisionSampler(0.5)
        t = sampler._threshold("abc")
        self.assertIsInstance(t, float)


if __name__ == "__main__":
    unittest.main()
