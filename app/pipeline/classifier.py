import torch
from torch import nn as nn
from torch.nn import functional as F


class FeatureCNN_Attn(nn.Module):
    def __init__(self, n_feats, n_classes, drop=0.35, return_embedding=True):
        super().__init__()
        self.return_embedding = return_embedding
        self.conv1 = nn.Conv1d(1, 128, 5, padding=2)
        self.bn1   = nn.BatchNorm1d(128)
        self.conv2 = nn.Conv1d(128, 256, 3, padding=1)
        self.bn2   = nn.BatchNorm1d(256)
        self.attn  = nn.MultiheadAttention(embed_dim=256, num_heads=4, dropout=drop, batch_first=True)
        self.ln    = nn.LayerNorm(256)
        self.head  = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(drop),
        )
        self.out   = nn.Linear(128, n_classes)

    def forward(self, x):  # (B,1,F)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))   # (B,256,F)
        x = x.transpose(1, 2)                 # (B,F,256)
        attn_out, _ = self.attn(x, x, x)
        x = self.ln(x + attn_out)             # residual + norm
        x = x.mean(dim=1)                     # (B,256)
        emb = self.head(x)                    # (B,128)
        logits = self.out(emb)                # (B,C)
        return (logits, emb) if self.return_embedding else logits


class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.log_t = nn.Parameter(torch.zeros(1))
    def forward(self, logits):
        return logits / torch.exp(self.log_t)


class RLDecisionLayer(nn.Module):
    def __init__(self, in_dim, hidden=64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, 2))
    def forward(self, s):
        return self.net(s)


def get_logits(model_out):
    return model_out[0] if isinstance(model_out, (tuple, list)) else model_out
