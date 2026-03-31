# U-Net architecture placeholder
import segmentation_models_pytorch as smp
import torch
import torch.nn as nn
import yaml

def load_config(config_path="configs/config.yaml"):
    with open(config_path) as f:
        return yaml.safe_load(f)

class damagesegmentationmodel(nn.Module):
    def __init__(self,config):
        super(damagesegmentationmodel,self).__init__()

        #creating a unet model 
        self.model=smp.Unet(
            encoder_name=config["encoder_name"],
            encoder_weights=config.get("encoder_weights","imagenet"),
            in_channels=22,
            classes=4,
            activation=None            
        )
    def forward(self,x):
        return self.model(x)  
def get_model(config):
    return damagesegmentationmodel(config)

def load_trained_model(checkpoint_path, config, device="cpu"):
    model = get_model(config)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.to(device)
    model.eval()
    return model      

# 130. TEST
if __name__ == "__main__":
    config = {
        "encoder_name": "resnet34",
        "encoder_weights": "imagenet"
    }

    model = get_model(config)

    # Random input tensor
    x = torch.randn(2, 22, 256, 256)

    # Forward pass
    output = model(x)

    print("Output shape:", output.shape)