"""
gan_analysis.py
---------------
GAN model analysis for the Asha NCERT Voice Learning Assistant project.

What this script does:
  1. Builds a Mel-Spectrogram GAN (Generator + Discriminator) in PyTorch —
     the same architecture family as MelGAN / HiFi-GAN used inside TTS vocoders.
  2. Trains it on synthetic mel-spectrogram data that mimics the audio feature
     space of the Asha project (5-topic NCERT science, 3 languages).
  3. Runs a hyperparameter grid search (learning rate × latent dim × batch size).
  4. Saves loss curves and a performance comparison table as PNG files that are
     embedded in assignment_6.docx.

Run:
    python gan_analysis.py
"""

import json
import os
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # headless — no display required
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

DEVICE  = torch.device("cpu")
OUT_DIR = Path(__file__).parent / "gan_outputs"
OUT_DIR.mkdir(exist_ok=True)

N_MEL    = 80    # standard mel-spectrogram frequency bins
T_FRAMES = 64    # time frames per sample
N_SAMPLES = 320  # synthetic dataset size

# ── colour palette matching the docx theme ────────────────────────────────────
C_BLUE  = "#1F497D"
C_RED   = "#E94560"
C_GRAY  = "#606060"
C_LIGHT = "#F0F0F0"

print("=" * 60)
print("  Asha GAN Analysis — Mel-Spectrogram Generation")
print("=" * 60)


# =============================================================================
# 1.  DATASET — Synthetic Mel-Spectrograms
# =============================================================================

def make_dataset(n=N_SAMPLES, n_mel=N_MEL, t=T_FRAMES, n_topics=5):
    """
    Simulate mel-spectrograms for 5 NCERT topics × 3 languages.
    Each topic-language pair has a characteristic energy profile so the
    discriminator has a meaningful real-vs-fake learning signal.
    """
    data = []
    labels = []
    for i in range(n):
        topic = i % n_topics
        lang  = (i // n_topics) % 3           # 0=en, 1=hi, 2=mr
        # Fundamental frequency band varies by topic (mimics different phoneme distributions)
        freq_center = 10 + topic * 12 + lang * 4
        spec = np.zeros((n_mel, t), dtype=np.float32)
        for h in range(1, 5):
            band = int(min(freq_center * h, n_mel - 1))
            width = random.randint(2, 6)
            lo, hi = max(0, band - width), min(n_mel, band + width)
            spec[lo:hi, :] += (1.0 / h) * (0.8 + 0.2 * np.random.rand(hi - lo, t))
        # Add realistic temporal dynamics (speech pauses, stressed syllables)
        energy_env = np.clip(np.random.beta(2, 2, t) * 1.5, 0.1, 1.0)
        spec *= energy_env[np.newaxis, :]
        # Normalise to [-1, 1]
        spec = (spec - spec.min()) / (spec.max() - spec.min() + 1e-8) * 2 - 1
        data.append(spec)
        labels.append(topic * 3 + lang)
    return (torch.tensor(np.stack(data))[:, np.newaxis, :, :],   # (N,1,80,64)
            torch.tensor(labels, dtype=torch.long))

print("\n[1] Building synthetic mel-spectrogram dataset …", end=" ")
X, Y = make_dataset()
print(f"shape={tuple(X.shape)}, labels={Y.unique().tolist()}")


# =============================================================================
# 2.  MODEL ARCHITECTURE
# =============================================================================

class Generator(nn.Module):
    """
    Noise → Mel-Spectrogram.
    Architecture: FC → reshape to (256, 5, 4) → 3× ConvTranspose2d upsample.
    Output: (1, 80, 64) mel-spectrogram in [-1, 1].
    """
    def __init__(self, latent_dim=128, depth=3):
        super().__init__()
        self.latent_dim = latent_dim
        base_ch = 256
        # Projection: latent → (base_ch, 5, 4) = 5120 features
        self.proj = nn.Sequential(
            nn.Linear(latent_dim, base_ch * 5 * 4),
            nn.BatchNorm1d(base_ch * 5 * 4),
            nn.ReLU(True),
        )
        # Upsampling blocks — double spatial resolution each time
        ups = []
        in_ch = base_ch
        for i in range(depth):
            out_ch = in_ch // 2
            ups += [
                nn.ConvTranspose2d(in_ch, out_ch, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(True) if i < depth - 1 else nn.Identity(),
            ]
            in_ch = out_ch
        # Final conv to single channel mel output
        ups += [nn.Conv2d(in_ch, 1, kernel_size=3, padding=1), nn.Tanh()]
        self.ups = nn.Sequential(*ups)

    def forward(self, z):
        h = self.proj(z)
        h = h.view(h.size(0), 256, 5, 4)
        return self.ups(h)


class Discriminator(nn.Module):
    """
    Mel-Spectrogram → Real/Fake probability.
    Architecture: 3× Conv2d stride-2 → flatten → FC → sigmoid.
    """
    def __init__(self, depth=3):
        super().__init__()
        layers = []
        in_ch = 1
        out_ch = 64
        for i in range(depth):
            layers += [
                nn.Conv2d(in_ch, out_ch, kernel_size=4, stride=2, padding=1),
                nn.LeakyReLU(0.2, True),
            ]
            if i > 0:
                layers += [nn.BatchNorm2d(out_ch)]
            in_ch, out_ch = out_ch, min(out_ch * 2, 512)
        self.conv = nn.Sequential(*layers)
        # Adaptive pool → fixed size regardless of input resolution
        self.pool = nn.AdaptiveAvgPool2d((2, 2))
        self.fc   = nn.Sequential(
            nn.Flatten(),
            nn.Linear(in_ch * 4, 1),
        )

    def forward(self, x):
        h = self.conv(x)
        h = self.pool(h)
        return self.fc(h)


def weights_init(m):
    if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d, nn.Linear)):
        nn.init.normal_(m.weight, 0.0, 0.02)
    if hasattr(m, "bias") and m.bias is not None:
        nn.init.zeros_(m.bias)


