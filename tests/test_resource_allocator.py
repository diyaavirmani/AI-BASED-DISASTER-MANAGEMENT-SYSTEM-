import pytest
from src.models.resource_allocator import allocate_resources


def test_allocate_resources_empty_zones():
    result = allocate_resources([])
    assert result == []


def test_allocate_resources_single_zone():
    zones = [{"zone_id": "A", "severity": 8, "lat": 12.5, "lon": 34.2}]
    result = allocate_resources(zones)
    assert len(result) == 1
    assert result[0]["zone_id"] == "A"


def test_allocate_resources_multiple_zones():
    zones = [
        {"zone_id": "A", "severity": 9, "lat": 12.5, "lon": 34.2},
        {"zone_id": "B", "severity": 5, "lat": 14.1, "lon": 35.8},
        {"zone_id": "C", "severity": 7, "lat": 13.0, "lon": 33.5},
    ]
    result = allocate_resources(zones)
    assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__])
