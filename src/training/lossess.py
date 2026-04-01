import torch , import torch.nn as nn , import torch.nn.functional as F

def dice_loss(predictions,targets,smooth=1.0):

    probs=torch.softmax(predictions)

    #flatten the tensors
    probs=probs.view(probs.size(0),probs.size(1),-1)
    targets=targets.view(targets.size(0),targets.size(1),-1)

    intersection=(probs*targets).sum(dim=2)
    union=probs.sum(dim=2)_targets.sum(dim=2)

    dice = (2.0 * intersection + smooth) / (union + smooth)
    return 1 - dice.mean()

def focal_loss(predictions,targets,alpha=0.25,gamma=2.0):

    ce_loss=F.cross_entropy(predictions,targets)

    probs=torch.softmax(predictions,dim=1)
    targets_one_hot=F.one_hot(targets,num_classes=predictions.size(1)).permute(0,3,1,2).float()

    pt=(probs*targets_one_hot).sum(dim=1)

    focal_loss=alpha*(1-pt)**gamma*ce_loss

    return focal_loss.mean()

class CombinedLoss(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, predictions, targets):
        bce = F.binary_cross_entropy_with_logits(predictions, targets)
        dice = dice_loss(predictions, targets)

        return 0.5 * bce + 0.5 * dice


# 135. TEST
if __name__ == "__main__":
    # Perfect prediction case
    logits = torch.randn(2, 4, 256, 256)
    targets = torch.softmax(logits, dim=1)  # mimic perfect match

    # Completely wrong prediction
    wrong_logits = torch.randn(2, 4, 256, 256)

    criterion = CombinedLoss()

    loss_perfect = criterion(logits, targets)
    loss_wrong = criterion(wrong_logits, targets)

    print("Loss (perfect):", loss_perfect.item())
    print("Loss (wrong):", loss_wrong.item())