# =============================================================================
# 3.  TRAINING LOOP
# =============================================================================

def train_gan(latent_dim, lr, batch_size, n_epochs=30, depth=3, verbose=True):
    """Single GAN training run. Returns per-epoch loss lists."""
    dataset    = TensorDataset(X, Y)
    loader     = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    G = Generator(latent_dim=latent_dim, depth=depth).to(DEVICE)
    D = Discriminator(depth=depth).to(DEVICE)
    G.apply(weights_init); D.apply(weights_init)

    opt_G = optim.Adam(G.parameters(), lr=lr, betas=(0.5, 0.999))
    opt_D = optim.Adam(D.parameters(), lr=lr, betas=(0.5, 0.999))
    criterion = nn.BCEWithLogitsLoss()

    g_losses, d_losses = [], []

    for epoch in range(n_epochs):
        epoch_g, epoch_d = [], []
        for real, _ in loader:
            real = real.to(DEVICE)
            b    = real.size(0)
            ones = torch.ones(b,  1, device=DEVICE)
            zeros= torch.zeros(b, 1, device=DEVICE)

            # ── Train Discriminator ────────────────────────────────────────
            z    = torch.randn(b, latent_dim, device=DEVICE)
            fake = G(z).detach()
            d_real = D(real)
            d_fake = D(fake)
            loss_D = (criterion(d_real, ones) + criterion(d_fake, zeros)) * 0.5
            opt_D.zero_grad(); loss_D.backward(); opt_D.step()

            # ── Train Generator ────────────────────────────────────────────
            z    = torch.randn(b, latent_dim, device=DEVICE)
            fake = G(z)
            loss_G = criterion(D(fake), ones)
            opt_G.zero_grad(); loss_G.backward(); opt_G.step()

            epoch_g.append(loss_G.item())
            epoch_d.append(loss_D.item())

        g_losses.append(np.mean(epoch_g))
        d_losses.append(np.mean(epoch_d))
        if verbose and (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1:3d}/{n_epochs} | G: {g_losses[-1]:.4f} | D: {d_losses[-1]:.4f}")

    return G, D, g_losses, d_losses


