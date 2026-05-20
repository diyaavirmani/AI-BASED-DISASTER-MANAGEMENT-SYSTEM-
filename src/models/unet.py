# U-Net architecture placeholder
import segmentation_models_pytorch as smp
import torch
import torch.nn as nn
import yaml

def load_config(config_path="configs/config.yaml"):
    with open(config_path) as f:
        return yaml.safe_load(f)

class DamageSegmentationModel(nn.Module):
    def __init__(self, config):
        super(DamageSegmentationModel, self).__init__()

        # Try to resolve in_channels dynamically from config
        if "model" in config:
            in_channels = config["model"].get("in_channels", 9)
            encoder_name = config["model"].get("encoder_name", "resnet50")
            encoder_weights = config["model"].get("encoder_weights", "imagenet")
        else:
            in_channels = config.get("in_channels", 9)
            encoder_name = config.get("encoder_name", "resnet50")
            encoder_weights = config.get("encoder_weights", "imagenet")

        # Creating U-Net model
        self.model = smp.Unet(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=4,
            activation=None            
        )

    def forward(self, x):
        return self.model(x)  

def get_model(config):
    return DamageSegmentationModel(config)

def load_trained_model(checkpoint_path, config, device="cpu"):
    model = get_model(config)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.to(device)
    model.eval()
    return model      

# TEST
if __name__ == "__main__":
    config = {
        "model": {
            "encoder_name": "resnet34",
            "encoder_weights": "imagenet",
            "in_channels": 9
        }
    }

    model = get_model(config)

    # Random input tensor (batch, channels, height, width)
    x = torch.randn(2, 9, 256, 256)

    # Forward pass
    output = model(x)

    print("Output shape:", output.shape)