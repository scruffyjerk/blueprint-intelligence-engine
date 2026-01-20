#!/usr/bin/env python3
"""
Test script to verify cost calculation is working correctly.
"""

import sys
sys.path.insert(0, 'src')

from calculator import (
    MaterialCalculator,
    CostEstimator,
    QualityTier,
    Region,
    compare_quality_tiers,
    format_material_report,
    format_cost_report
)

# Simulate room data from a blueprint analysis
test_rooms = [
    {
        "name": "Living Room",
        "width": "15'",
        "length": "20'",
        "area": None,
        "unit": "imperial",
        "confidence": "high"
    },
    {
        "name": "Kitchen",
        "width": "12'",
        "length": "14'",
        "area": None,
        "unit": "imperial",
        "confidence": "high"
    },
    {
        "name": "Master Bedroom",
        "width": "14'",
        "length": "16'",
        "area": None,
        "unit": "imperial",
        "confidence": "high"
    },
    {
        "name": "Bathroom",
        "width": "8'",
        "length": "10'",
        "area": None,
        "unit": "imperial",
        "confidence": "medium"
    }
]

blueprint_dict = {"rooms": test_rooms}

print("=" * 70)
print("TESTING COST CALCULATION SYSTEM")
print("=" * 70)

# Step 1: Calculate materials
print("\n[1] MATERIAL CALCULATION")
print("-" * 50)

calculator = MaterialCalculator(ceiling_height_m=2.4)
room_materials = calculator.calculate_from_blueprint(blueprint_dict)

print(f"Rooms processed: {len(room_materials)}")
for room_name, materials in room_materials.items():
    print(f"\n  {room_name}:")
    for mat_type, mat in materials.items():
        print(f"    - {mat.material_type}: {mat.units_needed} {mat.unit}(s)")

# Step 2: Get totals
print("\n[2] MATERIAL TOTALS")
print("-" * 50)

totals = calculator.get_totals(room_materials)
print(f"Total material types: {len(totals)}")
for mat_type, mat in totals.items():
    print(f"  {mat_type}: {mat.units_needed} {mat.unit}(s) - {mat.notes}")

# Step 3: Cost estimation
print("\n[3] COST ESTIMATION (Standard Quality)")
print("-" * 50)

estimator = CostEstimator(
    quality_tier=QualityTier.STANDARD,
    region=Region.US_NATIONAL,
    include_labor=True,
    contingency_percent=0.10
)

estimate = estimator.estimate_project("Test Project", totals)

print(f"Project: {estimate.project_name}")
print(f"Region: {estimate.region.value}")
print(f"\nCost breakdown:")
for item in estimate.estimates:
    print(f"  {item.display_name}:")
    print(f"    Material: ${item.material_cost:,.2f}")
    print(f"    Labor: ${item.labor_cost:,.2f}")
    print(f"    Total: ${item.total_cost:,.2f}")

print(f"\nSUMMARY:")
print(f"  Materials subtotal: ${estimate.subtotal_materials:,.2f}")
print(f"  Labor subtotal: ${estimate.subtotal_labor:,.2f}")
print(f"  Contingency ({estimate.contingency_percent:.0%}): ${estimate.contingency_amount:,.2f}")
print(f"  TOTAL ESTIMATE: ${estimate.total_estimate:,.2f}")

# Step 4: Quality tier comparison
print("\n[4] QUALITY TIER COMPARISON")
print("-" * 50)

comparisons = compare_quality_tiers(totals, Region.US_NATIONAL)
for tier, est in comparisons.items():
    print(f"  {tier.value.upper()}: ${est.total_estimate:,.2f}")

print("\n" + "=" * 70)
print("TEST COMPLETE!")
print("=" * 70)