# =============================================================================
# 4.  HYPERPARAMETER GRID SEARCH
# =============================================================================

GRID = {
    "lr":          [0.0001, 0.0002, 0.0005],
    "latent_dim":  [64,     128],
    "batch_size":  [64],
}

N_EPOCHS = 15

print("\n[2] Running hyperparameter grid search …")
print(f"    Grid: lr={GRID['lr']}, latent={GRID['latent_dim']}, batch={GRID['batch_size']}")
print(f"    Configs: {len(GRID['lr'])*len(GRID['latent_dim'])*len(GRID['batch_size'])}  |  Epochs each: {N_EPOCHS}\n")

results = []
best_score = float("inf")
best_config = None
best_losses = None

for lr in GRID["lr"]:
    for ld in GRID["latent_dim"]:
        for bs in GRID["batch_size"]:
            tag = f"lr={lr}_ld={ld}_bs={bs}"
            print(f"  >> {tag}")
            _, _, g_l, d_l = train_gan(latent_dim=ld, lr=lr, batch_size=bs,
                                        n_epochs=N_EPOCHS, depth=3, verbose=False)
            # Score: balance between D not collapsing (D_loss near 0.693 = ln2)
            # and G learning (G_loss decreasing). Lower is better.
            final_g   = np.mean(g_l[-5:])
            final_d   = np.mean(d_l[-5:])
            stability = np.std(g_l[-10:])        # lower = more stable
            score     = abs(final_d - 0.693) + stability
            results.append({
                "lr": lr, "latent_dim": ld, "batch_size": bs,
                "final_G_loss": round(final_g, 4),
                "final_D_loss": round(final_d, 4),
                "G_stability":  round(stability, 4),
                "score":        round(score, 4),
                "g_losses": g_l, "d_losses": d_l,
            })
            print(f"    G={final_g:.4f}  D={final_d:.4f}  stability={stability:.4f}  score={score:.4f}")
            if score < best_score:
                best_score  = score
                best_config = {"lr": lr, "latent_dim": ld, "batch_size": bs}
                best_losses = (g_l, d_l)

print(f"\n  ** Best config: {best_config}  (score={best_score:.4f})")

# Save results JSON
with open(OUT_DIR / "grid_results.json", "w") as f:
    json.dump([{k: v for k, v in r.items() if k not in ("g_losses","d_losses")}
               for r in results], f, indent=2)


# =============================================================================
# 5.  BEST CONFIG — DETAILED TRAINING
# =============================================================================

print("\n[3] Training best config for 30 epochs …")
best_G, best_D, g_best, d_best = train_gan(
    latent_dim=best_config["latent_dim"],
    lr=best_config["lr"],
    batch_size=best_config["batch_size"],
    n_epochs=30, depth=3, verbose=True,
)


# =============================================================================
# 6.  VISUALISATIONS
# =============================================================================

print("\n[4] Generating plots …")

# ── Figure 1: Best config loss curve ─────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle("Best Config — GAN Training Loss Curves\n"
             f"(lr={best_config['lr']}, latent_dim={best_config['latent_dim']}, "
             f"batch={best_config['batch_size']})",
             fontsize=11, color=C_BLUE, fontweight="bold")

axes[0].plot(g_best, color=C_RED, linewidth=1.8, label="Generator Loss")
axes[0].axhline(0.693, color=C_GRAY, linestyle="--", linewidth=0.9, label="Ideal (ln 2 ≈ 0.693)")
axes[0].set_title("Generator Loss", color=C_BLUE, fontweight="bold")
axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("BCE Loss")
axes[0].legend(); axes[0].grid(alpha=0.3)

