# Evaluation script for trained models
import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import yaml

from src.data_pipeline.dataset_builder import build_dataloaders
from src.models.unet import load_trained_model
from src.training.metrics import compute_all_metrics

def run_inference_on_test_set(model, test_loader, device):
    """
    Run inference on the test set and collect all predictions and labels.
    """
    model.eval()
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for images, masks in test_loader:
            images = images.to(device)
            masks = masks.to(device)
            
            outputs = model(images)
            preds = torch.argmax(outputs, dim=1)
            
            all_predictions.append(preds.cpu())
            all_labels.append(masks.cpu())
    
    all_predictions = torch.cat(all_predictions).numpy().flatten()
    all_labels = torch.cat(all_labels).numpy().flatten()
    
    return all_predictions, all_labels

def compute_full_report(predictions, labels, class_names):
    """
    Compute comprehensive evaluation metrics.
    """
    # Basic metrics
    metrics = compute_all_metrics(predictions, labels, num_classes=len(class_names))
    
    # Confusion matrix
    cm = confusion_matrix(labels, predictions, labels=range(len(class_names)))
    
    # Per-class breakdown
    per_class_iou = metrics["iou"]
    
    # Placeholder for per-disaster and per-region (would need metadata)
    per_disaster = {"earthquake": per_class_iou, "flood": per_class_iou}  # Placeholder
    per_region = {"asia": per_class_iou, "america": per_class_iou}  # Placeholder
    
    return {
        "metrics": metrics,
        "confusion_matrix": cm,
        "per_class_iou": per_class_iou,
        "per_disaster": per_disaster,
        "per_region": per_region
    }

def visualise_predictions(model, test_dataset, num_samples=10, save_dir="docs/figures"):
    """
    Create visualisation plots of model predictions.
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Color scheme: 0=no damage (green), 1=minor (yellow), 2=major (orange), 3=destroyed (red)
    colors = ['green', 'yellow', 'orange', 'red']
    
    indices = np.random.choice(len(test_dataset), num_samples, replace=False)
    
    fig, axes = plt.subplots(num_samples, 3, figsize=(12, 4*num_samples))
    
    model.eval()
    device = next(model.parameters()).device
    
    for i, idx in enumerate(indices):
        image, true_mask = test_dataset[idx]
        
        # Run prediction
        with torch.no_grad():
            pred_mask = model(image.unsqueeze(0).to(device))
            pred_mask = torch.argmax(pred_mask, dim=1).squeeze().cpu().numpy()
        
        image = image.permute(1, 2, 0).numpy()
        # Normalize image for display
        image = (image - image.min()) / (image.max() - image.min())
        
        # Plot
        axes[i, 0].imshow(image)
        axes[i, 0].set_title("Satellite Image")
        axes[i, 0].axis('off')
        
        axes[i, 1].imshow(true_mask, cmap='viridis', vmin=0, vmax=3)
        axes[i, 1].set_title("True Damage Mask")
        axes[i, 1].axis('off')
        
        axes[i, 2].imshow(pred_mask, cmap='viridis', vmin=0, vmax=3)
        axes[i, 2].set_title("Predicted Damage Mask")
        axes[i, 2].axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "prediction_visualisations.png"))
    plt.close()

def save_evaluation_report(metrics_dict, save_path="docs/evaluation_report.md"):
    """
    Save comprehensive evaluation report as Markdown.
    """
    with open(save_path, "w") as f:
        f.write("# Model Evaluation Report\n\n")
        
        f.write("## Model Information\n")
        f.write("- Model: Damage Segmentation U-Net\n")
        f.write("- Checkpoint: [path]\n\n")
        
        f.write("## Test Set Summary\n")
        f.write("- Total samples: [count]\n")
        f.write("- Classes: No Damage, Minor Damage, Major Damage, Destroyed\n\n")
        
        f.write("## Overall Metrics\n")
        metrics = metrics_dict["metrics"]
        f.write(f"- Mean IoU: {metrics['iou']['mean_iou']:.4f}\n")
        f.write(f"- Pixel Accuracy: {metrics['accuracy']:.4f}\n")
        f.write(f"- Macro F1: {metrics['f1']['macro_f1']:.4f}\n\n")
        
        f.write("## Per-Class IoU\n")
        for class_name, iou in metrics_dict["per_class_iou"].items():
            if class_name != "mean_iou":
                f.write(f"- {class_name}: {iou:.4f}\n")
        f.write("\n")
        
        f.write("## Confusion Matrix\n")
        cm = metrics_dict["confusion_matrix"]
        f.write("```\n")
        f.write(str(cm))
        f.write("\n```\n\n")
        
        f.write("## Visualisations\n")
        f.write("- Prediction samples: docs/figures/prediction_visualisations.png\n\n")
        
        f.write("## Recommendations\n")
        f.write("- [Analysis based on metrics]\n")

def evaluate(checkpoint_path, config):
    """
    Main evaluation function.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load model
    model = load_trained_model(checkpoint_path, config, device)
    
    # Get test dataloader
    train_loader, val_loader = build_dataloaders(config)
    # For now, use val_loader as test (in real scenario, have separate test)
    test_loader = val_loader
    
    # Run inference
    predictions, labels = run_inference_on_test_set(model, test_loader, device)
    
    # Compute metrics
    class_names = ["no_damage", "minor", "major", "destroyed"]
    report = compute_full_report(predictions, labels, class_names)
    
    # Visualise
    visualise_predictions(model, test_loader.dataset)
    
    # Save report
    save_evaluation_report(report)
    
    # Print summary
    print("Evaluation Complete")
    print(f"Mean IoU: {report['metrics']['iou']['mean_iou']:.4f}")
    print(f"Pixel Accuracy: {report['metrics']['accuracy']:.4f}")
    print(f"Macro F1: {report['metrics']['f1']['macro_f1']:.4f}")

# TEST
if __name__ == "__main__":
    with open("configs/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    checkpoint_path = "checkpoints/damage_model.pth"
    if os.path.exists(checkpoint_path):
        evaluate(checkpoint_path, config)
    else:
        print("Checkpoint not found. Train the model first.")
