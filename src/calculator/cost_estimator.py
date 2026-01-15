"""
Takeoff.ai - Cost Estimation Engine

This module provides cost estimates based on material quantities
using current market pricing data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime

from .material_calculator import MaterialQuantity


class QualityTier(Enum):
    """Quality tiers for materials."""
    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"
    LUXURY = "luxury"


class Region(Enum):
    """Geographic regions for pricing."""
    US_NATIONAL = "us_national"
    US_NORTHEAST = "us_northeast"
    US_SOUTHEAST = "us_southeast"
    US_MIDWEST = "us_midwest"
    US_SOUTHWEST = "us_southwest"
    US_WEST = "us_west"


@dataclass
class PricePoint:
    """Price information for a material at a specific quality tier."""
    price_per_unit: float
    unit: str
    quality_tier: QualityTier
    brand_example: str = ""
    notes: str = ""


@dataclass
class MaterialPricing:
    """Complete pricing information for a material type."""
    material_type: str
    display_name: str
    price_points: Dict[QualityTier, PricePoint] = field(default_factory=dict)
    labor_rate_per_unit: float = 0.0  # Labor cost per unit installed
    labor_unit: str = "sq ft"


@dataclass
class CostEstimate:
    """Cost estimate for a specific material."""
    material_type: str
    display_name: str
    quality_tier: QualityTier
    units_needed: int
    unit: str
    material_cost: float
    labor_cost: float
    total_cost: float
    price_per_unit: float
    brand_example: str = ""
    notes: str = ""


@dataclass
class ProjectEstimate:
    """Complete cost estimate for a project."""
    project_name: str
    timestamp: str
    region: Region
    estimates: List[CostEstimate] = field(default_factory=list)
    subtotal_materials: float = 0.0
    subtotal_labor: float = 0.0
    contingency_percent: float = 0.10
    contingency_amount: float = 0.0
    total_estimate: float = 0.0
    notes: List[str] = field(default_factory=list)


class PricingDatabase:
    """
    Material pricing database with current market rates.
    
    Prices are approximate US national averages as of 2024-2025.
    Actual prices vary by region, supplier, and market conditions.
    """
    
    # Material pricing data
    PRICING_DATA: Dict[str, MaterialPricing] = {
        "flooring_hardwood": MaterialPricing(
            material_type="flooring_hardwood",
            display_name="Hardwood Flooring",
            price_points={
                QualityTier.BUDGET: PricePoint(2.50, "sq ft", QualityTier.BUDGET, "Builder's Pride", "Thin veneer, limited warranty"),
                QualityTier.STANDARD: PricePoint(5.00, "sq ft", QualityTier.STANDARD, "Bruce, Mohawk", "3/4\" solid, 25-year warranty"),
                QualityTier.PREMIUM: PricePoint(8.00, "sq ft", QualityTier.PREMIUM, "Shaw, Armstrong", "Premium species, lifetime warranty"),
                QualityTier.LUXURY: PricePoint(15.00, "sq ft", QualityTier.LUXURY, "Carlisle, Duchateau", "Wide plank, exotic species"),
            },
            labor_rate_per_unit=4.00,  # Per sq ft installed
            labor_unit="sq ft"
        ),
        "flooring_laminate": MaterialPricing(
            material_type="flooring_laminate",
            display_name="Laminate Flooring",
            price_points={
                QualityTier.BUDGET: PricePoint(1.00, "sq ft", QualityTier.BUDGET, "TrafficMaster", "6mm, basic warranty"),
                QualityTier.STANDARD: PricePoint(2.50, "sq ft", QualityTier.STANDARD, "Pergo, Mohawk", "10mm, 20-year warranty"),
                QualityTier.PREMIUM: PricePoint(4.00, "sq ft", QualityTier.PREMIUM, "Quick-Step", "12mm, waterproof"),
                QualityTier.LUXURY: PricePoint(6.00, "sq ft", QualityTier.LUXURY, "Kaindl, Kronotex", "Premium European"),
            },
            labor_rate_per_unit=2.50,
            labor_unit="sq ft"
        ),
        "flooring_tile": MaterialPricing(
            material_type="flooring_tile",
            display_name="Ceramic/Porcelain Tile",
            price_points={
                QualityTier.BUDGET: PricePoint(1.50, "sq ft", QualityTier.BUDGET, "MSI, Florida Tile", "Basic ceramic"),
                QualityTier.STANDARD: PricePoint(4.00, "sq ft", QualityTier.STANDARD, "Daltile, Marazzi", "Porcelain, varied patterns"),
                QualityTier.PREMIUM: PricePoint(8.00, "sq ft", QualityTier.PREMIUM, "Emser, Crossville", "Large format, premium finish"),
                QualityTier.LUXURY: PricePoint(15.00, "sq ft", QualityTier.LUXURY, "Artistic Tile, Ann Sacks", "Designer, natural stone"),
            },
            labor_rate_per_unit=6.00,
            labor_unit="sq ft"
        ),
        "flooring_carpet": MaterialPricing(
            material_type="flooring_carpet",
            display_name="Carpet",
            price_points={
                QualityTier.BUDGET: PricePoint(1.00, "sq ft", QualityTier.BUDGET, "LifeProof", "Basic polyester"),
                QualityTier.STANDARD: PricePoint(3.00, "sq ft", QualityTier.STANDARD, "Shaw, Mohawk", "Nylon, stain resistant"),
                QualityTier.PREMIUM: PricePoint(6.00, "sq ft", QualityTier.PREMIUM, "Karastan", "Premium nylon, plush"),
                QualityTier.LUXURY: PricePoint(12.00, "sq ft", QualityTier.LUXURY, "Stanton, Masland", "Wool, custom patterns"),
            },
            labor_rate_per_unit=1.50,
            labor_unit="sq ft"
        ),
        "paint_wall": MaterialPricing(
            material_type="paint_wall",
            display_name="Interior Wall Paint",
            price_points={
                QualityTier.BUDGET: PricePoint(25.00, "gallon", QualityTier.BUDGET, "Glidden, Valspar", "Basic latex"),
                QualityTier.STANDARD: PricePoint(45.00, "gallon", QualityTier.STANDARD, "Behr, PPG", "Premium latex, washable"),
                QualityTier.PREMIUM: PricePoint(65.00, "gallon", QualityTier.PREMIUM, "Benjamin Moore, Sherwin-Williams", "Designer colors, low VOC"),
                QualityTier.LUXURY: PricePoint(100.00, "gallon", QualityTier.LUXURY, "Farrow & Ball, Fine Paints", "Artisan, specialty finishes"),
            },
            labor_rate_per_unit=2.00,  # Per sq ft of wall
            labor_unit="sq ft"
        ),
        "paint_ceiling": MaterialPricing(
            material_type="paint_ceiling",
            display_name="Ceiling Paint",
            price_points={
                QualityTier.BUDGET: PricePoint(20.00, "gallon", QualityTier.BUDGET, "Glidden Ceiling", "Flat white"),
                QualityTier.STANDARD: PricePoint(35.00, "gallon", QualityTier.STANDARD, "Behr Ceiling", "Ultra flat, splatter-resistant"),
                QualityTier.PREMIUM: PricePoint(55.00, "gallon", QualityTier.PREMIUM, "Benjamin Moore", "Premium ceiling paint"),
                QualityTier.LUXURY: PricePoint(80.00, "gallon", QualityTier.LUXURY, "Fine Paints of Europe", "Specialty ceiling"),
            },
            labor_rate_per_unit=1.50,
            labor_unit="sq ft"
        ),
        "drywall": MaterialPricing(
            material_type="drywall",
            display_name="Drywall",
            price_points={
                QualityTier.BUDGET: PricePoint(12.00, "sheet", QualityTier.BUDGET, "USG, National Gypsum", "1/2\" standard"),
                QualityTier.STANDARD: PricePoint(15.00, "sheet", QualityTier.STANDARD, "USG Sheetrock", "1/2\" moisture resistant"),
                QualityTier.PREMIUM: PricePoint(25.00, "sheet", QualityTier.PREMIUM, "USG Mold Tough", "Mold/moisture resistant"),
                QualityTier.LUXURY: PricePoint(40.00, "sheet", QualityTier.LUXURY, "QuietRock", "Soundproof drywall"),
            },
            labor_rate_per_unit=2.00,  # Per sq ft (includes taping/mudding)
            labor_unit="sq ft"
        ),
        "baseboard": MaterialPricing(
            material_type="baseboard",
            display_name="Baseboard Trim",
            price_points={
                QualityTier.BUDGET: PricePoint(1.00, "linear ft", QualityTier.BUDGET, "MDF primed", "3.25\" MDF"),
                QualityTier.STANDARD: PricePoint(2.50, "linear ft", QualityTier.STANDARD, "Pine, poplar", "Solid wood, paintable"),
                QualityTier.PREMIUM: PricePoint(5.00, "linear ft", QualityTier.PREMIUM, "Oak, maple", "Hardwood, stainable"),
                QualityTier.LUXURY: PricePoint(10.00, "linear ft", QualityTier.LUXURY, "Custom millwork", "Custom profiles"),
            },
            labor_rate_per_unit=3.00,
            labor_unit="linear ft"
        ),
        "crown_molding": MaterialPricing(
            material_type="crown_molding",
            display_name="Crown Molding",
            price_points={
                QualityTier.BUDGET: PricePoint(1.50, "linear ft", QualityTier.BUDGET, "Polystyrene", "Foam, lightweight"),
                QualityTier.STANDARD: PricePoint(4.00, "linear ft", QualityTier.STANDARD, "MDF, pine", "3.5\" profile"),
                QualityTier.PREMIUM: PricePoint(8.00, "linear ft", QualityTier.PREMIUM, "Hardwood", "5.25\" ornate"),
                QualityTier.LUXURY: PricePoint(15.00, "linear ft", QualityTier.LUXURY, "Custom millwork", "Multi-piece crown"),
            },
            labor_rate_per_unit=5.00,
            labor_unit="linear ft"
        ),
    }
    
    # Regional price adjustments (multipliers)
    REGIONAL_ADJUSTMENTS: Dict[Region, float] = {
        Region.US_NATIONAL: 1.00,
        Region.US_NORTHEAST: 1.25,  # Higher costs (NYC, Boston)
        Region.US_SOUTHEAST: 0.90,  # Lower costs
        Region.US_MIDWEST: 0.95,
        Region.US_SOUTHWEST: 1.00,
        Region.US_WEST: 1.20,  # Higher costs (CA, WA)
    }
    
    @classmethod
    def get_pricing(cls, material_type: str) -> Optional[MaterialPricing]:
        """Get pricing information for a material type."""
        return cls.PRICING_DATA.get(material_type)
    
    @classmethod
    def get_regional_multiplier(cls, region: Region) -> float:
        """Get the price adjustment multiplier for a region."""
        return cls.REGIONAL_ADJUSTMENTS.get(region, 1.0)


class CostEstimator:
    """
    Calculate cost estimates based on material quantities and pricing.
    """
    
    def __init__(
        self,
        quality_tier: QualityTier = QualityTier.STANDARD,
        region: Region = Region.US_NATIONAL,
        include_labor: bool = True,
        contingency_percent: float = 0.10
    ):
        """
        Initialize the cost estimator.
        
        Args:
            quality_tier: Default quality tier for materials
            region: Geographic region for pricing
            include_labor: Whether to include labor costs
            contingency_percent: Contingency percentage (0.10 = 10%)
        """
        self.quality_tier = quality_tier
        self.region = region
        self.include_labor = include_labor
        self.contingency_percent = contingency_percent
        self.regional_multiplier = PricingDatabase.get_regional_multiplier(region)
    
    def estimate_material(
        self,
        material_key: str,
        quantity: MaterialQuantity,
        quality_tier: QualityTier = None
    ) -> Optional[CostEstimate]:
        """
        Calculate cost estimate for a single material.
        
        Args:
            material_key: Key for the material (e.g., 'flooring_hardwood')
            quantity: MaterialQuantity from the calculator
            quality_tier: Override quality tier (uses default if None)
        
        Returns:
            CostEstimate or None if pricing not available
        """
        tier = quality_tier or self.quality_tier
        pricing = PricingDatabase.get_pricing(material_key)
        
        if not pricing or tier not in pricing.price_points:
            return None
        
        price_point = pricing.price_points[tier]
        
        # Calculate material cost
        material_cost = quantity.units_needed * price_point.price_per_unit * self.regional_multiplier
        
        # Calculate labor cost based on area/length
        labor_cost = 0.0
        if self.include_labor:
            # Convert quantity to labor units (sq ft or linear ft)
            if pricing.labor_unit == "sq ft":
                labor_area = quantity.quantity * 10.7639  # m² to sq ft
            else:  # linear ft
                labor_area = quantity.quantity * 3.28084  # m to ft
            
            labor_cost = labor_area * pricing.labor_rate_per_unit * self.regional_multiplier
        
        total_cost = material_cost + labor_cost
        
        return CostEstimate(
            material_type=material_key,
            display_name=pricing.display_name,
            quality_tier=tier,
            units_needed=quantity.units_needed,
            unit=quantity.unit,
            material_cost=round(material_cost, 2),
            labor_cost=round(labor_cost, 2),
            total_cost=round(total_cost, 2),
            price_per_unit=price_point.price_per_unit,
            brand_example=price_point.brand_example,
            notes=price_point.notes
        )
    
    def estimate_project(
        self,
        project_name: str,
        material_totals: Dict[str, MaterialQuantity],
        selected_materials: Dict[str, QualityTier] = None
    ) -> ProjectEstimate:
        """
        Calculate complete cost estimate for a project.
        
        Args:
            project_name: Name for the project
            material_totals: Dictionary of material quantities from MaterialCalculator
            selected_materials: Optional dict mapping material_key to quality tier
        
        Returns:
            ProjectEstimate with all costs
        """
        estimates = []
        subtotal_materials = 0.0
        subtotal_labor = 0.0
        
        for material_key, quantity in material_totals.items():
            # Get quality tier for this material
            tier = self.quality_tier
            if selected_materials and material_key in selected_materials:
                tier = selected_materials[material_key]
            
            estimate = self.estimate_material(material_key, quantity, tier)
            if estimate:
                estimates.append(estimate)
                subtotal_materials += estimate.material_cost
                subtotal_labor += estimate.labor_cost
        
        # Calculate contingency
        subtotal = subtotal_materials + subtotal_labor
        contingency_amount = subtotal * self.contingency_percent
        total_estimate = subtotal + contingency_amount
        
        return ProjectEstimate(
            project_name=project_name,
            timestamp=datetime.now().isoformat(),
            region=self.region,
            estimates=estimates,
            subtotal_materials=round(subtotal_materials, 2),
            subtotal_labor=round(subtotal_labor, 2),
            contingency_percent=self.contingency_percent,
            contingency_amount=round(contingency_amount, 2),
            total_estimate=round(total_estimate, 2),
            notes=[
                f"Prices based on {self.region.value} averages",
                f"Regional adjustment: {self.regional_multiplier:.0%}",
                f"Quality tier: {self.quality_tier.value}",
                "Actual costs may vary based on supplier and market conditions"
            ]
        )


def format_cost_report(estimate: ProjectEstimate) -> str:
    """Format a project estimate as a readable report."""
    lines = [
        "=" * 70,
        f"COST ESTIMATE: {estimate.project_name}",
        "=" * 70,
        f"Generated: {estimate.timestamp}",
        f"Region: {estimate.region.value}",
        "",
        "-" * 70,
        "MATERIAL BREAKDOWN",
        "-" * 70,
    ]
    
    for item in estimate.estimates:
        lines.append(f"\n{item.display_name} ({item.quality_tier.value})")
        lines.append(f"  Brand example: {item.brand_example}")
        lines.append(f"  Quantity: {item.units_needed} {item.unit}(s) @ ${item.price_per_unit:.2f}/{item.unit}")
        lines.append(f"  Material cost: ${item.material_cost:,.2f}")
        if item.labor_cost > 0:
            lines.append(f"  Labor cost: ${item.labor_cost:,.2f}")
        lines.append(f"  Subtotal: ${item.total_cost:,.2f}")
    
    lines.extend([
        "",
        "-" * 70,
        "SUMMARY",
        "-" * 70,
        f"  Materials subtotal: ${estimate.subtotal_materials:,.2f}",
        f"  Labor subtotal: ${estimate.subtotal_labor:,.2f}",
        f"  Contingency ({estimate.contingency_percent:.0%}): ${estimate.contingency_amount:,.2f}",
        "",
        f"  TOTAL ESTIMATE: ${estimate.total_estimate:,.2f}",
        "",
        "-" * 70,
        "NOTES",
        "-" * 70,
    ])
    
    for note in estimate.notes:
        lines.append(f"  • {note}")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def compare_quality_tiers(
    material_totals: Dict[str, MaterialQuantity],
    region: Region = Region.US_NATIONAL
) -> Dict[QualityTier, ProjectEstimate]:
    """
    Generate cost estimates for all quality tiers for comparison.
    
    Args:
        material_totals: Material quantities from calculator
        region: Geographic region
    
    Returns:
        Dictionary of quality tier to ProjectEstimate
    """
    comparisons = {}
    
    for tier in QualityTier:
        estimator = CostEstimator(
            quality_tier=tier,
            region=region,
            include_labor=True
        )
        estimate = estimator.estimate_project(
            f"Comparison - {tier.value}",
            material_totals
        )
        comparisons[tier] = estimate
    
    return comparisons


def format_comparison_report(comparisons: Dict[QualityTier, ProjectEstimate]) -> str:
    """Format a quality tier comparison as a readable report."""
    lines = [
        "=" * 70,
        "QUALITY TIER COMPARISON",
        "=" * 70,
        "",
        f"{'Tier':<12} {'Materials':>15} {'Labor':>15} {'Total':>15}",
        "-" * 60,
    ]
    
    for tier in [QualityTier.BUDGET, QualityTier.STANDARD, QualityTier.PREMIUM, QualityTier.LUXURY]:
        if tier in comparisons:
            est = comparisons[tier]
            lines.append(
                f"{tier.value:<12} ${est.subtotal_materials:>13,.2f} ${est.subtotal_labor:>13,.2f} ${est.total_estimate:>13,.2f}"
            )
    
    lines.extend([
        "",
        "=" * 70,
    ])
    
    return "\n".join(lines)