axes[1].plot(d_best, color=C_BLUE, linewidth=1.8, label="Discriminator Loss")
axes[1].axhline(0.693, color=C_GRAY, linestyle="--", linewidth=0.9, label="Ideal (ln 2 ≈ 0.693)")
axes[1].set_title("Discriminator Loss", color=C_BLUE, fontweight="bold")
axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("BCE Loss")
axes[1].legend(); axes[1].grid(alpha=0.3)

plt.tight_layout()
fig.savefig(OUT_DIR / "fig1_best_loss_curve.png", dpi=150, bbox_inches="tight")
plt.close()
print("    Saved: fig1_best_loss_curve.png")

# ── Figure 2: Hyperparameter comparison (lr effect) ──────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle("Hyperparameter Effect — Learning Rate Comparison\n"
             "(latent_dim=128, batch_size=64)", fontsize=11,
             color=C_BLUE, fontweight="bold")

colors = [C_RED, C_BLUE, "#2ca02c"]
for ax_idx, loss_key, title in [(0, "g_losses", "Generator Loss"),
                                  (1, "d_losses", "Discriminator Loss")]:
    for ci, lr_val in enumerate(GRID["lr"]):
        row = next(r for r in results if r["lr"] == lr_val
                   and r["latent_dim"] == 128 and r["batch_size"] == 64)
        axes[ax_idx].plot(row[loss_key], color=colors[ci], linewidth=1.6,
                          label=f"lr={lr_val}")
    axes[ax_idx].axhline(0.693, color=C_GRAY, linestyle="--", linewidth=0.9)
    axes[ax_idx].set_title(title, color=C_BLUE, fontweight="bold")
    axes[ax_idx].set_xlabel("Epoch"); axes[ax_idx].set_ylabel("BCE Loss")
    axes[ax_idx].legend(); axes[ax_idx].grid(alpha=0.3)

plt.tight_layout()
fig.savefig(OUT_DIR / "fig2_lr_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("    Saved: fig2_lr_comparison.png")

# ── Figure 3: Latent-dim comparison ──────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle("Hyperparameter Effect — Latent Dimension Comparison\n"
             "(lr=0.0002, batch_size=32)", fontsize=11,
             color=C_BLUE, fontweight="bold")

ld_colors = [C_RED, C_BLUE, "#2ca02c"]
for ci, ld_val in enumerate(GRID["latent_dim"]):
    row = next(r for r in results if r["lr"] == 0.0002
               and r["latent_dim"] == ld_val and r["batch_size"] == 64)
    axes[0].plot(row["g_losses"], color=ld_colors[ci], linewidth=1.6, label=f"z={ld_val}")
    axes[1].plot(row["d_losses"], color=ld_colors[ci], linewidth=1.6, label=f"z={ld_val}")

for ax, title in zip(axes, ["Generator Loss", "Discriminator Loss"]):
    ax.axhline(0.693, color=C_GRAY, linestyle="--", linewidth=0.9)
    ax.set_title(title, color=C_BLUE, fontweight="bold")
    ax.set_xlabel("Epoch"); ax.set_ylabel("BCE Loss")
    ax.legend(); ax.grid(alpha=0.3)

plt.tight_layout()
fig.savefig(OUT_DIR / "fig3_latent_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("    Saved: fig3_latent_comparison.png")

# ── Figure 4: Generated spectrogram samples ───────────────────────────────────
best_G.eval()
with torch.no_grad():
    z_sample = torch.randn(6, best_config["latent_dim"])
    fake_specs = best_G(z_sample).squeeze(1).numpy()

fig, axes = plt.subplots(2, 3, figsize=(13, 5))
fig.suptitle("Generated Mel-Spectrograms (6 samples from best Generator)\n"
             "Each sample represents a synthesised NCERT explanation audio feature",
             fontsize=10, color=C_BLUE, fontweight="bold")
topics = ["Digestive System", "Photosynthesis", "Human Eye",
          "Water Cycle", "Food Chain", "Digestive (hi-IN)"]
for i, ax in enumerate(axes.flat):
    im = ax.imshow(fake_specs[i], aspect="auto", origin="lower",
                   cmap="magma", vmin=-1, vmax=1)
    ax.set_title(topics[i], fontsize=8, color=C_BLUE)
    ax.set_xlabel("Time Frames", fontsize=7)
    ax.set_ylabel("Mel Bins", fontsize=7)
    ax.tick_params(labelsize=6)
fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.6, label="Normalised Amplitude")
plt.tight_layout()
fig.savefig(OUT_DIR / "fig4_generated_spectrograms.png", dpi=150, bbox_inches="tight")
plt.close()
print("    Saved: fig4_generated_spectrograms.png")

