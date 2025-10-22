from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Task:
    id: str
    name: str
    stage: str
    depends_on: List[str]
    min_days: float
    max_days: float
    fixed_days: Optional[float] = None
    resource: str = ""
    supplier: str = ""
    duration: float = 0.0
    es: float = 0.0
    ef: float = 0.0
    ls: float = 0.0
    lf: float = 0.0
    slack: float = 0.0
    def set_duration(self, rng):
        if self.fixed_days and self.fixed_days > 0:
            self.duration = float(self.fixed_days)
        else:
            low = max(0.0, float(self.min_days))
            high = max(low, float(self.max_days))
            self.duration = round(low + (high - low) * rng.random(), 2)
