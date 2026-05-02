# LSTM-based zone risk predictor
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import Dataset
import pandas as pd
from datetime import datetime, timedelta

class ZonePredictorLSTM(nn.Module):
    def __init__(self, config):
        super(ZonePredictorLSTM, self).__init__()
        
        input_size = config.get("zone_input_size", 8)  # Number of features per timestep
        hidden_size = config.get("zone_hidden_size", 256)
        num_layers = config.get("zone_num_layers", 2)
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3
        )
        
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Take the last time step's output
        last_output = lstm_out[:, -1, :]  # (batch_size, hidden_size)
        
        # Pass through linear layer and sigmoid
        risk_score = self.sigmoid(self.fc(last_output))  # (batch_size, 1)
        
        return risk_score

class ZoneDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = sequences  # List of (seq_len, num_features) arrays
        self.labels = labels  # List of risk labels (0.0 or 1.0)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = torch.tensor(self.sequences[idx], dtype=torch.float32)
        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return sequence, label

def prepare_zone_features(zone_id, end_date, lookback_days=30):
    """
    Assemble feature matrix for a specific geographic zone.
    
    Features: daily_max_temp, daily_rainfall_mm, daily_wind_speed, 
    seismic_count_24h, max_seismic_magnitude, historical_disaster_count,
    elevation_mean, slope_mean
    
    Returns: numpy array of shape (lookback_days, 8)
    """
    # Placeholder implementation - in real system, fetch from APIs/databases
    features = []
    
    for i in range(lookback_days):
        date = end_date - timedelta(days=lookback_days - 1 - i)
        
        # Synthetic data for demonstration
        daily_max_temp = 25 + 5 * np.sin(2 * np.pi * date.timetuple().tm_yday / 365) + np.random.normal(0, 2)
        daily_rainfall_mm = max(0, np.random.exponential(2))
        daily_wind_speed = np.random.gamma(2, 2)
        seismic_count_24h = np.random.poisson(0.1)
        max_seismic_magnitude = 0 if seismic_count_24h == 0 else np.random.uniform(2, 5)
        historical_disaster_count = np.random.poisson(0.05)
        elevation_mean = 500 + np.random.normal(0, 50)
        slope_mean = np.random.uniform(0, 30)
        
        features.append([
            daily_max_temp, daily_rainfall_mm, daily_wind_speed,
            seismic_count_24h, max_seismic_magnitude, historical_disaster_count,
            elevation_mean, slope_mean
        ])
    
    return np.array(features)

def predict_risk_map(model, zones_list, current_date):
    """
    Predict risk scores for all geographic zones.
    
    Returns: dict mapping zone_id to risk_score
    """
    model.eval()
    risk_map = {}
    
    with torch.no_grad():
        for zone_id in zones_list:
            # Prepare features for this zone
            features = prepare_zone_features(zone_id, current_date, lookback_days=30)
            features = torch.tensor(features, dtype=torch.float32).unsqueeze(0)  # Add batch dimension
            
            # Predict risk
            risk_score = model(features).item()
            risk_map[zone_id] = risk_score
    
    return risk_map

# TEST
if __name__ == "__main__":
    # Test with synthetic data
    config = {
        "zone_input_size": 8,
        "zone_hidden_size": 256,
        "zone_num_layers": 2
    }
    
    model = ZonePredictorLSTM(config)
    
    # Create synthetic time series with high risk pattern
    # High wind + high rainfall + high seismic activity
    high_risk_sequence = []
    for i in range(30):
        if i > 20:  # Last 10 days show risk pattern
            features = [30, 20, 15, 5, 4.5, 2, 600, 25]  # High values
        else:
            features = [20, 2, 5, 0, 0, 0, 500, 10]  # Normal values
        high_risk_sequence.append(features)
    
    high_risk_sequence = torch.tensor(high_risk_sequence, dtype=torch.float32).unsqueeze(0)
    
    # Forward pass
    risk_score = model(high_risk_sequence)
    print(f"Predicted risk score for high-risk pattern: {risk_score.item():.4f}")
    
    # Test with normal pattern
    normal_sequence = torch.tensor([[20, 2, 5, 0, 0, 0, 500, 10]] * 30, dtype=torch.float32).unsqueeze(0)
    normal_risk = model(normal_sequence)
    print(f"Predicted risk score for normal pattern: {normal_risk.item():.4f}")
    
    # Test predict_risk_map
    zones_list = ["zone_1", "zone_2", "zone_3"]
    current_date = datetime.now()
    risk_map = predict_risk_map(model, zones_list, current_date)
    print("Risk map:", risk_map)
    model : Optional[object]
        Trained LSTM model instance.

    Returns
    -------
    List[dict]
        List of predicted zones with confidence scores.
    """
    logger.info("Predicting disaster zones from time-series data")
    return []