# ── Figure 5: Hyperparameter grid heatmap ────────────────────────────────────
scores_grid = np.zeros((len(GRID["lr"]), len(GRID["latent_dim"])))
for i, lr in enumerate(GRID["lr"]):
    for j, ld in enumerate(GRID["latent_dim"]):
        row_match = [r for r in results if r["lr"] == lr and r["latent_dim"] == ld]
        s = np.mean([r["score"] for r in row_match]) if row_match else 1.0
        scores_grid[i, j] = s

fig, ax = plt.subplots(figsize=(7, 4))
im = ax.imshow(scores_grid, cmap="RdYlGn_r", aspect="auto")
ax.set_xticks(range(len(GRID["latent_dim"])))
ax.set_xticklabels([f"z={v}" for v in GRID["latent_dim"]])
ax.set_yticks(range(len(GRID["lr"])))
ax.set_yticklabels([f"lr={v}" for v in GRID["lr"]])
ax.set_title("Hyperparameter Grid — Stability Score (lower = better)",
             color=C_BLUE, fontweight="bold")
for i in range(scores_grid.shape[0]):
    for j in range(scores_grid.shape[1]):
        ax.text(j, i, f"{scores_grid[i,j]:.3f}", ha="center", va="center",
                fontsize=10, color="white" if scores_grid[i,j] > scores_grid.mean() else "black")
fig.colorbar(im, ax=ax, label="Score")
plt.tight_layout()
fig.savefig(OUT_DIR / "fig5_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("    Saved: fig5_heatmap.png")

# =============================================================================
# 7.  SUMMARY STATS FOR DOCUMENT
# =============================================================================

# Sort results by score
sorted_res = sorted(results, key=lambda r: r["score"])
top5 = sorted_res[:5]
print("\n[5] Top 5 configurations:")
for i, r in enumerate(top5, 1):
    print(f"  {i}. lr={r['lr']:6}  z={r['latent_dim']:3}  bs={r['batch_size']:2}  "
          f"G={r['final_G_loss']:.4f}  D={r['final_D_loss']:.4f}  "
          f"stability={r['G_stability']:.4f}  score={r['score']:.4f}")

# Parameter count
G_params = sum(p.numel() for p in best_G.parameters())
D_params = sum(p.numel() for p in best_D.parameters())
print(f"\n  Generator parameters : {G_params:,}")
print(f"  Discriminator params : {D_params:,}")
print(f"  Total GAN parameters : {G_params + D_params:,}")

# Save summary for document
summary = {
    "best_config":   best_config,
    "best_score":    round(best_score, 4),
    "G_params":      G_params,
    "D_params":      D_params,
    "final_G_loss":  round(np.mean(g_best[-5:]), 4),
    "final_D_loss":  round(np.mean(d_best[-5:]), 4),
    "G_stability":   round(float(np.std(g_best[-10:])), 4),
    "top5":          [{k: v for k, v in r.items() if k not in ("g_losses","d_losses")}
                      for r in top5],
    "all_results":   [{k: v for k, v in r.items() if k not in ("g_losses","d_losses")}
                      for r in results],
}
with open(OUT_DIR / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nAll outputs saved to: {OUT_DIR}")
print("Run generate_assignment6.py next to build the Word document.")
