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

    def compute_f1(predictions, targets, num_classes=4):
    f1_scores = {}

    for cls in range(num_classes):
        pred_mask = (predictions == cls)
        target_mask = (targets == cls)

        tp = (pred_mask & target_mask).sum()
        fp = (pred_mask & ~target_mask).sum()
        fn = (~pred_mask & target_mask).sum()

        denom = (2 * tp + fp + fn)

        if denom == 0:
            f1 = 1.0
        else:
            f1 = (2 * tp) / denom

        f1_scores[f"class_{cls}"] = float(f1)

    mean_f1 = sum(f1_scores.values()) / num_classes
    return {**f1_scores, "mean_f1": float(mean_f1)}

    def compute_pixel_accuracy(predictions, targets):
    correct = (predictions == targets).sum()
    total = targets.size

    return float(correct / total)

    def compute_all_metrics(predictions, targets, num_classes=4):
    iou_dict = compute_iou(predictions, targets, num_classes)
    f1_dict = compute_f1(predictions, targets, num_classes)
    pixel_acc = compute_pixel_accuracy(predictions, targets)

    return {
        "iou": iou_dict,
        "f1": f1_dict,
        "pixel_accuracy": pixel_acc
    }
    