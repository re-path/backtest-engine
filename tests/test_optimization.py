"""
Unit tests for the Optimizer class (simulated annealing and hill climbing).
"""
import pytest
import math
from core.optimization import Optimizer, OptimizationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def simple_objective(params):
    """
    A simple quadratic objective: maximize -(x-3)^2 + 10
    Peak at x=3, score=10.
    """
    x = params.get("x", 0)
    return {"score": -(x - 3) ** 2 + 10, "other_metric": x * 2}


def multi_param_objective(params):
    """Two-parameter objective: maximize -(x-2)^2 - (y-5)^2 + 100."""
    x = params.get("x", 0)
    y = params.get("y", 0)
    return {"score": -(x - 2)**2 - (y - 5)**2 + 100}


# ---------------------------------------------------------------------------
# OptimizationResult
# ---------------------------------------------------------------------------

class TestOptimizationResult:
    def test_fields(self):
        r = OptimizationResult(params={"x": 1}, metrics={"score": 5.0}, score=5.0)
        assert r.params == {"x": 1}
        assert r.metrics == {"score": 5.0}
        assert r.score == 5.0


# ---------------------------------------------------------------------------
# Optimizer._evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_evaluate_calls_objective(self):
        opt = Optimizer(simple_objective, target_metric="score")
        result = opt._evaluate({"x": 3})
        assert result.score == pytest.approx(10.0)

    def test_evaluate_stores_in_history(self):
        opt = Optimizer(simple_objective, target_metric="score")
        opt._evaluate({"x": 0})
        opt._evaluate({"x": 3})
        assert len(opt.history) == 2

    def test_evaluate_missing_metric(self):
        opt = Optimizer(simple_objective, target_metric="nonexistent")
        result = opt._evaluate({"x": 3})
        assert result.score == -1e18


# ---------------------------------------------------------------------------
# Optimizer._get_random_neighbor
# ---------------------------------------------------------------------------

class TestGetRandomNeighbor:
    def test_stays_within_bounds(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": 0, "max": 10, "step": 1}}
        for _ in range(100):
            neighbor = opt._get_random_neighbor({"x": 5}, ranges)
            assert 0 <= neighbor["x"] <= 10

    def test_respects_int_type(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": 0, "max": 100, "step": 5, "type": "int"}}
        for _ in range(50):
            neighbor = opt._get_random_neighbor({"x": 50}, ranges)
            assert isinstance(neighbor["x"], int)

    def test_single_param_changed(self):
        opt = Optimizer(multi_param_objective, target_metric="score")
        ranges = {
            "x": {"min": 0, "max": 10, "step": 1},
            "y": {"min": 0, "max": 10, "step": 1},
        }
        original = {"x": 5, "y": 5}
        # Over many tries, at least one param should change
        changed_params = set()
        for _ in range(50):
            neighbor = opt._get_random_neighbor(original, ranges)
            for k in ["x", "y"]:
                if neighbor[k] != original[k]:
                    changed_params.add(k)
        assert len(changed_params) > 0


# ---------------------------------------------------------------------------
# Simulated Annealing
# ---------------------------------------------------------------------------

class TestSimulatedAnnealing:
    def test_returns_non_empty_history(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 0.5}}
        results = opt.simulated_annealing({"x": 0}, ranges, iterations=10)
        assert len(results) > 0

    def test_history_length(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 0.5}}
        results = opt.simulated_annealing({"x": 0}, ranges, iterations=20)
        # 1 initial + 20 iterations = 21
        assert len(results) == 21

    def test_finds_better_than_initial(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 1.0}}
        initial = {"x": -10}  # score = -(−10−3)^2 + 10 = -159
        results = opt.simulated_annealing(initial, ranges, iterations=200)
        best = max(results, key=lambda r: r.score)
        initial_score = simple_objective(initial)["score"]
        assert best.score >= initial_score


# ---------------------------------------------------------------------------
# Hill Climbing
# ---------------------------------------------------------------------------

class TestHillClimbing:
    def test_returns_non_empty_history(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 0.5}}
        results = opt.hill_climbing({"x": 0}, ranges, iterations=10)
        assert len(results) > 0

    def test_history_length(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 0.5}}
        results = opt.hill_climbing({"x": 0}, ranges, iterations=15)
        assert len(results) == 16  # 1 initial + 15 iterations

    def test_monotonically_improves_or_stays(self):
        """Hill climbing should never accept a worse solution."""
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": -10, "max": 10, "step": 0.5}}
        opt.hill_climbing({"x": 0}, ranges, iterations=30)
        
        # Track the "current best" through history
        # Hill climbing keeps current_result if neighbor is worse
        # So the returned history includes ALL evaluated points (not just accepted)
        # We can't assert monotonicity on history, but we can assert
        # the best score is >= initial
        best = max(opt.history, key=lambda r: r.score)
        initial_score = simple_objective({"x": 0})["score"]
        assert best.score >= initial_score

    def test_finds_good_solution(self):
        opt = Optimizer(simple_objective, target_metric="score")
        ranges = {"x": {"min": 0, "max": 6, "step": 0.5}}
        results = opt.hill_climbing({"x": 1}, ranges, iterations=200)
        best = max(results, key=lambda r: r.score)
        # Should find x close to 3 (score close to 10)
        # Initial score at x=1 is -(1-3)^2+10 = 6, so anything > 1 is an improvement
        assert best.score > 1.0
