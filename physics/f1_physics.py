import numpy as np

# ── Physical constants ────────────────────────────────────────────────────────
AIR_DENSITY     = 1.225    # kg/m³ at sea level, 20 °C
AIR_VISCOSITY   = 1.81e-5  # Pa·s dynamic viscosity
GRAVITY         = 9.81     # m/s²

# ── F1 car parameters (2024 regulations baseline) ───────────────────────────
CAR_MASS          = 798.0   # kg
ENGINE_POWER      = 950_000 # W (~950 hp total incl. ERS)
FRONTAL_AREA      = 1.5     # m²
WING_AREA         = 0.65    # m² (combined front+rear reference area)
WING_SPAN         = 2.0     # m  (rear wing span)
WING_CHORD        = WING_AREA / WING_SPAN   # 0.325 m
ASPECT_RATIO      = WING_SPAN**2 / WING_AREA  # ~6.15 effective
OSWALD_EFF        = 0.82    # Oswald efficiency factor
TIRE_FRICTION     = 1.85    # lateral grip coefficient (slick tyres)
ROLLING_RESIST    = 0.013   # rolling resistance coefficient

# Body + floor + wheels drag area EXCLUDING wings (calibrated so Monza top speed ≈ 360 km/h)
BODY_DRAG_AREA    = 1.50    # m²  (Cd_body × A_frontal equivalent)
# Floor/diffuser downforce area EXCLUDING wings (active at all wing angles)
FLOOR_CL_AREA     = 1.10    # m²  (Cl_floor × A_ref equivalent)

# ── Aerodynamic helpers ───────────────────────────────────────────────────────

def reynolds_number(velocity, chord=WING_CHORD):
    return AIR_DENSITY * velocity * chord / AIR_VISCOSITY


def drag_force(Cd, velocity, area=WING_AREA):
    return 0.5 * AIR_DENSITY * velocity**2 * Cd * area


def downforce(Cl, velocity, area=WING_AREA):
    return 0.5 * AIR_DENSITY * velocity**2 * Cl * area


def max_corner_speed(Cl, radius, area=WING_AREA):
    """
    Max cornering speed from force balance including floor downforce:
        m·v²/r = μ·(m·g + 0.5·ρ·v²·(Cl·A_wing + CL_floor_area))
    """
    m   = CAR_MASS
    mu  = TIRE_FRICTION
    rho = AIR_DENSITY

    total_cl_area = Cl * area + FLOOR_CL_AREA
    denom = m / radius - 0.5 * rho * total_cl_area * mu
    if denom <= 0:
        return 85.0  # aerodynamically unlimited — cap at 306 km/h
    v_sq = (mu * m * GRAVITY) / denom
    return float(np.sqrt(max(v_sq, 0.0)))


def max_straight_speed(Cd, area=WING_AREA, n_iter=200):
    """
    Newton solve: ENGINE_POWER = (F_wing_drag + F_body_drag + F_rolling) × v.
    BODY_DRAG_AREA accounts for body, wheels, floor — calibrated to ~100 m/s at Monza.
    """
    P  = ENGINE_POWER
    m  = CAR_MASS
    v  = 75.0

    for _ in range(n_iter):
        total_CdA = Cd * area + BODY_DRAG_AREA
        F_aero    = 0.5 * AIR_DENSITY * v**2 * total_CdA
        F_rolling = ROLLING_RESIST * m * GRAVITY
        P_now     = (F_aero + F_rolling) * v
        dP        = 3 * 0.5 * AIR_DENSITY * total_CdA * v**2 + ROLLING_RESIST * m * GRAVITY
        v        -= (P_now - P) / max(dP, 1.0)
        v         = float(np.clip(v, 10.0, 102.0))  # hard cap ≈ 367 km/h

    return v


def thin_airfoil_cl(alpha_deg, AR=ASPECT_RATIO, cl_factor=2.8):
    """
    Prandtl finite-wing lift: Cl = 2π·sin(α) / (1 + 2/AR).
    cl_factor scales to realistic multi-element F1 wing levels.
    """
    alpha_rad = np.radians(alpha_deg)
    cl_raw = (2 * np.pi * np.sin(alpha_rad)) / (1 + 2 / AR)
    return float(cl_raw * cl_factor)


def thin_airfoil_cd(Cl, AR=ASPECT_RATIO, Cd0=0.028):
    """Lift-induced drag polar: Cd = Cd0 + Cl²/(π·AR·e)."""
    return float(Cd0 + Cl**2 / (np.pi * AR * OSWALD_EFF))
