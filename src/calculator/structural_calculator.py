"""
Takeoff.ai - Structural Calculator

Estimates structural material quantities from blueprint-derived measurements.
All outputs are inference-based using standard residential construction ratios.
Target accuracy: ±15% for typical single-family residential.

Phase 1 scope: Framing lumber only.
Phase 2+ will add foundation, roofing, MEP.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


M_TO_FT = 3.28084
FT_TO_M = 1 / M_TO_FT


@dataclass
class MaterialQuantity:
    """A single structural material quantity in both unit systems."""
    name: str
    quantity_metric: float
    unit_metric: str
    quantity_imperial: float
    unit_imperial: str
    category: str = "structural"
    confidence: str = "estimated"
    note: str = "Based on standard residential construction ratios"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "quantity_metric": round(self.quantity_metric, 2),
            "unit_metric": self.unit_metric,
            "quantity_imperial": round(self.quantity_imperial, 2),
            "unit_imperial": self.unit_imperial,
            "category": self.category,
            "confidence": self.confidence,
            "note": self.note,
        }


class StructuralCalculator:
    """
    Estimates structural material quantities for residential construction.

    All calculations use standard residential ratios and are labeled as
    estimated. No actual blueprint structural drawings are parsed in Phase 1.

    Args:
        ceiling_height: Floor-to-ceiling height in metres (default 2.7 m / ~9 ft)
        stories: Number of above-grade stories (default 1)
        wall_thickness: Framing wall thickness in metres (default 0.14 m / ~5.5 in)
    """

    STUD_SPACING_FT = 16 / 12  # 16" OC → ~1.333 ft per stud bay
    STUDS_PER_FT = 1 / STUD_SPACING_FT  # ~0.75 studs per linear ft of wall
    INTERIOR_PARTITION_RATIO = 0.40  # interior studs ≈ 40% of exterior studs
    PLATE_LAYERS = 3  # double top plate + single bottom plate
    BOARD_LENGTH_FT = 8  # standard stud board length in feet
    HEADER_RATIO = 0.10  # header stock ≈ 10% of perimeter in LF

    def __init__(
        self,
        ceiling_height: float = 2.7,
        stories: int = 1,
        wall_thickness: float = 0.14,
    ):
        self.ceiling_height = ceiling_height  # metres
        self.stories = stories
        self.wall_thickness = wall_thickness  # metres

    # ------------------------------------------------------------------
    # Framing
    # ------------------------------------------------------------------

    def calculate_framing(
        self,
        perimeter_m: float,
        floor_area_m2: float,
    ) -> Dict[str, Dict]:
        """
        Calculate framing lumber quantities for exterior and interior walls.

        Args:
            perimeter_m: Exterior wall perimeter in metres
            floor_area_m2: Total floor area in square metres

        Returns:
            Dict mapping material key → MaterialQuantity.to_dict()
            Keys: exterior_studs, interior_partition_studs,
                  top_bottom_plates_boards, header_stock_lf
        """
        perimeter_ft = perimeter_m * M_TO_FT
        # floor_area_sqft kept for future use / validation
        # floor_area_sqft = floor_area_m2 * (M_TO_FT ** 2)

        # --- Exterior studs ---
        # (perimeter_ft / stud_spacing_ft) × stories
        exterior_studs = (perimeter_ft * self.STUDS_PER_FT) * self.stories
        exterior_studs_rounded = round(exterior_studs)

        # --- Interior partition studs ---
        interior_studs = exterior_studs * self.INTERIOR_PARTITION_RATIO
        interior_studs_rounded = round(interior_studs)

        # --- Top/bottom plates ---
        # 3 plates × perimeter_ft / 8 ft per board
        plates_lf = perimeter_ft * self.PLATE_LAYERS * self.stories
        plates_boards = plates_lf / self.BOARD_LENGTH_FT
        plates_boards_rounded = round(plates_boards)

        # Metric equivalent: linear metres of plate material
        plates_lm = plates_lf * FT_TO_M

        # --- Header stock ---
        header_lf = perimeter_ft * self.HEADER_RATIO * self.stories
        header_lm = header_lf * FT_TO_M

        results = {
            "exterior_studs": MaterialQuantity(
                name="Exterior Wall Studs",
                quantity_metric=exterior_studs_rounded,
                unit_metric="pieces",
                quantity_imperial=exterior_studs_rounded,
                unit_imperial="pieces",
            ),
            "interior_partition_studs": MaterialQuantity(
                name="Interior Partition Studs",
                quantity_metric=interior_studs_rounded,
                unit_metric="pieces",
                quantity_imperial=interior_studs_rounded,
                unit_imperial="pieces",
            ),
            "top_bottom_plates_boards": MaterialQuantity(
                name="Top & Bottom Plates",
                quantity_metric=round(plates_lm, 1),
                unit_metric="linear metres",
                quantity_imperial=plates_boards_rounded,
                unit_imperial="8-ft boards",
            ),
            "header_stock_lf": MaterialQuantity(
                name="Header Stock",
                quantity_metric=round(header_lm, 1),
                unit_metric="linear metres",
                quantity_imperial=round(header_lf, 1),
                unit_imperial="linear feet",
            ),
        }

        return {key: mq.to_dict() for key, mq in results.items()}
