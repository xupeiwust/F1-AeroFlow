import numpy as np
from scipy.optimize import minimize_scalar

from physics.f1_physics import (
    max_corner_speed, max_straight_speed,
    CAR_MASS, GRAVITY, ENGINE_POWER,
    AIR_DENSITY, WING_AREA, ROLLING_RESIST, BODY_DRAG_AREA,
)
from tracks.track_data import TRACKS


class LaptimeAgent:
    """
    Estimates and optimises lap times given aerodynamic coefficients.

    Lap model (covers the full circuit):
      - Corner arcs  : speed limited by downforce + lateral grip
      - Straights    : acceleration phase → cruise at v_max
      - Linking zones: medium-speed transitions (~75 % of v_max)
    """

    DT = 0.05  # integration step (s)

    def __init__(self, pinn_agent):
        self.pinn = pinn_agent

    # ── Full-lap time estimate ────────────────────────────────────────────────

    def estimate_laptime(self, Cd: float, Cl: float, track: dict) -> float:
        v_max = max_straight_speed(Cd)

        t_total   = 0.0
        dist_done = 0.0

        # ── Corner arcs ───────────────────────────────────────────────────────
        for corner in track["corners"]:
            v_c   = max_corner_speed(Cl, corner["radius"])
            count = corner.get("count", 1)
            # Average turn arc ≈ 90 ° per corner instance
            arc   = np.pi * corner["radius"] * 0.5 * count
            t_total   += arc / max(v_c, 1.0)
            dist_done += arc

        # ── Straight sections ─────────────────────────────────────────────────
        for straight in track["straights"]:
            L         = straight["length_m"]
            v_entry   = min(50.0, v_max * 0.55)
            t_acc, d_acc = self._accelerate(v_entry, v_max, Cd)

            if d_acc >= L:
                t_total += self._coast(v_entry, L, Cd)
            else:
                t_total += t_acc + (L - d_acc) / max(v_max, 1.0)
            dist_done += L

        # ── Remaining track (linking zones, chicanes, etc.) ───────────────────
        lap_length   = track["length_km"] * 1000.0
        remaining    = max(0.0, lap_length - dist_done)
        v_link       = v_max * 0.72   # typical medium-speed section
        t_total     += remaining / max(v_link, 1.0)

        return t_total

    # ── Dynamics integration ──────────────────────────────────────────────────

    def _accelerate(self, v0: float, v_max: float, Cd: float):
        """Return (time, distance) to accelerate from v0 to v_max."""
        v, t, d = v0, 0.0, 0.0
        total_CdA = Cd * WING_AREA + BODY_DRAG_AREA
        while v < v_max * 0.97 and t < 35.0:
            F_engine  = min(ENGINE_POWER / max(v, 1.0), 14_000.0)
            F_drag    = 0.5 * AIR_DENSITY * v**2 * total_CdA
            F_rolling = ROLLING_RESIST * CAR_MASS * GRAVITY
            a         = (F_engine - F_drag - F_rolling) / CAR_MASS
            v        += a * self.DT
            v         = min(v, v_max)
            d        += v * self.DT
            t        += self.DT
        return t, d

    def _coast(self, v0: float, distance: float, Cd: float) -> float:
        """Time to cover `distance` starting from v0 under power."""
        total_CdA = Cd * WING_AREA + BODY_DRAG_AREA
        v, d, t = v0, 0.0, 0.0
        while d < distance:
            F_engine  = ENGINE_POWER / max(v, 1.0)
            F_drag    = 0.5 * AIR_DENSITY * v**2 * total_CdA
            F_rolling = ROLLING_RESIST * CAR_MASS * GRAVITY
            a         = (F_engine - F_drag - F_rolling) / CAR_MASS
            v        += a * self.DT
            v         = float(np.clip(v, 1.0, 102.0))
            d        += v * self.DT
            t        += self.DT
        return t

    # ── Wing-angle optimisation ───────────────────────────────────────────────

    def optimize_wing_angle(self, track_name: str, velocity: float = 75.0) -> dict | None:
        if track_name not in TRACKS:
            return None

        track = TRACKS[track_name]

        def objective(alpha):
            r = self.pinn.simulate(float(alpha), velocity)
            return self.estimate_laptime(r["Cd"], r["Cl"], track)

        # Coarse grid search then bounded refinement
        alphas = np.linspace(1.0, 22.0, 42)
        times  = np.array([objective(a) for a in alphas])
        best_i = int(np.argmin(times))
        lo     = max(0.5, alphas[best_i] - 2.5)
        hi     = min(23.0, alphas[best_i] + 2.5)

        refined = minimize_scalar(objective, bounds=(lo, hi), method="bounded",
                                  options={"xatol": 0.05})

        opt_alpha = float(refined.x)
        opt_time  = float(refined.fun)
        sim       = self.pinn.simulate(opt_alpha, velocity)

        return {
            "track":          track_name,
            "track_name":     track["name"],
            "optimal_alpha":  opt_alpha,
            "optimal_Cd":     sim["Cd"],
            "optimal_Cl":     sim["Cl"],
            "laptime_s":      opt_time,
            "laptime_fmt":    self._fmt(opt_time),
            "lap_record_s":   track.get("lap_record_s"),
            "lap_record_fmt": self._fmt(track["lap_record_s"]) if track.get("lap_record_s") else "—",
            "downforce_bias": track.get("downforce_bias", "—"),
            "v_max_ms":       max_straight_speed(sim["Cd"]),
            "alpha_sweep":    alphas.tolist(),
            "time_sweep":     times.tolist(),
        }

    def run_all_tracks(self, velocity: float = 75.0) -> dict:
        return {name: self.optimize_wing_angle(name, velocity) for name in TRACKS}

    @staticmethod
    def _fmt(seconds: float) -> str:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}:{s:06.3f}"
