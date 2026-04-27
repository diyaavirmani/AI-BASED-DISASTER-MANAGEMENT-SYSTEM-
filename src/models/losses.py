import torch
import torch.nn as nn
import torch.nn.functional as F

class CombinedLoss(nn.Module):
    def __init__(self, dice_weight=0.5, ce_weight=0.5):
        super(CombinedLoss, self).__init__()
        self.dice_weight = dice_weight
        self.ce_weight = ce_weight
        self.ce_loss = nn.CrossEntropyLoss()
    
    def dice_loss(self, pred, target, smooth=1e-6):
        # pred: (batch, classes, h, w)
        # target: (batch, h, w) with class indices
        
        # Convert target to one-hot
        target_one_hot = torch.zeros_like(pred)
        target_one_hot.scatter_(1, target.unsqueeze(1), 1)
        
        # Flatten
        pred_flat = pred.view(pred.size(0), pred.size(1), -1)
        target_flat = target_one_hot.view(target_one_hot.size(0), target_one_hot.size(1), -1)
        
        # Dice coefficient
        intersection = torch.sum(pred_flat * target_flat, dim=2)
        pred_sum = torch.sum(pred_flat, dim=2)
        target_sum = torch.sum(target_flat, dim=2)
        
        dice = (2. * intersection + smooth) / (pred_sum + target_sum + smooth)
        dice_loss = 1 - dice.mean(dim=1)  # Mean over classes
        
        return dice_loss.mean()  # Mean over batch
    
    def forward(self, pred, target):
        # pred: (batch, classes, h, w) - logits
        # target: (batch, h, w) - class indices
        
        ce = self.ce_loss(pred, target)
        
        # Apply softmax to get probabilities for dice
        pred_softmax = F.softmax(pred, dim=1)
        dice = self.dice_loss(pred_softmax, target)
        
        return self.ce_weight * ce + self.dice_weight * dice