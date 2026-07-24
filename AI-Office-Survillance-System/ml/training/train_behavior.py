"""Train a temporal behavior classifier on YOLO-pose keypoint sequences.

Input: sequences of 17 COCO keypoints (x,y,conf) over T frames per tracked person.
Output: activity label in {working, idle, phone, talking, walking, break, meeting}.
This is a compact GRU baseline — swap for a TCN/Transformer for higher accuracy.
"""
from __future__ import annotations
import argparse, json
# NOTE: requires torch; kept import-light so the file is browsable without it.

def build_model(in_dim=51, hidden=128, n_classes=7):
    import torch.nn as nn
    class GRUClf(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(in_dim, hidden, batch_first=True, num_layers=2, dropout=0.2)
            self.head = nn.Linear(hidden, n_classes)
        def forward(self, x):           # x: (B, T, 51)
            _, h = self.gru(x)
            return self.head(h[-1])
    return GRUClf()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="ml/datasets/behavior")  # npz: X (N,T,51), y (N,)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--out", default="ml/export/behavior_gru.pt")
    args = ap.parse_args()

    import numpy as np, torch
    from torch.utils.data import TensorDataset, DataLoader
    d = np.load(f"{args.data}/train.npz")
    ds = TensorDataset(torch.tensor(d["X"], dtype=torch.float32),
                       torch.tensor(d["y"], dtype=torch.long))
    dl = DataLoader(ds, batch_size=64, shuffle=True)
    model = build_model(); opt = torch.optim.Adam(model.parameters(), 1e-3)
    lossf = torch.nn.CrossEntropyLoss()
    for ep in range(args.epochs):
        tot = 0.0
        for xb, yb in dl:
            opt.zero_grad(); out = model(xb); loss = lossf(out, yb)
            loss.backward(); opt.step(); tot += loss.item()
        print(f"epoch {ep+1}/{args.epochs} loss={tot/len(dl):.4f}")
    torch.save(model.state_dict(), args.out)
    print("saved", args.out)

if __name__ == "__main__":
    main()
