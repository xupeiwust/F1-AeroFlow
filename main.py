#!/usr/bin/env python3
"""
AeroFlow — Neural F1 Optimizer
================================
Multi-agent aerodynamic design tool powered by Physics-Informed Neural Networks.
Orchestrated by SpoonOS.

Usage examples:
  python main.py                            # full run, all tracks
  python main.py --track monaco             # single track
  python main.py --track monza --track spa  # multiple tracks
  python main.py --image wing.jpg           # analyse a component image
  python main.py --probe 12.5              # probe a single wing angle
  python main.py --quiet                    # suppress rich output
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="aeroflow",
        description="AeroFlow — Neural F1 Aerodynamic Optimizer (SpoonOS)",
    )
    parser.add_argument("--image",  metavar="PATH",    help="Path to component image for geometry extraction")
    parser.add_argument("--track",  metavar="NAME",    action="append", help="Track name to optimise for (repeatable)")
    parser.add_argument("--probe",  metavar="ALPHA",   type=float,      help="Probe a specific wing angle (degrees)")
    parser.add_argument("--all",    action="store_true",                 help="Run all tracks (default behaviour)")
    parser.add_argument("--quiet",  action="store_true",                 help="Suppress verbose output")
    parser.add_argument("--list-tracks", action="store_true",            help="List available tracks and exit")
    args = parser.parse_args()

    if args.list_tracks:
        from tracks.track_data import TRACKS
        print("\nAvailable tracks:")
        for key, val in TRACKS.items():
            print(f"  {key:<14}  {val['name']}")
        print()
        return 0

    # ── Agent initialisation ─────────────────────────────────────────────────
    from spoonos.orchestrator import SpoonOS
    from agents.pinn_agent      import PINNAgent
    from agents.image_analyzer  import ImageAnalyzerAgent
    from agents.laptime_agent   import LaptimeAgent
    from tracks.track_data      import TRACKS

    pinn     = PINNAgent()
    img_agt  = ImageAnalyzerAgent()
    lap_agt  = LaptimeAgent(pinn)

    spoon = SpoonOS()
    spoon.register("pinn",           pinn)
    spoon.register("image_analyzer", img_agt)
    spoon.register("laptime",        lap_agt)

    # ── Track selection ──────────────────────────────────────────────────────
    if args.track:
        bad = [t for t in args.track if t not in TRACKS]
        if bad:
            print(f"Unknown track(s): {bad}. Run with --list-tracks to see options.")
            return 1
        tracks = args.track
    else:
        tracks = list(TRACKS.keys())

    # ── Main pipeline ────────────────────────────────────────────────────────
    results = spoon.run(
        image_path=args.image,
        tracks=tracks,
        verbose=not args.quiet,
    )

    # ── Single-point probe ───────────────────────────────────────────────────
    if args.probe is not None:
        from rich.console import Console
        from rich.panel   import Panel
        c   = Console()
        sim = pinn.simulate(args.probe)
        c.print(Panel(
            f"[cyan]α = {sim['alpha']:.1f}°[/cyan]\n"
            f"Cd = [white]{sim['Cd']:.5f}[/white]\n"
            f"Cl = [white]{sim['Cl']:.4f}[/white]\n"
            f"L/D = [green]{sim['L_over_D']:.2f}[/green]",
            title="Single-Point Probe",
            border_style="cyan",
        ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
