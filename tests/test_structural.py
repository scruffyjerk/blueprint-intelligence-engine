"""
Tests for StructuralCalculator — Framing (Ticket 1)

Scenarios:
  - 1200 sqft SFR  (~111 m², perimeter ~44 m / 144 ft)
  - 2000 sqft SFR  (~186 m², perimeter ~57 m / 188 ft)
"""

import pytest
from src.calculator.structural_calculator import StructuralCalculator, M_TO_FT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SQF_TO_M2 = 1 / (M_TO_FT ** 2)
FT_TO_M = 1 / M_TO_FT

# Approximate perimeters for simple rectangular SFRs
# 1200 sqft ~ 30×40 ft  → perimeter 140 ft ~ 42.7 m
SFR_1200 = dict(
    floor_area_m2=1200 * SQF_TO_M2,
    perimeter_m=140 * FT_TO_M,
    perimeter_ft=140,
    floor_area_sqft=1200,
)

# 2000 sqft ~ 40×50 ft → perimeter 180 ft ~ 54.9 m
SFR_2000 = dict(
    floor_area_m2=2000 * SQF_TO_M2,
    perimeter_m=180 * FT_TO_M,
    perimeter_ft=180,
    floor_area_sqft=2000,
)


def calc_expected_exterior_studs(perimeter_ft: float, stories: int = 1) -> int:
    """Mirror the spec formula."""
    return round((perimeter_ft / (16 / 12)) * stories)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def calc_default():
    return StructuralCalculator()


@pytest.fixture
def calc_2story():
    return StructuralCalculator(stories=2)


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------

class TestCalculateFramingReturnShape:
    def test_returns_four_keys(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        assert set(result.keys()) == {
            "exterior_studs",
            "interior_partition_studs",
            "top_bottom_plates_boards",
            "header_stock_lf",
        }

    def test_each_item_has_required_fields(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        required = {
            "name", "quantity_metric", "unit_metric",
            "quantity_imperial", "unit_imperial",
            "category", "confidence", "note",
        }
        for key, item in result.items():
            assert required.issubset(item.keys()), f"Missing fields in {key}"

    def test_category_and_confidence_tags(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        for key, item in result.items():
            assert item["category"] == "structural", f"{key} wrong category"
            assert item["confidence"] == "estimated", f"{key} wrong confidence"


# ---------------------------------------------------------------------------
# 1200 sqft SFR — value checks
# ---------------------------------------------------------------------------

class TestSFR1200:
    def test_exterior_studs_count(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        expected = calc_expected_exterior_studs(SFR_1200["perimeter_ft"])
        actual = result["exterior_studs"]["quantity_imperial"]
        # Allow ±5 for rounding across unit conversions
        assert abs(actual - expected) <= 5, f"Expected ~{expected}, got {actual}"

    def test_interior_studs_roughly_40pct_of_exterior(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        ext = result["exterior_studs"]["quantity_imperial"]
        intr = result["interior_partition_studs"]["quantity_imperial"]
        ratio = intr / ext
        assert 0.35 <= ratio <= 0.45, f"Interior/exterior ratio {ratio:.2f} out of range"

    def test_plates_boards_positive(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        boards = result["top_bottom_plates_boards"]["quantity_imperial"]
        assert boards > 0
        # 3 plates × 140 ft / 8 ft per board = 52.5 → 53
        assert 45 <= boards <= 65, f"Plate board count {boards} outside expected range"

    def test_header_stock_positive(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        header = result["header_stock_lf"]["quantity_imperial"]
        # 140 ft × 0.10 = 14 LF
        assert abs(header - 14.0) <= 2, f"Header stock {header} outside expected range"


# ---------------------------------------------------------------------------
# 2000 sqft SFR — value checks
# ---------------------------------------------------------------------------

class TestSFR2000:
    def test_exterior_studs_count(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_2000["perimeter_m"],
            floor_area_m2=SFR_2000["floor_area_m2"],
        )
        expected = calc_expected_exterior_studs(SFR_2000["perimeter_ft"])
        actual = result["exterior_studs"]["quantity_imperial"]
        assert abs(actual - expected) <= 5, f"Expected ~{expected}, got {actual}"

    def test_2000_larger_than_1200(self, calc_default):
        r1200 = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        r2000 = calc_default.calculate_framing(
            perimeter_m=SFR_2000["perimeter_m"],
            floor_area_m2=SFR_2000["floor_area_m2"],
        )
        for key in ["exterior_studs", "interior_partition_studs",
                    "top_bottom_plates_boards", "header_stock_lf"]:
            assert r2000[key]["quantity_imperial"] > r1200[key]["quantity_imperial"], \
                f"{key}: 2000 sqft should be larger than 1200 sqft"

    def test_header_stock_2000(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_2000["perimeter_m"],
            floor_area_m2=SFR_2000["floor_area_m2"],
        )
        header = result["header_stock_lf"]["quantity_imperial"]
        # 180 ft × 0.10 = 18 LF
        assert abs(header - 18.0) <= 2, f"Header stock {header} outside expected range"


# ---------------------------------------------------------------------------
# Multi-story scaling
# ---------------------------------------------------------------------------

class TestMultiStory:
    def test_2story_doubles_studs(self, calc_2story, calc_default):
        r1 = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        r2 = calc_2story.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        ratio = r2["exterior_studs"]["quantity_imperial"] / r1["exterior_studs"]["quantity_imperial"]
        assert abs(ratio - 2.0) < 0.1, f"2-story stud ratio {ratio:.2f} should be ~2.0"

    def test_2story_doubles_plates(self, calc_2story, calc_default):
        r1 = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        r2 = calc_2story.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        ratio = r2["top_bottom_plates_boards"]["quantity_imperial"] / r1["top_bottom_plates_boards"]["quantity_imperial"]
        assert abs(ratio - 2.0) < 0.1, f"2-story plate ratio {ratio:.2f} should be ~2.0"


# ---------------------------------------------------------------------------
# Unit consistency
# ---------------------------------------------------------------------------

class TestUnitConsistency:
    def test_metric_and_imperial_studs_match(self, calc_default):
        """Studs are unit-less counts — metric and imperial should be equal."""
        result = calc_default.calculate_framing(
            perimeter_m=SFR_1200["perimeter_m"],
            floor_area_m2=SFR_1200["floor_area_m2"],
        )
        for key in ["exterior_studs", "interior_partition_studs"]:
            assert result[key]["quantity_metric"] == result[key]["quantity_imperial"], \
                f"{key}: metric and imperial piece counts should match"

    def test_all_quantities_positive(self, calc_default):
        result = calc_default.calculate_framing(
            perimeter_m=SFR_2000["perimeter_m"],
            floor_area_m2=SFR_2000["floor_area_m2"],
        )
        for key, item in result.items():
            assert item["quantity_metric"] > 0, f"{key} metric quantity must be > 0"
            assert item["quantity_imperial"] > 0, f"{key} imperial quantity must be > 0"
