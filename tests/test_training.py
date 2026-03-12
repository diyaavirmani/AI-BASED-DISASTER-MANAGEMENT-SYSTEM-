import pytest
from src.training.train_zone import train_zone_predictor


def test_train_zone_predictor_defaults():
    model_path, metrics = train_zone_predictor()
    assert isinstance(model_path, str)
    assert isinstance(metrics, dict)
    assert "val_loss" in metrics
    assert "val_acc" in metrics


def test_train_zone_predictor_with_epochs():
    model_path, metrics = train_zone_predictor(epochs=50)
    assert model_path is not None
    assert metrics is not None


def test_train_zone_predictor_with_sequence_length():
    model_path, metrics = train_zone_predictor(sequence_length=15)
    assert model_path is not None
    assert metrics is not None


def test_train_zone_predictor_full_params():
    test_data = [[1, 2, 3], [4, 5, 6]]
    val_data = [[7, 8, 9]]
    model_path, metrics = train_zone_predictor(
        train_data=test_data,
        val_data=val_data,
        epochs=5,
        sequence_length=8
    )
    assert model_path is not None
    assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__])
