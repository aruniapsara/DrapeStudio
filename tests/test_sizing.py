"""Tests for the size recommendation service and size chart data.

Covers:
- Size chart structure integrity
- calculate_fit_detail — tight / good / slightly loose / loose
- calculate_confidence — score aggregation
- recommend_size with garment_measurements
- recommend_size with garment_size_label
- recommend_size without garment data (pure size-chart lookup)
- _find_best_size — known measurement → known size
- Fit preference adjustments (slim / regular / loose)
- API validation for module=fiton (schema-level)
"""

import pytest

from app.config.size_charts import (
    FIT_SCORES,
    SIZE_ORDER,
    SL_WOMEN_SIZE_CHART,
    FIT_PREFERENCE_EASE,
)
from app.services.sizing import SizeRecommendationService, SizeRecommendationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> SizeRecommendationService:
    return SizeRecommendationService()


# Standard "M" measurements (midpoints of M range)
MEDIUM_CUSTOMER = {
    "bust_cm":   89.0,
    "waist_cm":  71.0,
    "hips_cm":   97.0,
    "height_cm": 163.0,
}

SMALL_CUSTOMER = {
    "bust_cm":   84.0,
    "waist_cm":  66.0,
    "hips_cm":   92.0,
    "height_cm": 158.0,
}

LARGE_CUSTOMER = {
    "bust_cm":   95.0,
    "waist_cm":  77.0,
    "hips_cm":   103.0,
    "height_cm": 168.0,
}


# ---------------------------------------------------------------------------
# 1. Size chart structure
# ---------------------------------------------------------------------------

class TestSizeChartStructure:
    def test_all_size_labels_present(self):
        assert set(SL_WOMEN_SIZE_CHART.keys()) == set(SIZE_ORDER)

    def test_all_sizes_have_three_measurements(self):
        for size, ranges in SL_WOMEN_SIZE_CHART.items():
            assert "bust" in ranges, f"{size} missing bust"
            assert "waist" in ranges, f"{size} missing waist"
            assert "hips" in ranges, f"{size} missing hips"

    def test_all_ranges_are_tuples_of_two_floats(self):
        for size, ranges in SL_WOMEN_SIZE_CHART.items():
            for meas, (lo, hi) in ranges.items():
                assert lo < hi, f"{size}/{meas}: min {lo} >= max {hi}"
                assert isinstance(lo, float), f"{size}/{meas} lo not float"
                assert isinstance(hi, float), f"{size}/{meas} hi not float"

    def test_sizes_are_in_order_by_bust(self):
        """Each successive size should have larger bust range than the previous."""
        bust_mins = [SL_WOMEN_SIZE_CHART[s]["bust"][0] for s in SIZE_ORDER]
        assert bust_mins == sorted(bust_mins), "Bust mins not in ascending order"

    def test_fit_preference_ease_keys(self):
        for pref in ("slim", "regular", "loose"):
            assert pref in FIT_PREFERENCE_EASE
            assert "bust" in FIT_PREFERENCE_EASE[pref]
            assert "waist" in FIT_PREFERENCE_EASE[pref]
            assert "hips" in FIT_PREFERENCE_EASE[pref]

    def test_fit_scores_all_labels_present(self):
        for label in ("good", "slightly loose", "loose", "tight"):
            assert label in FIT_SCORES


# ---------------------------------------------------------------------------
# 2. calculate_fit_detail
# ---------------------------------------------------------------------------

