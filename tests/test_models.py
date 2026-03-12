import pytest
from src.models.zone_predictor import predict_zones
from src.models.hrnet import build_hrnet, forward_hrnet
import numpy as np


def test_predict_zones_empty():
    result = predict_zones(np.array([]))
    assert result == []


def test_predict_zones_with_data():
    time_series = np.random.rand(10, 5)
    result = predict_zones(time_series)
    assert isinstance(result, list)


def test_build_hrnet():
    build_hrnet(num_channels=13, num_classes=2)
    assert True


def test_forward_hrnet():
    x = np.random.rand(2, 3, 512, 512)
    result = forward_hrnet(x)
    assert result.shape == (2, 3, 512, 512)


if __name__ == "__main__":
    pytest.main([__file__])
