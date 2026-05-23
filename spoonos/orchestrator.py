import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box


class SpoonOS:
    """
    Multi-agent orchestrator — coordinates the PINN, ImageAnalyzer,
    and LaptimeAgent in a sequential pipeline and renders rich output.
    """

    def __init__(self):
        self.console = Console()
        self.agents: dict = {}
        self.results: dict = {}

    def register(self, name: str, agent) -> None:
        self.agents[name] = agent

    # ── Pipeline entry-point ─────────────────────────────────────────────────

    def run(self, image_path: str | None = None,
            tracks: list[str] | None = None,
            verbose: bool = True) -> dict:

        t0 = time.perf_counter()

        if verbose:
            self._banner()

        self._run_image_analysis(image_path, verbose)
        self._run_pinn_training(verbose)
        self._run_aero_scan(verbose)
        self._run_laptime_opt(tracks, verbose)

        elapsed = time.perf_counter() - t0
        if verbose:
            self._summary(elapsed)

        return self.results

    # ── Phase 1: Image analysis ───────────────────────────────────────────────

    def _run_image_analysis(self, image_path, verbose):
        agent = self.agents.get("image_analyzer")
        if not agent:
            return

        if verbose:
            self.console.rule("[bold yellow]Agent 1 — Image Analyzer[/bold yellow]")

        with self.console.status("[yellow]Extracting component geometry…[/yellow]", spinner="dots"):
            params = agent.analyze(image_path)

        self.results["geometry"] = params

        if verbose:
            t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            t.add_column("key",   style="dim cyan", no_wrap=True)
            t.add_column("value", style="white")
            t.add_row("Component",   params["component_type"].replace("_", " ").title())
            t.add_row("Wing angle",  f"{params['wing_angle_deg']:.1f}°")
            t.add_row("Aspect ratio",f"{params['aspect_ratio']:.2f}")
            t.add_row("Chord",       f"{params['chord_m']*100:.0f} cm")
            t.add_row("Source",      params["source"])
            if params["confidence"] > 0:
                t.add_row("Confidence", f"{params['confidence']*100:.0f}%")
            self.console.print(t)

    # ── Phase 2: PINN training ────────────────────────────────────────────────

    def _run_pinn_training(self, verbose):
        agent = self.agents.get("pinn")
        if not agent:
            return

        if verbose:
            self.console.rule("[bold yellow]Agent 2 — PINN Simulator[/bold yellow]")

        epochs = 500

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=self.console,
            transient=True,
        ) as prog:
            task = prog.add_task("[cyan]Training PINN on physics-derived data…", total=epochs)

            losses: list[float] = []

            def cb(epoch, loss):
                prog.update(task, advance=epochs // 8)
                losses.append(loss)

            history = agent.train(epochs=epochs, callback=cb)

        self.results["training"] = {
            "epochs":      epochs,
            "final_loss":  history[-1] if history else None,
        }

        if verbose:
            fl  = history[-1] if history else float("nan")
            tag = "[green]converged[/green]" if fl < 0.15 else "[yellow]trained[/yellow]"
            self.console.print(
                f"  [dim]Epochs:[/dim] {epochs}   "
                f"[dim]Final loss:[/dim] {fl:.5f}   "
                f"[dim]Status:[/dim] {tag}"
            )

    # ── Phase 3: Aerodynamic scan ─────────────────────────────────────────────

    def _run_aero_scan(self, verbose):
        agent = self.agents.get("pinn")
        if not agent:
            return

        if verbose:
            self.console.rule("[bold yellow]Agent 2b — Aerodynamic Scan[/bold yellow]")

        with self.console.status("[cyan]Scanning α from −5° to 25°…[/cyan]", spinner="dots"):
            scan = agent.scan_alpha(n_points=20)

        self.results["aero_scan"] = scan

        if verbose:
            t = Table(box=box.SIMPLE, padding=(0, 3))
            t.add_column("α (°)",  justify="right", style="cyan")
            t.add_column("Cd",     justify="right")
            t.add_column("Cl",     justify="right")
            t.add_column("L/D",    justify="right")

            best_ld = max(r["L_over_D"] for r in scan)
            for r in scan[::2]:  # every other point for readability
                ld  = r["L_over_D"]
                style = "bold green" if abs(ld - best_ld) < 0.01 else "white"
                t.add_row(
                    f"{r['alpha']:+.1f}",
                    f"{r['Cd']:.4f}",
                    f"{r['Cl']:.3f}",
                    f"[{style}]{ld:.2f}[/{style}]",
                )
            self.console.print(t)

    # ── Phase 4: Lap-time optimisation ────────────────────────────────────────

    def _run_laptime_opt(self, tracks, verbose):
        agent = self.agents.get("laptime")
        if not agent:
            return

        if verbose:
            self.console.rule("[bold yellow]Agent 3 — Laptime Optimizer[/bold yellow]")

        from tracks.track_data import TRACKS as ALL_TRACKS
        track_list = tracks or list(ALL_TRACKS.keys())

        opt_results: dict = {}
        for name in track_list:
            display = ALL_TRACKS[name]["name"] if name in ALL_TRACKS else name
            with self.console.status(
                f"[cyan]Optimising setup for {display}…[/cyan]", spinner="dots"
            ):
                opt_results[name] = agent.optimize_wing_angle(name)

        self.results["laptime"] = opt_results

        if verbose:
            t = Table(
                title="[bold]Optimal Wing Setup by Circuit[/bold]",
                box=box.ROUNDED,
                border_style="cyan",
                show_lines=False,
            )
            t.add_column("Circuit",       style="white",  no_wrap=True)
            t.add_column("Wing α",        justify="center", style="cyan")
            t.add_column("Cd",            justify="right")
            t.add_column("Cl",            justify="right")
            t.add_column("v_max",         justify="right", style="dim")
            t.add_column("Est. laptime",  justify="right", style="green")
            t.add_column("Bias",          justify="center", style="yellow")

            for name, res in opt_results.items():
                if res:
                    v_kmh = res.get("v_max_ms", 0) * 3.6
                    t.add_row(
                        res["track_name"],
                        f"{res['optimal_alpha']:.1f}°",
                        f"{res['optimal_Cd']:.4f}",
                        f"{res['optimal_Cl']:.3f}",
                        f"{v_kmh:.0f} km/h",
                        res["laptime_fmt"],
                        res["downforce_bias"].upper(),
                    )
            self.console.print(t)

    # ── Summary panel ─────────────────────────────────────────────────────────

    def _summary(self, elapsed: float) -> None:
        scan = self.results.get("aero_scan", [])
        lines = []

        if scan:
            best = max(scan, key=lambda r: r["L_over_D"])
            lines.append(
                f"[bold white]Best L/D:[/bold white]  "
                f"{best['L_over_D']:.2f}  at  α = {best['alpha']:.1f}°  "
                f"(Cd={best['Cd']:.4f}, Cl={best['Cl']:.3f})"
            )

        speedup = int(43_200 / elapsed)
        lines.append(
            f"[bold white]Wall time:[/bold white]  {elapsed:.2f} s  "
            f"[dim]vs ~12 h for full CFD  →  ≈{speedup:,}× speedup[/dim]"
        )

        laptime_res = self.results.get("laptime", {})
        if laptime_res:
            best_track = min(
                (r for r in laptime_res.values() if r),
                key=lambda r: r["optimal_Cl"] / max(r["optimal_Cd"], 1e-9),
                default=None,
            )
            if best_track:
                lines.append(
                    f"[bold white]Top aero efficiency:[/bold white]  "
                    f"{best_track['track_name']}"
                )

        self.console.print()
        self.console.print(Panel(
            "\n".join(lines),
            title="[bold cyan]SpoonOS — Run Complete[/bold cyan]",
            border_style="green",
            padding=(1, 3),
        ))

    # ── Banner ────────────────────────────────────────────────────────────────

    def _banner(self) -> None:
        self.console.print()
        self.console.print(Panel.fit(
            "[bold cyan]AeroFlow[/bold cyan]  [white]Neural F1 Optimizer[/white]\n"
            "[dim]SpoonOS  ·  Multi-Agent Orchestration  ·  Physics-Informed Neural Networks[/dim]",
            border_style="bright_cyan",
            padding=(1, 6),
        ))
        self.console.print()
