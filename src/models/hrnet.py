# HRNet architecture for damage segmentation
import segmentation_models_pytorch as smp
import torch
import torch.nn as nn

class HRNetSegmentationModel(nn.Module):
    def __init__(self, config):
        super(HRNetSegmentationModel, self).__init__()

        # Try to resolve parameters dynamically from config
        if "model" in config:
            in_channels = config["model"].get("in_channels", 9)
            hrnet_width = config["model"].get("hrnet_width", 32)
            encoder_weights = config["model"].get("encoder_weights", "imagenet")
        else:
            in_channels = config.get("in_channels", 9)
            hrnet_width = config.get("hrnet_width", 32)
            encoder_weights = config.get("encoder_weights", "imagenet")

        encoder_name = f"tu-hrnet_w{hrnet_width}"

        # Creating an HRNet model using SMP
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
    return HRNetSegmentationModel(config)

def load_trained_model(checkpoint_path, config, device="cpu"):
    model = get_model(config)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.to(device)
    model.eval()
    return model

def compare_models(config):
    # Instantiate U-Net
    unet_model = smp.Unet(
        encoder_name="resnet50",
        encoder_weights="imagenet",
        in_channels=9,
        classes=4,
        activation=None
    )

    # Instantiate HRNet
    hrnet_width = config.get("model", config).get("hrnet_width", 32)
    encoder_name = f"tu-hrnet_w{hrnet_width}"
    hrnet_model = smp.Unet(
        encoder_name=encoder_name,
        encoder_weights="imagenet",
        in_channels=9,
        classes=4,
        activation=None
    )

    # Dummy input
    x = torch.randn(2, 9, 256, 256)

    # Forward pass
    with torch.no_grad():
        unet_output = unet_model(x)
        hrnet_output = hrnet_model(x)

    # Count parameters
    unet_params = sum(p.numel() for p in unet_model.parameters())
    hrnet_params = sum(p.numel() for p in hrnet_model.parameters())

    print(f"U-Net parameters: {unet_params}")
    print(f"HRNet parameters: {hrnet_params}")
    print(f"U-Net output shape: {unet_output.shape}")
    print(f"HRNet output shape: {hrnet_output.shape}")

# TEST
if __name__ == "__main__":
    config = {
        "model": {
            "hrnet_width": 32,
            "encoder_weights": "imagenet",
            "in_channels": 9
        }
    }
    compare_models(config)
