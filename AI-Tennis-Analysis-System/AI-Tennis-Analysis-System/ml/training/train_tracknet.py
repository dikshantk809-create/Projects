"""Train TrackNetV4-style ball tracker (heatmap regression).

Targets are Gaussian heatmaps centered on the labeled ball position. Loss = weighted
BCE/MSE on the heatmap. This is a compact trainer skeleton; plug your dataset loader.
Requires torch. Export with torch.jit.save → ml/export/tracknet.ts for the edge.
"""
from __future__ import annotations
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="ml/datasets/tennis")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--out", default="ml/export/tracknet.ts")
    args = ap.parse_args()
    import torch, torch.nn as nn
    # --- minimal U-Net-ish heatmap net (replace with full TrackNetV4) ---
    class Net(nn.Module):
        def __init__(self, in_ch=9):  # 3 frames x RGB
            super().__init__()
            self.enc = nn.Sequential(nn.Conv2d(in_ch,32,3,1,1), nn.ReLU(),
                                     nn.Conv2d(32,64,3,2,1), nn.ReLU())
            self.dec = nn.Sequential(nn.ConvTranspose2d(64,32,2,2), nn.ReLU(),
                                     nn.Conv2d(32,1,3,1,1), nn.Sigmoid())
        def forward(self,x): return self.dec(self.enc(x))
    model = Net()
    print("TrackNet trainer ready — wire dataset loader at", args.data)
    # training loop omitted for brevity; see ml/README.md for the full recipe.
    scripted = torch.jit.script(model)
    torch.jit.save(scripted, args.out)
    print("exported", args.out)

if __name__ == "__main__":
    main()
