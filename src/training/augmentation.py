# Data augmentation for satellite imagery training
import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np

def get_training_transforms(tile_size=256):
    """
    Get augmentation pipeline for training data.
    
    Includes spatial and pixel augmentations suitable for satellite imagery.
    """
    return A.Compose([
        # Spatial augmentations - applied to both image and mask
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        
        # Small geometric transformations
        A.ShiftScaleRotate(
            shift_limit=0.05, 
            scale_limit=0.1, 
            rotate_limit=15, 
            p=0.4
        ),
        
        # Pixel augmentations - applied only to image
        A.RandomBrightnessContrast(
            brightness_limit=0.2, 
            contrast_limit=0.2, 
            p=0.4
        ),
        
        # Noise augmentation
        A.GaussNoise(var_limit=(10, 50), p=0.3),
        
        # Coarse dropout for missing data simulation
        A.CoarseDropout(
            max_holes=8, 
            max_height=32, 
            max_width=32, 
            fill_value=0, 
            p=0.3
        ),
        
        # Convert to tensor
        ToTensorV2()
    ])

def get_validation_transforms():
    """
    Get transforms for validation/test data - no augmentation, just tensor conversion.
    """
    return A.Compose([
        ToTensorV2()
    ])

def apply_sar_specific_augmentation(sar_array):
    """
    Apply SAR-specific multiplicative noise (speckle noise).
    
    SAR noise is multiplicative, unlike additive Gaussian noise.
    """
    # Speckle noise: multiplicative noise
    noise_level = 0.1  # Typical speckle noise level
    noise = np.random.normal(0, noise_level, sar_array.shape)
    
    # Apply multiplicative noise
    noisy_sar = sar_array * (1 + noise)
    
    # Ensure non-negative values (SAR backscatter is always positive)
    noisy_sar = np.maximum(noisy_sar, 0)
    
    return noisy_sar

# TEST
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Create a dummy satellite tile (simulating RGB image)
    dummy_tile = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    dummy_mask = np.random.randint(0, 4, (256, 256), dtype=np.uint8)
    
    transforms = get_training_transforms()
    
    # Apply transforms 10 times
    augmented_images = []
    augmented_masks = []
    
    for i in range(10):
        augmented = transforms(image=dummy_tile, mask=dummy_mask)
        augmented_images.append(augmented['image'].numpy().transpose(1, 2, 0))
        augmented_masks.append(augmented['mask'])
    
    # Plot results
    fig, axes = plt.subplots(2, 5, figsize=(15, 6))
    for i in range(10):
        row = i // 5
        col = i % 5
        axes[row, col].imshow(augmented_images[i].astype(np.uint8))
        axes[row, col].set_title(f'Aug {i+1}')
        axes[row, col].axis('off')
    
    plt.tight_layout()
    plt.savefig('augmentation_test.png')
    plt.show()
    
    print("Augmentation test completed. Check augmentation_test.png for results.")
