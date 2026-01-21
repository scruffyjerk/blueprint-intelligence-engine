#!/usr/bin/env python3
"""Test labor availability multiplier."""

import sys
sys.path.insert(0, 'src')

from calculator import (
    CostEstimator, 
    QualityTier, 
    Region, 
    LaborAvailability,
    MaterialCalculator
)

# Create test blueprint analysis as dict
blueprint = {
    "rooms": [
        {"name": "Living Room", "width": "16", "length": "12", "area": "192", "unit": "imperial"},
        {"name": "Kitchen", "width": "12", "length": "10", "area": "120", "unit": "imperial"},
    ]
}

# Calculate materials
calc = MaterialCalculator(ceiling_height_m=2.4)
room_materials = calc.calculate_from_blueprint(blueprint)
totals = calc.get_totals(room_materials)

print("Testing Labor Availability Multipliers:")
print("=" * 60)

for labor in [LaborAvailability.LOW, LaborAvailability.AVERAGE, LaborAvailability.HIGH]:
    estimator = CostEstimator(
        quality_tier=QualityTier.STANDARD,
        region=Region.US_NATIONAL,
        include_labor=True,
        contingency_percent=0.10,
        labor_availability=labor
    )
    
    print(f"\nLabor Availability: {labor.value}")
    print(f"  Multiplier: {estimator.labor_availability_multiplier}")
    
    estimate = estimator.estimate_project("Test", totals)
    print(f"  Labor Subtotal: ${estimate.subtotal_labor:,.2f}")
    print(f"  Total Estimate: ${estimate.total_estimate:,.2f}")
