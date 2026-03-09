#!/usr/bin/env python3
"""Sample Python module for testing AutoDoc."""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class UserProfile:
    """User profile data structure."""
    user_id: str
    username: str
    email: str
    is_active: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataProcessor:
    """Processes and transforms data records."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._cache = {}
    
    def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single data record."""
        record_id = record.get('id')
        if record_id in self._cache:
            return self._cache[record_id]
        
        processed = self._transform(record)
        self._cache[record_id] = processed
        return processed
    
    def _transform(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Internal transformation logic."""
        return {k: v for k, v in record.items() if v is not None}
    
    def batch_process(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple records in batch."""
        return [self.process_record(r) for r in records]


def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def calculate_stats(values: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for a list of values."""
    if not values:
        return {'mean': 0.0, 'median': 0.0, 'std': 0.0}
    
    n = len(values)
    mean = sum(values) / n
    sorted_vals = sorted(values)
    median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    
    return {'mean': mean, 'median': median, 'std': std}


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as pretty-printed JSON."""
    return json.dumps(data, indent=indent, default=str)
