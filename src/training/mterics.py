def compute_iou(predictions, targets, num_classes=4):
    """
    predictions, targets: shape (H, W) or (N, H, W)
    values: 0 ... num_classes-1
    """
    iou_scores = {}

    for cls in range(num_classes):
        pred_mask = (predictions == cls)
        target_mask = (targets == cls)

        intersection = (pred_mask & target_mask).sum()
        union = (pred_mask | target_mask).sum()

        if union == 0:
            iou = 1.0  # no ground truth & no prediction → perfect
        else:
            iou = intersection / union

        iou_scores[f"class_{cls}"] = float(iou)

    mean_iou = sum(iou_scores.values()) / num_classes
    return {**iou_scores, "mean_iou": float(mean_iou)}