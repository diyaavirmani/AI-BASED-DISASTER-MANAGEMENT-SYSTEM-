import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, accuracy_score

def compute_iou(predictions, targets, num_classes=4):
    """
    Compute Intersection over Union (IoU) for each class and mean IoU.
    
    Args:
        predictions: numpy array of predicted labels
        targets: numpy array of true labels
        num_classes: number of classes
    
    Returns:
        dict with per-class IoU and mean IoU
    """
    iou_per_class = {}
    total_iou = 0.0
    
    for class_id in range(num_classes):
        # True positives, false positives, false negatives for this class
        pred_mask = (predictions == class_id)
        true_mask = (targets == class_id)
        
        intersection = np.logical_and(pred_mask, true_mask).sum()
        union = np.logical_or(pred_mask, true_mask).sum()
        
        if union == 0:
            iou = 1.0  # If no ground truth and no prediction, consider perfect
        else:
            iou = intersection / union
        
        iou_per_class[f"class_{class_id}"] = iou
        total_iou += iou
    
    iou_per_class["mean_iou"] = total_iou / num_classes
    return {"iou": iou_per_class}

def compute_f1(predictions, targets, num_classes=4):
    """
    Compute F1 score for each class.
    
    Args:
        predictions: flattened numpy array of predicted labels
        targets: flattened numpy array of true labels
        num_classes: number of classes
    
    Returns:
        dict with per-class F1 and macro F1
    """
    f1_per_class = {}
    
    for class_id in range(num_classes):
        pred_binary = (predictions == class_id).astype(int)
        true_binary = (targets == class_id).astype(int)
        
        tp = np.sum(pred_binary * true_binary)
        fp = np.sum(pred_binary * (1 - true_binary))
        fn = np.sum((1 - pred_binary) * true_binary)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        f1_per_class[f"class_{class_id}"] = f1
    
    # Macro F1
    f1_per_class["macro_f1"] = np.mean(list(f1_per_class.values()))
    return {"f1": f1_per_class}

def compute_pixel_accuracy(predictions, targets):
    """
    Compute pixel-wise accuracy.
    
    Args:
        predictions: flattened numpy array of predicted labels
        targets: flattened numpy array of true labels
    
    Returns:
        dict with pixel accuracy
    """
    accuracy = np.mean(predictions == targets)
    return {"accuracy": accuracy}

def compute_all_metrics(predictions, targets, num_classes=4):
    """
    Compute all metrics: IoU, F1, and pixel accuracy.
    
    Args:
        predictions: numpy array of predicted labels (flattened)
        targets: numpy array of true labels (flattened)
        num_classes: number of classes
    
    Returns:
        dict containing all metrics
    """
    iou_metrics = compute_iou(predictions, targets, num_classes)
    f1_metrics = compute_f1(predictions, targets, num_classes)
    acc_metrics = compute_pixel_accuracy(predictions, targets)
    
    return {**iou_metrics, **f1_metrics, **acc_metrics}

# TEST
if __name__ == "__main__":
    # Test with identical inputs
    predictions = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    targets = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    
    metrics = compute_all_metrics(predictions, targets, num_classes=4)
    
    print("Test with identical inputs:")
    print(metrics)
    
    # Should all be 1.0