#!/usr/bin/env python3
"""Test script to verify kitchen and bathroom material calculations."""

import sys
sys.path.insert(0, '/home/ubuntu/blueprint-intelligence-engine/src')

from calculator.material_calculator import MaterialCalculator, RoomTypeDetector, RoomType
from calculator.cost_estimator import CostEstimator, QualityTier, Region, compare_quality_tiers

def test_room_detection():
    """Test room type detection."""
    print("\n" + "="*60)
    print("ROOM TYPE DETECTION TEST")
    print("="*60)
    
    test_rooms = [
        "Kitchen",
        "Master Bathroom",
        "Half Bath",
        "Powder Room",
        "Living Room",
        "Master Bedroom",
        "Dining Room",
        "Office",
        "Garage",
    ]
    
    for room in test_rooms:
        room_type = RoomTypeDetector.detect(room)
        print(f"  '{room}' -> {room_type.value}")

def test_kitchen_calculation():
    """Test kitchen material calculation."""
    print("\n" + "="*60)
    print("KITCHEN CALCULATION TEST")
    print("="*60)
    
    calculator = MaterialCalculator()
    
    # Simulate a 12x14 kitchen (168 sq ft)
    kitchen_data = {
        'name': 'Kitchen',
        'width': None,
        'length': None,
        'area': '168 sq ft',
        'unit': 'imperial'
    }
    
    materials = calculator.calculate_from_room(kitchen_data)
    
    print(f"\nKitchen (168 sq ft) Materials:")
    print("-" * 40)
    
    # Group by category
    categories = {}
    for key, qty in materials.items():
        cat = qty.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, qty))
    
    for cat, items in sorted(categories.items()):
        print(f"\n{cat.upper()}:")
        for key, qty in items:
            print(f"  {qty.material_type}: {qty.units_needed} {qty.unit} ({qty.notes})")
    
    return materials

def test_bathroom_calculation():
    """Test bathroom material calculation."""
    print("\n" + "="*60)
    print("BATHROOM CALCULATION TEST")
    print("="*60)
    
    calculator = MaterialCalculator()
    
    # Test full bathroom (80 sq ft)
    full_bath_data = {
        'name': 'Master Bathroom',
        'width': None,
        'length': None,
        'area': '80 sq ft',
        'unit': 'imperial'
    }
    
    # Test half bathroom (35 sq ft)
    half_bath_data = {
        'name': 'Powder Room',
        'width': None,
        'length': None,
        'area': '35 sq ft',
        'unit': 'imperial'
    }
    
    print(f"\nFull Bathroom (80 sq ft) Materials:")
    print("-" * 40)
    full_bath_materials = calculator.calculate_from_room(full_bath_data)
    
    categories = {}
    for key, qty in full_bath_materials.items():
        cat = qty.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, qty))
    
    for cat, items in sorted(categories.items()):
        print(f"\n{cat.upper()}:")
        for key, qty in items:
            print(f"  {qty.material_type}: {qty.units_needed} {qty.unit}")
    
    print(f"\n\nHalf Bathroom (35 sq ft) Materials:")
    print("-" * 40)
    half_bath_materials = calculator.calculate_from_room(half_bath_data)
    
    categories = {}
    for key, qty in half_bath_materials.items():
        cat = qty.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, qty))
    
    for cat, items in sorted(categories.items()):
        print(f"\n{cat.upper()}:")
        for key, qty in items:
            print(f"  {qty.material_type}: {qty.units_needed} {qty.unit}")
    
    return full_bath_materials, half_bath_materials

def test_full_house_estimate():
    """Test a full house with kitchen and bathrooms."""
    print("\n" + "="*60)
    print("FULL HOUSE ESTIMATE TEST")
    print("="*60)
    
    calculator = MaterialCalculator()
    
    # Simulate a typical house
    blueprint = {
        'rooms': [
            {'name': 'Kitchen', 'area': '200 sq ft', 'unit': 'imperial'},
            {'name': 'Master Bathroom', 'area': '100 sq ft', 'unit': 'imperial'},
            {'name': 'Bathroom 2', 'area': '60 sq ft', 'unit': 'imperial'},
            {'name': 'Half Bath', 'area': '30 sq ft', 'unit': 'imperial'},
            {'name': 'Living Room', 'area': '350 sq ft', 'unit': 'imperial'},
            {'name': 'Dining Room', 'area': '180 sq ft', 'unit': 'imperial'},
            {'name': 'Master Bedroom', 'area': '250 sq ft', 'unit': 'imperial'},
            {'name': 'Bedroom 2', 'area': '150 sq ft', 'unit': 'imperial'},
            {'name': 'Bedroom 3', 'area': '130 sq ft', 'unit': 'imperial'},
        ]
    }
    
    # Calculate materials
    room_materials = calculator.calculate_from_blueprint(blueprint)
    totals = calculator.get_totals(room_materials)
    
    print(f"\nTotal Square Footage: 1,450 sq ft")
    print(f"Rooms: {len(blueprint['rooms'])}")
    print(f"  - 1 Kitchen")
    print(f"  - 3 Bathrooms (1 master, 1 full, 1 half)")
    print(f"  - 3 Bedrooms")
    print(f"  - Living Room + Dining Room")
    
    # Cost estimate
    estimator = CostEstimator(
        quality_tier=QualityTier.STANDARD,
        region=Region.US_NATIONAL,
        include_labor=True,
        contingency_percent=0.10
    )
    
    estimate = estimator.estimate_project("Test House", totals)
    
    print(f"\n" + "-"*40)
    print("COST ESTIMATE (Standard Quality)")
    print("-"*40)
    
    # Group estimates by category
    categories = {}
    for est in estimate.estimates:
        cat = est.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(est)
    
    for cat in ['flooring', 'paint', 'drywall', 'trim', 'kitchen', 'bathroom']:
        if cat not in categories:
            continue
        items = categories[cat]
        cat_total = sum(e.total_cost for e in items)
        print(f"\n{cat.upper()}: ${cat_total:,.2f}")
        for est in items:
            print(f"  {est.display_name}: ${est.total_cost:,.2f} ({est.units_needed} {est.unit})")
    
    print(f"\n" + "="*40)
    print(f"Materials Subtotal: ${estimate.subtotal_materials:,.2f}")
    print(f"Labor Subtotal: ${estimate.subtotal_labor:,.2f}")
    print(f"Contingency (10%): ${estimate.contingency_amount:,.2f}")
    print(f"GRAND TOTAL: ${estimate.total_estimate:,.2f}")
    print("="*40)
    
    # Quality tier comparison
    print("\nQUALITY TIER COMPARISON:")
    tier_comparison = compare_quality_tiers(totals)
    for tier, total in tier_comparison.items():
        print(f"  {tier.capitalize()}: ${total:,.2f}")
    
    return estimate

if __name__ == "__main__":
    test_room_detection()
    test_kitchen_calculation()
    test_bathroom_calculation()
    test_full_house_estimate()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED!")
    print("="*60)
