"""Size recommendation service for DrapeStudio Virtual Fit-On.

Compares customer body measurements against garment measurements (or a Sri Lankan
size-chart lookup) to recommend the best-fitting size and provide per-measurement
fit assessments (tight / good / slightly loose / loose) with an overall confidence
score (0–100%).

Usage::

    from app.services.sizing import SizeRecommendationService

    svc = SizeRecommendationService()
    result = svc.recommend_size(
        customer_measurements={"bust_cm": 88, "waist_cm": 70, "hips_cm": 96, "height_cm": 163},
        garment_size_label="M",
        fit_preference="regular",
    )
    print(result.recommended_size)   # e.g. "M"
    print(result.fit_confidence)     # e.g. 92.5
    print(result.fit_details)        # e.g. {"bust": "good", "waist": "good", "hips": "good"}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.config.size_charts import (
    FIT_PREFERENCE_EASE,
    FIT_SCORES,
    SIZE_ORDER,
    SL_WOMEN_SIZE_CHART,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SizeRecommendationResult:
    """Output of the size recommendation algorithm."""

    recommended_size: str
    """The recommended size label (XS / S / M / L / XL / XXL / 3XL)."""

    fit_confidence: float
    """Overall fit confidence, 0–100%. Higher = better fit for the recommended size."""

    fit_details: dict[str, str] = field(default_factory=dict)
    """Per-measurement fit labels: bust, waist, hips, length.
    Values: 'tight' | 'good' | 'slightly loose' | 'loose'
    """


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SizeRecommendationService:
    """Recommends garment sizes and assesses per-measurement fit quality.

    Supports three input modes:
    1. garment_measurements provided → compare customer to garment dims directly.
    2. garment_size_label provided   → look up size chart midpoints, then compare.
    3. Neither provided              → find best size from chart only.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend_size(
        self,
        customer_measurements: dict,
        garment_measurements: Optional[dict] = None,
        garment_size_label: Optional[str] = None,
        fit_preference: str = "regular",
    ) -> SizeRecommendationResult:
        """Calculate recommended size and per-measurement fit assessment.

        Args:
            customer_measurements: Keys: bust_cm, waist_cm, hips_cm, height_cm,
                                   shoulder_width_cm (all optional but at least
                                   one of bust/waist/hips should be present).
            garment_measurements:  Keys: bust_cm, waist_cm, hips_cm, length_cm,
                                   shoulder_width_cm.  Uses actual garment dims.
            garment_size_label:    XS | S | M | L | XL | XXL | 3XL.
                                   Used when garment_measurements is not given.
            fit_preference:        "slim" | "regular" | "loose".

        Returns:
            SizeRecommendationResult with recommended_size, fit_confidence, fit_details.
        """
        ease = FIT_PREFERENCE_EASE.get(fit_preference, FIT_PREFERENCE_EASE["regular"])
        adjusted = self._apply_ease(customer_measurements, ease)

        # ── Mode 1: actual garment measurements provided ──────────────────
        if garment_measurements:
            fit_details = self._compare_to_garment_dims(adjusted, customer_measurements, garment_measurements)
            confidence = self.calculate_confidence(fit_details)
            recommended = self._find_best_size(customer_measurements, fit_preference)
            return SizeRecommendationResult(
                recommended_size=recommended,
                fit_confidence=confidence,
                fit_details=fit_details,
            )

        # ── Mode 2: size label → look up chart midpoints ──────────────────
        if garment_size_label and garment_size_label in SL_WOMEN_SIZE_CHART:
            garment_mid = self._size_midpoints(garment_size_label)
            fit_details = self._compare_to_midpoints(adjusted, garment_mid)
            confidence = self.calculate_confidence(fit_details)

            # Keep the stated size if confidence is reasonable; otherwise re-recommend.
            if confidence >= 70.0:
                recommended = garment_size_label
            else:
                recommended = self._find_best_size(customer_measurements, fit_preference)

            return SizeRecommendationResult(
                recommended_size=recommended,
                fit_confidence=confidence,
                fit_details=fit_details,
            )

        # ── Mode 3: no garment dims → pure size-chart lookup ─────────────
        recommended = self._find_best_size(customer_measurements, fit_preference)
        if recommended in SL_WOMEN_SIZE_CHART:
            garment_mid = self._size_midpoints(recommended)
            fit_details = self._compare_to_midpoints(adjusted, garment_mid)
            confidence = self.calculate_confidence(fit_details)
        else:
            fit_details = {}
            confidence = 0.0

        return SizeRecommendationResult(
            recommended_size=recommended,
            fit_confidence=confidence,
            fit_details=fit_details,
        )

    def calculate_fit_detail(
        self, customer_cm: float, garment_cm: float, measurement_name: str
    ) -> str:
        """Compare a single measurement and return a fit label.

        The diff is ``garment_cm - customer_cm``:
        - Negative → garment smaller than body → **tight**.
        - Small positive → good fit range.
        - Large positive → garment much bigger → **loose**.

        Args:
            customer_cm:      Customer's body measurement.
            garment_cm:       Garment dimension for the same measurement.
            measurement_name: "bust" | "waist" | "hips" | "chest" | "length" | other.

        Returns:
            One of: "tight", "good", "slightly loose", "loose".
        """
        diff = garment_cm - customer_cm

        if measurement_name in ("bust", "waist", "hips", "chest"):
            if diff < -2.0:
                return "tight"
            elif diff < 4.0:
                return "good"
            elif diff < 8.0:
                return "slightly loose"
            else:
                return "loose"

        elif measurement_name == "length":
            if diff < -5.0:
                return "tight"       # garment too short
            elif diff < 3.0:
                return "good"
            elif diff < 10.0:
                return "slightly loose"
            else:
                return "loose"       # garment too long

        else:
            # Generic fallback
            if diff < -2.0:
                return "tight"
            elif diff < 6.0:
                return "good"
            else:
                return "loose"

    def calculate_confidence(self, fit_details: dict) -> float:
        """Compute overall fit confidence (0–100%) from per-measurement labels.

        Each measurement contributes equally.  Scores per label:
        - good:           100
        - slightly loose:  70
        - loose:           40
        - tight:           20

        Returns:
            Rounded float, e.g. 90.0 or 76.7.
        """
        if not fit_details:
            return 0.0

        total = sum(FIT_SCORES.get(label, 50.0) for label in fit_details.values())
        return round(total / len(fit_details), 1)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_ease(self, customer_measurements: dict, ease: dict) -> dict:
        """Return adjusted bust/waist/hips after applying fit-preference ease."""
        return {
            "bust":  customer_measurements.get("bust_cm", 0.0) + ease.get("bust", 0.0),
            "waist": customer_measurements.get("waist_cm", 0.0) + ease.get("waist", 0.0),
            "hips":  customer_measurements.get("hips_cm", 0.0) + ease.get("hips", 0.0),
        }

    def _size_midpoints(self, size_label: str) -> dict:
        """Return the midpoint (cm) of each measurement range for a size."""
        ranges = SL_WOMEN_SIZE_CHART[size_label]
        return {meas: (lo + hi) / 2.0 for meas, (lo, hi) in ranges.items()}

    def _compare_to_midpoints(self, adjusted_customer: dict, garment_mid: dict) -> dict:
        """Build fit_details by comparing adjusted customer to size-chart midpoints."""
        fit_details: dict[str, str] = {}
        for meas_name in ("bust", "waist", "hips"):
            g_cm = garment_mid.get(meas_name)
            c_cm = adjusted_customer.get(meas_name, 0.0)
            if g_cm is not None and c_cm > 0.0:
                fit_details[meas_name] = self.calculate_fit_detail(c_cm, g_cm, meas_name)
        return fit_details

    def _compare_to_garment_dims(
        self, adjusted_customer: dict, customer_measurements: dict, garment_measurements: dict
    ) -> dict:
        """Build fit_details by comparing against explicit garment measurements."""
        fit_details: dict[str, str] = {}

        for meas_name in ("bust", "waist", "hips"):
            g_cm = garment_measurements.get(f"{meas_name}_cm")
            c_cm = adjusted_customer.get(meas_name, 0.0)
            if g_cm is not None and c_cm > 0.0:
                fit_details[meas_name] = self.calculate_fit_detail(c_cm, g_cm, meas_name)

        # Chest (men's garments may use 'chest_cm' instead of 'bust_cm')
        if "chest_cm" in garment_measurements and "bust" not in fit_details:
            g_cm = garment_measurements["chest_cm"]
            c_cm = adjusted_customer.get("bust", 0.0)
            if c_cm > 0.0:
                fit_details["chest"] = self.calculate_fit_detail(c_cm, g_cm, "chest")

        # Length
        length_cm = garment_measurements.get("length_cm")
        if length_cm is not None:
            height_cm = customer_measurements.get("height_cm", 160.0)
            fit_details["length"] = self._assess_length(height_cm, length_cm)

        return fit_details

    def _find_best_size(
        self, customer_measurements: dict, fit_preference: str = "regular"
    ) -> str:
        """Score every size in the chart and return the best match.

        Scoring: for each of bust/waist/hips, a measurement that falls inside
        the size range earns 3 points.  Measurements outside the range lose
        0.5 points per cm of deviation, floored at 0.
        """
        ease = FIT_PREFERENCE_EASE.get(fit_preference, FIT_PREFERENCE_EASE["regular"])

        bust  = customer_measurements.get("bust_cm",  0.0) + ease.get("bust",  0.0)
        waist = customer_measurements.get("waist_cm", 0.0) + ease.get("waist", 0.0)
        hips  = customer_measurements.get("hips_cm",  0.0) + ease.get("hips",  0.0)

        best_size = "M"
        best_score: float = -1.0

        for size in SIZE_ORDER:
            ranges = SL_WOMEN_SIZE_CHART[size]
            score = 0.0
            count = 0

            if bust > 0.0:
                b_min, b_max = ranges["bust"]
                if b_min <= bust <= b_max:
                    score += 3.0
                elif bust < b_min:
                    score += max(0.0, 3.0 - (b_min - bust) * 0.5)
                else:
                    score += max(0.0, 3.0 - (bust - b_max) * 0.5)
                count += 1

            if waist > 0.0:
                w_min, w_max = ranges["waist"]
                if w_min <= waist <= w_max:
                    score += 3.0
                elif waist < w_min:
                    score += max(0.0, 3.0 - (w_min - waist) * 0.5)
                else:
                    score += max(0.0, 3.0 - (waist - w_max) * 0.5)
                count += 1

            if hips > 0.0:
                h_min, h_max = ranges["hips"]
                if h_min <= hips <= h_max:
                    score += 3.0
                elif hips < h_min:
                    score += max(0.0, 3.0 - (h_min - hips) * 0.5)
                else:
                    score += max(0.0, 3.0 - (hips - h_max) * 0.5)
                count += 1

            if count == 0:
                continue

            normalised = score / count
            if normalised > best_score:
                best_score = normalised
                best_size = size

        return best_size

    def _assess_length(self, customer_height: float, garment_length_cm: float) -> str:
        """Heuristic length fit: compares garment length to ~62% of customer height."""
        expected = customer_height * 0.62
        diff = garment_length_cm - expected

        if diff < -10.0:
            return "tight"          # much shorter than expected
        elif diff < 5.0:
            return "good"
        elif diff < 15.0:
            return "slightly loose"
        else:
            return "loose"          # much longer than expected


# ---------------------------------------------------------------------------
# Module-level singleton for convenience
# ---------------------------------------------------------------------------
sizing_service = SizeRecommendationService()
