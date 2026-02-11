import random
import math
import copy
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass

@dataclass
class OptimizationResult:
    params: Dict[str, Any]
    metrics: Dict[str, float]
    score: float

class Optimizer:
    def __init__(self, objective_function: Callable[[Dict[str, Any]], Dict[str, float]], target_metric: str = "total_net_profit"):
        """
        :param objective_function: Function that takes params and returns metrics dict
        :param target_metric: The metric key to maximize
        """
        self.objective_function = objective_function
        self.target_metric = target_metric
        self.history: List[OptimizationResult] = []

    def _evaluate(self, params: Dict[str, Any]) -> OptimizationResult:
        metrics = self.objective_function(params)
        score = metrics.get(self.target_metric, -1e18) # Use large negative number instead of -inf for JSON compatibility
        result = OptimizationResult(params=copy.deepcopy(params), metrics=metrics, score=score)
        self.history.append(result)
        return result

    def _get_random_neighbor(self, current_params: Dict[str, Any], ranges: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate a neighbor by perturbing one parameter."""
        neighbor = copy.deepcopy(current_params)
        
        # Pick one parameter to change
        param_to_change = random.choice(list(ranges.keys()))
        config = ranges[param_to_change]
        
        current_val = neighbor[param_to_change]
        step = config.get('step', (config['max'] - config['min']) / 20.0)
        
        # Perturb
        if isinstance(current_val, int) or config.get('type') == 'int':
            delta = random.randint(-int(step), int(step))
            new_val = current_val + delta
        else:
            delta = random.uniform(-step, step)
            new_val = current_val + delta
            
        # Clip to bounds
        new_val = max(config['min'], min(config['max'], new_val))
        
        if config.get('type') == 'int':
            new_val = int(round(new_val))
            
        neighbor[param_to_change] = new_val
        return neighbor

    def simulated_annealing(self, initial_params: Dict[str, Any], ranges: Dict[str, Dict[str, float]], iterations: int = 100, initial_temp: float = 100.0) -> List[OptimizationResult]:
        current_params = initial_params
        current_result = self._evaluate(current_params)
        best_result = current_result
        
        temp = initial_temp
        # Cooling rate
        alpha = 0.95
        
        for i in range(iterations):
            neighbor_params = self._get_random_neighbor(current_params, ranges)
            neighbor_result = self._evaluate(neighbor_params)
            
            # Acceptance probability
            if neighbor_result.score > current_result.score:
                current_params = neighbor_params
                current_result = neighbor_result
                if neighbor_result.score > best_result.score:
                    best_result = neighbor_result
            else:
                prob = math.exp((neighbor_result.score - current_result.score) / max(temp, 1e-9))
                if random.random() < prob:
                    current_params = neighbor_params
                    current_result = neighbor_result
            
            temp *= alpha
            
        return self.history

    def hill_climbing(self, initial_params: Dict[str, Any], ranges: Dict[str, Dict[str, float]], iterations: int = 100) -> List[OptimizationResult]:
        current_params = initial_params
        current_result = self._evaluate(current_params)
        best_result = current_result
        
        for i in range(iterations):
            neighbor_params = self._get_random_neighbor(current_params, ranges)
            neighbor_result = self._evaluate(neighbor_params)
            
            if neighbor_result.score > current_result.score:
                current_params = neighbor_params
                current_result = neighbor_result
                if neighbor_result.score > best_result.score:
                    best_result = neighbor_result
            
        return self.history