class TestCalculateFitDetail:
    def test_bust_tight_when_garment_smaller(self, svc):
        # garment - customer = -5 → tight
        assert svc.calculate_fit_detail(90.0, 85.0, "bust") == "tight"

    def test_bust_good_when_zero_diff(self, svc):
        assert svc.calculate_fit_detail(88.0, 88.0, "bust") == "good"

    def test_bust_good_when_small_positive_diff(self, svc):
        # diff = 3 → still within 0..4 range → good
        assert svc.calculate_fit_detail(88.0, 91.0, "bust") == "good"

    def test_bust_slightly_loose_when_medium_positive_diff(self, svc):
        # diff = 5 → 4..8 range → slightly loose
        assert svc.calculate_fit_detail(88.0, 93.0, "bust") == "slightly loose"

    def test_bust_loose_when_large_positive_diff(self, svc):
        # diff = 10 → > 8 → loose
        assert svc.calculate_fit_detail(88.0, 98.0, "bust") == "loose"

    def test_waist_tight(self, svc):
        assert svc.calculate_fit_detail(72.0, 68.0, "waist") == "tight"

    def test_waist_good(self, svc):
        assert svc.calculate_fit_detail(70.0, 72.0, "waist") == "good"

    def test_hips_slightly_loose(self, svc):
        # diff = 6 → slightly loose
        assert svc.calculate_fit_detail(95.0, 101.0, "hips") == "slightly loose"

    def test_length_tight_when_much_shorter(self, svc):
        # diff = -8 → < -5 → tight (garment too short)
        assert svc.calculate_fit_detail(100.0, 92.0, "length") == "tight"

    def test_length_good(self, svc):
        # diff = 0 → good
        assert svc.calculate_fit_detail(100.0, 100.0, "length") == "good"

    def test_length_loose_when_much_longer(self, svc):
        # diff = 15 → > 10 → loose
        assert svc.calculate_fit_detail(80.0, 95.0, "length") == "loose"

    def test_boundary_bust_tight_minus_two(self, svc):
        # diff exactly = -2.0 → tight (< -2 is tight, but -2 itself is not < -2)
        # diff = -2 is NOT < -2, so it falls into "good"
        assert svc.calculate_fit_detail(90.0, 88.0, "bust") == "good"

    def test_boundary_bust_good_at_four(self, svc):
        # diff exactly = 4.0 → NOT < 4, falls into slightly loose
        assert svc.calculate_fit_detail(88.0, 92.0, "bust") == "slightly loose"


# ---------------------------------------------------------------------------
# 3. calculate_confidence
# ---------------------------------------------------------------------------

class TestCalculateConfidence:
    def test_all_good_returns_100(self, svc):
        details = {"bust": "good", "waist": "good", "hips": "good"}
        assert svc.calculate_confidence(details) == 100.0

    def test_all_tight_returns_20(self, svc):
        details = {"bust": "tight", "waist": "tight", "hips": "tight"}
        assert svc.calculate_confidence(details) == 20.0

    def test_all_loose_returns_40(self, svc):
        details = {"bust": "loose", "waist": "loose", "hips": "loose"}
        assert svc.calculate_confidence(details) == 40.0

    def test_mixed_averages_correctly(self, svc):
        # good=100, slightly loose=70 → average = 85
        details = {"bust": "good", "waist": "slightly loose"}
        assert svc.calculate_confidence(details) == 85.0

    def test_empty_returns_zero(self, svc):
        assert svc.calculate_confidence({}) == 0.0

    def test_single_measurement_good(self, svc):
        assert svc.calculate_confidence({"bust": "good"}) == 100.0

    def test_confidence_above_80_for_all_good(self, svc):
        details = {"bust": "good", "waist": "good", "hips": "good", "length": "good"}
        assert svc.calculate_confidence(details) >= 80.0


# ---------------------------------------------------------------------------
# 4. recommend_size — size label lookup
# ---------------------------------------------------------------------------

class TestRecommendSizeByLabel:
    def test_medium_customer_in_medium_garment_good_confidence(self, svc):
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_size_label="M",
        )
        assert isinstance(result, SizeRecommendationResult)
        assert result.recommended_size == "M"
        assert result.fit_confidence >= 70.0

    def test_small_customer_in_medium_garment_lower_confidence(self, svc):
        result = svc.recommend_size(
            customer_measurements=SMALL_CUSTOMER,
            garment_size_label="M",
        )
        # Confidence may be lower since customer is smaller than M
        assert isinstance(result, SizeRecommendationResult)
        assert result.fit_confidence >= 0.0

    def test_fit_details_contain_expected_keys(self, svc):
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_size_label="M",
        )
        for key in ("bust", "waist", "hips"):
            assert key in result.fit_details

    def test_fit_details_values_are_valid_labels(self, svc):
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_size_label="L",
        )
        valid = {"tight", "good", "slightly loose", "loose"}
        for v in result.fit_details.values():
            assert v in valid, f"Unexpected fit label: {v!r}"

    def test_xs_customer_does_not_recommend_xxl(self, svc):
        xs_customer = {"bust_cm": 79.0, "waist_cm": 61.0, "hips_cm": 87.0, "height_cm": 155.0}
        result = svc.recommend_size(
            customer_measurements=xs_customer,
            garment_size_label="XXL",
        )
        # Confidence should be low; recommended may be re-evaluated to XS
        assert result.fit_confidence < 70.0 or result.recommended_size == "XS"

    def test_invalid_size_label_falls_back(self, svc):
        """Unknown label → Mode 3 (pure size-chart) should still return a result."""
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_size_label="INVALID",  # not in chart
        )
        # Falls through to _find_best_size
        assert result.recommended_size in SIZE_ORDER


