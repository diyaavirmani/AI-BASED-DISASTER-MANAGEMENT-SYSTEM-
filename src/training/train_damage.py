import os
import torch
import mlflow

from src.data_pipeline.dataset_builder import build_dataloaders
from src.models.unet import DamageSegmentationModel
from src.training.losses import CombinedLoss
from src.training.metrics import compute_all_metrics


# --------------------------------------------------
# 141. TRAIN ONE EPOCH
# --------------------------------------------------
def train_one_epoch(model, dataloader, optimizer, loss_fn, device):
    model.train()
    total_loss = 0.0

    for images, masks in dataloader:
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()

        outputs = model(images)
        loss = loss_fn(outputs, masks)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(dataloader)
    return avg_loss


# --------------------------------------------------
# 142. VALIDATE ONE EPOCH
# --------------------------------------------------
def validate_one_epoch(model, dataloader, loss_fn, metrics_fn, device):
    model.eval()
    total_loss = 0.0

    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device)
            masks = masks.to(device)

            outputs = model(images)
            loss = loss_fn(outputs, masks)

            total_loss += loss.item()

            preds = torch.argmax(outputs, dim=1)

            all_preds.append(preds.cpu())
            all_targets.append(masks.cpu())

    all_preds = torch.cat(all_preds)
    all_targets = torch.cat(all_targets)

    metrics = metrics_fn(all_preds.numpy(), all_targets.numpy())
    avg_loss = total_loss / len(dataloader)

    return avg_loss, metrics


# --------------------------------------------------
# 143. SAVE CHECKPOINT
# --------------------------------------------------
def save_checkpoint(model, optimizer, epoch, val_iou, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "best_val_iou": val_iou
    }, path)


# --------------------------------------------------
# 144. LOAD CHECKPOINT
# --------------------------------------------------
def load_checkpoint(model, optimizer, path, device):
    checkpoint = torch.load(path, map_location=device)

    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    return checkpoint["epoch"], checkpoint["best_val_iou"]


# --------------------------------------------------
# 145. MAIN TRAIN FUNCTION
# --------------------------------------------------
def train(config):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # DATALOADERS
    train_loader, val_loader = build_dataloaders(config)

    # MODEL
    model = DamageSegmentationModel(config).to(device)

    # LOSS
    loss_fn = CombinedLoss()

    # OPTIMIZER
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["training"]["lr"]
    )

    # SCHEDULER
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer,
        step_size=config["training"]["step_size"],
        gamma=config["training"]["gamma"]
    )

    # EARLY STOPPING
    best_val_iou = 0.0
    patience = config["training"]["early_stopping_patience"]
    patience_counter = 0

    checkpoint_path = config["training"]["checkpoint_path"]

    # MLFLOW
    mlflow.start_run()

    for epoch in range(config["training"]["max_epochs"]):
        print(f"\nEpoch [{epoch+1}/{config['training']['max_epochs']}]")

        train_loss = train_one_epoch(
            model, train_loader, optimizer, loss_fn, device
        )

        val_loss, metrics = validate_one_epoch(
            model, val_loader, loss_fn, compute_all_metrics, device
        )

        val_iou = metrics["iou"]["mean_iou"]

        # LOGGING
        mlflow.log_metric("train_loss", train_loss, step=epoch)
        mlflow.log_metric("val_loss", val_loss, step=epoch)
        mlflow.log_metric("val_mean_iou", val_iou, step=epoch)

        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_loss:.4f}")
        print(f"Val IoU: {val_iou:.4f}")

        # CHECKPOINT (BEST MODEL)
        if val_iou > best_val_iou:
            best_val_iou = val_iou
            save_checkpoint(model, optimizer, epoch, val_iou, checkpoint_path)
            patience_counter = 0
            print("✅ Best model saved")
        else:
            patience_counter += 1

        # EARLY STOPPING
        if patience_counter >= patience:
            print("⛔ Early stopping triggered")
            break

        scheduler.step()

    mlflow.end_run()


# --------------------------------------------------
# 146. FIRST RUN (DEBUG MODE)
# --------------------------------------------------
if __name__ == "__main__":
    import yaml

    with open("configs/config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # 🔥 TEMP DEBUG OVERRIDE
    config["training"]["max_epochs"] = 5
    config["data"]["subset_size"] = 50  # Ensure your dataloader supports this

    train(config)