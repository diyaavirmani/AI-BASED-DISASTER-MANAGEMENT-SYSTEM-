"""
Creates the PyTorch Dataset object that the
model training script will use. Stacks all image
bands and indices into tensors, loads labels, and
applies augmentations
    
    
    """

import logging
import torch
import os 
import numpy as np
from torch.utils.data import Dataset, DataLoader
import albumentations as A
from albumentations.pytorch import ToTensorV2
from src.training.augmentation import get_training_transforms, get_validation_transforms

class DisasterDataset(Dataset):
    def __init__(self, file_pairs, augment=False, config=None):
        self.file_pairs = file_pairs
        self.augment = augment
        self.config = config
        if augment:
            self.transform = get_training_transforms()
        else:
            self.transform = get_validation_transforms()
    
    def __len__(self):
        return len(self.file_pairs)
    
    def __getitem__(self, idx):
        image_path, label_path = self.file_pairs[idx]
        # load image 
        image = np.load(image_path)
        # load mask
        mask = np.load(label_path)
        
        # Apply transforms (includes augmentation if training, and tensor conversion)
        transformed = self.transform(image=image, mask=mask)
        image = transformed["image"]
        mask = transformed["mask"]
        
        return image, mask

def build_dataloaders(config):
    image_dir = config["data"]["image_dir"]
    label_dir = config["data"]["label_dir"]
    batch_size = config["training"]["batch_size"]
    subset_size = config["data"].get("subset_size")
    
    file_pairs = []
    
    for name in os.listdir(image_dir):
        img_path = os.path.join(image_dir, name)
        label_path = os.path.join(label_dir, name)
        
        if os.path.exists(img_path) and os.path.exists(label_path):
            file_pairs.append((img_path, label_path))
    
    if subset_size:
        file_pairs = file_pairs[:subset_size]
    
    train_pairs = []
    val_pairs = []
    
    for img, lbl in file_pairs:
        if "train" in img:
            train_pairs.append((img, lbl))
        elif "val" in img:
            val_pairs.append((img, lbl))
    
    train_dataset = DisasterDataset(train_pairs, augment=True, config=config)
    val_dataset = DisasterDataset(val_pairs, augment=False, config=config)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
    )
    
    return train_loader, val_loader

config = {
    "image_dir": "./data/images",
    "label_dir": "./data/labels",
    "batch_size": 16
}

train_loader, val_loader, test_loader = DisasterDataset.build_dataloaders(config)

dataset = train_loader.dataset
img, mask = dataset[0]

print(img.shape)
print(mask.shape)