# ---------------------------------------------------------------------------
# 5. recommend_size — garment measurements provided
# ---------------------------------------------------------------------------

class TestRecommendSizeByMeasurements:
    def test_exact_match_returns_high_confidence(self, svc):
        # Garment dims = customer dims (perfect fit at diff=0)
        garment = {
            "bust_cm":  89.0,
            "waist_cm": 71.0,
            "hips_cm":  97.0,
        }
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_measurements=garment,
        )
        assert result.fit_confidence >= 80.0
        for v in result.fit_details.values():
            assert v == "good"

    def test_tight_garment_returns_tight_details(self, svc):
        garment = {
            "bust_cm":  82.0,  # 7 cm smaller than customer → tight
            "waist_cm": 65.0,  # 6 cm smaller → tight
            "hips_cm":  90.0,  # 7 cm smaller → tight
        }
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_measurements=garment,
        )
        for key in ("bust", "waist", "hips"):
            assert result.fit_details.get(key) == "tight", f"{key} should be tight"

    def test_loose_garment_returns_loose_details(self, svc):
        garment = {
            "bust_cm":  102.0,  # 13 cm bigger → loose
            "waist_cm":  84.0,  # 13 cm bigger → loose
            "hips_cm":  110.0,  # 13 cm bigger → loose
        }
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_measurements=garment,
        )
        for key in ("bust", "waist", "hips"):
            assert result.fit_details.get(key) == "loose", f"{key} should be loose"

    def test_length_included_when_provided(self, svc):
        garment = {
            "bust_cm":  89.0,
            "waist_cm": 71.0,
            "hips_cm":  97.0,
            "length_cm": 101.0,  # 163 * 0.62 = ~101 → good
        }
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_measurements=garment,
        )
        assert "length" in result.fit_details

    def test_partial_garment_measurements_still_works(self, svc):
        garment = {"bust_cm": 89.0}  # only bust provided
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            garment_measurements=garment,
        )
        assert "bust" in result.fit_details
        assert result.recommended_size in SIZE_ORDER


# ---------------------------------------------------------------------------
# 6. recommend_size — no garment data (pure size-chart lookup)
# ---------------------------------------------------------------------------

class TestRecommendSizePureChart:
    def test_medium_measurements_recommend_m(self, svc):
        result = svc.recommend_size(customer_measurements=MEDIUM_CUSTOMER)
        assert result.recommended_size == "M"

    def test_small_measurements_recommend_s(self, svc):
        result = svc.recommend_size(customer_measurements=SMALL_CUSTOMER)
        assert result.recommended_size in ("XS", "S")

    def test_large_measurements_recommend_l(self, svc):
        result = svc.recommend_size(customer_measurements=LARGE_CUSTOMER)
        assert result.recommended_size in ("L", "XL")

    def test_result_has_fit_details(self, svc):
        result = svc.recommend_size(customer_measurements=MEDIUM_CUSTOMER)
        assert len(result.fit_details) > 0

    def test_confidence_reasonable_for_good_fit(self, svc):
        result = svc.recommend_size(customer_measurements=MEDIUM_CUSTOMER)
        assert result.fit_confidence >= 70.0


# ---------------------------------------------------------------------------
# 7. Fit preference adjustments
# ---------------------------------------------------------------------------

class TestFitPreference:
    def test_slim_may_recommend_smaller_size(self, svc):
        # Customer at the top of S range; slim pref should still recommend S or XS
        borderline_s = {"bust_cm": 85.5, "waist_cm": 67.5, "hips_cm": 93.5, "height_cm": 160.0}
        result_regular = svc.recommend_size(borderline_s, fit_preference="regular")
        result_slim = svc.recommend_size(borderline_s, fit_preference="slim")
        # slim applies -2 ease → pushes effective size down; result <= regular
        slim_idx = SIZE_ORDER.index(result_slim.recommended_size)
        regular_idx = SIZE_ORDER.index(result_regular.recommended_size)
        assert slim_idx <= regular_idx

    def test_loose_may_recommend_larger_size(self, svc):
        borderline_s = {"bust_cm": 85.5, "waist_cm": 67.5, "hips_cm": 93.5, "height_cm": 160.0}
        result_regular = svc.recommend_size(borderline_s, fit_preference="regular")
        result_loose = svc.recommend_size(borderline_s, fit_preference="loose")
        loose_idx = SIZE_ORDER.index(result_loose.recommended_size)
        regular_idx = SIZE_ORDER.index(result_regular.recommended_size)
        assert loose_idx >= regular_idx

    def test_unknown_fit_preference_defaults_to_regular(self, svc):
        result = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            fit_preference="unknown_pref",
        )
        result_regular = svc.recommend_size(
            customer_measurements=MEDIUM_CUSTOMER,
            fit_preference="regular",
        )
        assert result.recommended_size == result_regular.recommended_size


