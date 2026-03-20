from typing import Tuple

import torch
from torch import nn as nn
from torch.nn import functional as F


class FeatureCNN_Attn(nn.Module):
    def __init__(self, n_classes: int, drop: float = 0.35):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 128, 5, padding=2)
        self.bn1 = nn.BatchNorm1d(128)
        self.conv2 = nn.Conv1d(128, 256, 3, padding=1)
        self.bn2 = nn.BatchNorm1d(256)

        self.attn = nn.MultiheadAttention(embed_dim=256, num_heads=4, dropout=drop, batch_first=True)
        self.ln = nn.LayerNorm(256)

        self.emb_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(drop),
        )
        self.out = nn.Linear(128, n_classes)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = x.transpose(1, 2)
        attn_out, _ = self.attn(x, x, x)
        x = self.ln(x + attn_out)
        x = x.mean(dim=1)
        emb = self.emb_head(x)
        logits = self.out(emb)
        return logits, emb


class RLDecisionLayer(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, 2))

    def forward(self, s: torch.Tensor) -> torch.Tensor:
        return self.net(s)
