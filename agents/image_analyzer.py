import os
import numpy as np

from physics.f1_physics import ASPECT_RATIO, WING_CHORD, WING_SPAN


_DEFAULTS = {
    "component_type":    "rear_wing",
    "wing_angle_deg":    8.0,
    "aspect_ratio":      ASPECT_RATIO,
    "chord_m":           WING_CHORD,
    "span_m":            WING_SPAN,
    "confidence":        0.0,
    "source":            "defaults",
}


class ImageAnalyzerAgent:
    """
    Extracts geometric parameters from a wing/component image.
    Uses PIL + NumPy edge analysis (no heavy CV dependency).
    Falls back to F1 defaults when no image is supplied.
    """

    def analyze(self, image_path: str | None = None) -> dict:
        if image_path and os.path.isfile(image_path):
            return self._analyze_image(image_path)
        result = dict(_DEFAULTS)
        result["source"] = "defaults (no image)"
        return result

    # ── Internal ──────────────────────────────────────────────────────────────

    def _analyze_image(self, path: str) -> dict:
        try:
            from PIL import Image, ImageFilter

            img  = Image.open(path).convert("L").resize((512, 512))
            arr  = np.array(img, dtype=np.float32)

            # Sobel edge magnitude
            sx = np.gradient(arr, axis=1)
            sy = np.gradient(arr, axis=0)
            mag = np.hypot(sx, sy)

            threshold = np.percentile(mag, 88)
            ys, xs = np.where(mag > threshold)

            if len(xs) > 20:
                coeffs = np.polyfit(xs, ys, 1)
                slope  = coeffs[0]
                raw_angle = float(np.degrees(np.arctan(abs(slope))))
                # Map to sensible wing-angle range
                wing_angle = float(np.clip(raw_angle * 0.6, 0.5, 22.0))
            else:
                wing_angle = _DEFAULTS["wing_angle_deg"]

            h, w = arr.shape
            ar   = float(np.clip((w / max(h, 1)) * 2.0, 2.0, 9.0))
            span = float(ar * WING_CHORD)

            return {
                "component_type":  self._classify(arr),
                "wing_angle_deg":  wing_angle,
                "aspect_ratio":    ar,
                "chord_m":         WING_CHORD,
                "span_m":          span,
                "confidence":      0.78,
                "source":          f"image:{os.path.basename(path)}",
            }

        except Exception as exc:
            result = dict(_DEFAULTS)
            result["source"]  = f"defaults (image error: {exc})"
            return result

    @staticmethod
    def _classify(arr: np.ndarray) -> str:
        h, w = arr.shape
        if w > 3.5 * h:
            return "rear_wing"
        if h > 1.5 * w:
            return "front_wing_element"
        return "diffuser"