# ---------------------------------------------------------------------------
# 8. API schema validation — FitonParamsCreate
# ---------------------------------------------------------------------------

class TestFitonParamsSchema:
    def test_valid_with_size_label(self):
        from app.schemas.generation import FitonParamsCreate, CustomerMeasurements

        fp = FitonParamsCreate(
            customer_photo_url="local://uploads/session1/customer.jpg",
            customer_measurements=CustomerMeasurements(
                bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
            ),
            garment_size_label="M",
        )
        assert fp.garment_size_label == "M"
        assert fp.fit_preference == "regular"

    def test_valid_with_garment_measurements(self):
        from app.schemas.generation import FitonParamsCreate, CustomerMeasurements, GarmentMeasurements

        fp = FitonParamsCreate(
            customer_photo_url="local://uploads/session1/customer.jpg",
            customer_measurements=CustomerMeasurements(
                bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
            ),
            garment_measurements=GarmentMeasurements(
                bust_cm=91.0, waist_cm=73.0, hips_cm=99.0
            ),
        )
        assert fp.garment_measurements is not None

    def test_invalid_missing_both_garment_fields(self):
        from pydantic import ValidationError
        from app.schemas.generation import FitonParamsCreate, CustomerMeasurements

        with pytest.raises(ValidationError) as exc_info:
            FitonParamsCreate(
                customer_photo_url="local://uploads/session1/customer.jpg",
                customer_measurements=CustomerMeasurements(
                    bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
                ),
                # Neither garment_measurements nor garment_size_label
            )
        assert "garment_measurements or garment_size_label" in str(exc_info.value)

    def test_invalid_bust_too_low(self):
        from pydantic import ValidationError
        from app.schemas.generation import CustomerMeasurements

        with pytest.raises(ValidationError):
            CustomerMeasurements(bust_cm=30.0, waist_cm=70.0, hips_cm=96.0)

    def test_invalid_size_label(self):
        from pydantic import ValidationError
        from app.schemas.generation import FitonParamsCreate, CustomerMeasurements

        with pytest.raises(ValidationError):
            FitonParamsCreate(
                customer_photo_url="local://uploads/session1/customer.jpg",
                customer_measurements=CustomerMeasurements(
                    bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
                ),
                garment_size_label="XXXXXXL",  # not a valid literal
            )

    def test_fit_preference_defaults_to_regular(self):
        from app.schemas.generation import FitonParamsCreate, CustomerMeasurements

        fp = FitonParamsCreate(
            customer_photo_url="local://uploads/session1/customer.jpg",
            customer_measurements=CustomerMeasurements(
                bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
            ),
            garment_size_label="M",
        )
        assert fp.fit_preference == "regular"

    def test_module_fiton_in_create_generation_request(self):
        from app.schemas.generation import (
            CreateGenerationRequest,
            FitonParamsCreate,
            CustomerMeasurements,
        )

        req = CreateGenerationRequest(
            module="fiton",
            garment_images=["local://uploads/session1/garment.jpg"],
            fiton_params=FitonParamsCreate(
                customer_photo_url="local://uploads/session1/customer.jpg",
                customer_measurements=CustomerMeasurements(
                    bust_cm=88.0, waist_cm=70.0, hips_cm=96.0
                ),
                garment_size_label="M",
            ),
        )
        assert req.module == "fiton"

    def test_module_fiton_requires_fiton_params(self):
        from pydantic import ValidationError
        from app.schemas.generation import CreateGenerationRequest

        with pytest.raises(ValidationError) as exc_info:
            CreateGenerationRequest(
                module="fiton",
                garment_images=["local://uploads/session1/garment.jpg"],
                # fiton_params missing
            )
        assert "fiton_params" in str(exc_info.value)
