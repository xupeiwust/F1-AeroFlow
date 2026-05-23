import torch
import torch.nn as nn
import numpy as np


class AeroPINN(nn.Module):
    """
    Physics-Informed Neural Network for F1 aerodynamic coefficient prediction.

    Inputs  (all normalized internally):
        alpha  — angle of attack, degrees
        Re     — Reynolds number
        AR     — wing aspect ratio

    Outputs:
        Cd     — drag coefficient  (sigmoid-bounded positive)
        Cl     — lift coefficient  (tanh-bounded, signed)
    """

    # Normalization stats (matched to training data ranges)
    ALPHA_MEAN, ALPHA_STD = 10.0, 8.0
    RE_MEAN,    RE_STD    = 4.5e6, 2.0e6
    AR_MEAN,    AR_STD    = 4.0,   1.5

    def __init__(self, hidden=96, depth=5):
        super().__init__()
        layers = [nn.Linear(3, hidden), nn.Tanh()]
        for _ in range(depth - 1):
            layers += [nn.Linear(hidden, hidden), nn.Tanh()]
        layers += [nn.Linear(hidden, 2)]
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=0.6)
                nn.init.zeros_(m.bias)

    def _normalize(self, alpha, Re, AR):
        a  = (alpha - self.ALPHA_MEAN) / self.ALPHA_STD
        r  = (Re    - self.RE_MEAN)    / self.RE_STD
        ar = (AR    - self.AR_MEAN)    / self.AR_STD
        return torch.stack([a, r, ar], dim=-1)

    def forward(self, alpha, Re, AR):
        x       = self._normalize(alpha, Re, AR)
        raw     = self.net(x)
        Cd      = torch.sigmoid(raw[:, 0]) * 1.2      # Cd ∈ (0, 1.2)
        Cl      = torch.tanh(raw[:, 1]) * 5.0         # Cl ∈ (-5, 5)
        return Cd, Cl

    @torch.no_grad()
    def predict(self, alpha_deg: float, velocity_ms: float,
                AR: float = 6.15, chord: float = 0.325) -> tuple[float, float]:
        """Single-point inference — returns (Cd, Cl)."""
        from physics.f1_physics import AIR_DENSITY, AIR_VISCOSITY
        Re = AIR_DENSITY * velocity_ms * chord / AIR_VISCOSITY

        alpha = torch.tensor([alpha_deg], dtype=torch.float32)
        Re_t  = torch.tensor([Re],        dtype=torch.float32)
        AR_t  = torch.tensor([AR],        dtype=torch.float32)

        Cd, Cl = self.forward(alpha, Re_t, AR_t)
        return Cd.item(), Cl.item()
