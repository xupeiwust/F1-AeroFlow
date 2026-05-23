import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from models.pinn import AeroPINN
from physics.f1_physics import (
    thin_airfoil_cl, thin_airfoil_cd,
    AIR_DENSITY, AIR_VISCOSITY,
    ASPECT_RATIO, WING_CHORD, OSWALD_EFF,
)


class PINNAgent:
    """
    Trains the AeroPINN on physics-derived data and serves aerodynamic
    coefficient predictions.

    Training pipeline:
      1. Generate synthetic ground-truth from thin-airfoil theory + noise
      2. Minimize data loss (MSE) + physics loss (drag polar constraint,
         symmetry at zero incidence, Cd positivity)
    """

    def __init__(self):
        self.model   = AeroPINN()
        self.trained = False
        self.history: list[float] = []

    # ── Data generation ───────────────────────────────────────────────────────

    def _generate_data(self, n: int = 3000) -> dict:
        rng = np.random.default_rng(42)

        alphas     = rng.uniform(-5.0, 25.0, n)
        velocities = rng.uniform(30.0, 105.0, n)
        ARs        = rng.uniform(3.0,  8.0,   n)
        chords     = rng.uniform(0.15, 0.40,  n)

        Cls = np.array([thin_airfoil_cl(a, ar) for a, ar in zip(alphas, ARs)])
        Cds = np.array([thin_airfoil_cd(cl, ar) for cl, ar in zip(Cls, ARs)])

        # Sprinkle realistic variance (wind-tunnel scatter)
        Cls += rng.normal(0, 0.08, n)
        Cds += rng.normal(0, 0.003, n)
        Cds  = np.abs(Cds)

        Res = AIR_DENSITY * velocities * chords / AIR_VISCOSITY

        def t(x): return torch.tensor(x, dtype=torch.float32)
        return dict(alpha=t(alphas), Re=t(Res), AR=t(ARs), Cl=t(Cls), Cd=t(Cds))

    # ── Physics loss ──────────────────────────────────────────────────────────

    def _physics_loss(self, AR_batch: torch.Tensor,
                      Cl_pred: torch.Tensor, Cd_pred: torch.Tensor) -> torch.Tensor:
        # 1. Induced drag lower bound: Cd >= Cl² / (π·AR·e)
        Cd_ind = Cl_pred**2 / (torch.pi * AR_batch * OSWALD_EFF)
        loss_polar = torch.relu(Cd_ind - Cd_pred).mean()

        # 2. Cl(alpha=0) ≈ 0  (symmetry)
        bs = 32
        a0   = torch.zeros(bs)
        Re0  = torch.full((bs,), 4.5e6)
        AR0  = torch.full((bs,), 6.15)
        _, Cl0 = self.model(a0, Re0, AR0)
        loss_sym = (Cl0**2).mean()

        # 3. Cd must be strictly positive
        loss_pos = torch.relu(-Cd_pred + 1e-4).mean()

        return loss_polar + 0.4 * loss_sym + 0.2 * loss_pos

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, epochs: int = 500, callback=None) -> list[float]:
        data      = self._generate_data(3000)
        optimizer = optim.Adam(self.model.parameters(), lr=1e-3, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        mse       = nn.MSELoss()
        N         = data['alpha'].shape[0]

        self.model.train()
        for epoch in range(epochs):
            idx   = torch.randint(0, N, (256,))
            a_b   = data['alpha'][idx]
            Re_b  = data['Re'][idx]
            AR_b  = data['AR'][idx]
            Cl_b  = data['Cl'][idx]
            Cd_b  = data['Cd'][idx]

            optimizer.zero_grad()
            Cd_p, Cl_p = self.model(a_b, Re_b, AR_b)

            loss_data  = mse(Cl_p, Cl_b) + mse(Cd_p, Cd_b)
            loss_phys  = self._physics_loss(AR_b, Cl_p, Cd_p)
            loss       = loss_data + 0.15 * loss_phys

            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            self.history.append(loss.item())
            if callback and epoch % (epochs // 8) == 0:
                callback(epoch, loss.item())

        self.model.eval()
        self.trained = True
        return self.history

    # ── Inference ─────────────────────────────────────────────────────────────

    def simulate(self, alpha_deg: float, velocity_ms: float = 75.0,
                 AR: float = ASPECT_RATIO, chord: float = WING_CHORD) -> dict:
        """Return Cd, Cl for a single operating point."""
        if self.trained:
            Cd, Cl = self.model.predict(alpha_deg, velocity_ms, AR, chord)
        else:
            Cl = thin_airfoil_cl(alpha_deg, AR)
            Cd = thin_airfoil_cd(Cl, AR)

        LoD = Cl / max(abs(Cd), 1e-9)
        return {
            "alpha":    alpha_deg,
            "velocity": velocity_ms,
            "Cd":       float(Cd),
            "Cl":       float(Cl),
            "L_over_D": float(LoD),
        }

    def scan_alpha(self, velocity_ms: float = 75.0, n_points: int = 20) -> list[dict]:
        """Sweep angle of attack from -5° to 25°."""
        alphas  = np.linspace(-5, 25, n_points)
        results = [self.simulate(float(a), velocity_ms) for a in alphas]
        return results
