#!/usr/bin/env python3
"""Test the updated AI prompt with dimension estimation."""

import sys
import os
sys.path.insert(0, '/home/ubuntu/blueprint-intelligence-engine/src')

from parser.blueprint_parser import BlueprintParser

def test_floor_plan():
    """Test the floor plan with kitchen and bathrooms."""
    print("\n" + "="*60)
    print("TESTING AI DIMENSION ESTIMATION")
    print("="*60)
    
    # Test with the floor plan that has unlabeled kitchen/bathrooms
    image_path = "/home/ubuntu/test_floorplan.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Test image not found at {image_path}")
        return
    
    print(f"\nAnalyzing: {image_path}")
    print("This floor plan has labeled dimensions for bedrooms/living,")
    print("but Kitchen, Bath 1, Bath 2 are NOT labeled with dimensions.")
    print("\nThe AI should ESTIMATE these based on visual proportions...")
    print("-" * 60)
    
    parser = BlueprintParser()
    analysis = parser.parse(image_path)
    
    print(f"\nModel used: {analysis.model_used}")
    print(f"Unit system: {analysis.unit_system}")
    print(f"Total rooms found: {len(analysis.rooms)}")
    
    print("\n" + "-"*60)
    print("ROOM ANALYSIS:")
    print("-"*60)
    
    for room in analysis.rooms:
        print(f"\n{room.name}:")
        print(f"  Width: {room.width}")
        print(f"  Length: {room.length}")
        print(f"  Area: {room.area}")
        print(f"  Confidence: {room.confidence}")
    
    if analysis.warnings:
        print("\n" + "-"*60)
        print("WARNINGS:")
        for warning in analysis.warnings:
            print(f"  - {warning}")
    
    # Check if kitchen and bathrooms now have dimensions
    print("\n" + "="*60)
    print("VERIFICATION:")
    print("="*60)
    
    kitchen_rooms = [r for r in analysis.rooms if 'kitchen' in r.name.lower()]
    bath_rooms = [r for r in analysis.rooms if 'bath' in r.name.lower()]
    
    print(f"\nKitchens found: {len(kitchen_rooms)}")
    for room in kitchen_rooms:
        has_dims = room.width and room.length and room.width != "0" and room.length != "0"
        status = "✅ Has dimensions" if has_dims else "❌ Missing dimensions"
        print(f"  {room.name}: {room.width} x {room.length} - {status}")
    
    print(f"\nBathrooms found: {len(bath_rooms)}")
    for room in bath_rooms:
        has_dims = room.width and room.length and room.width != "0" and room.length != "0"
        status = "✅ Has dimensions" if has_dims else "❌ Missing dimensions"
        print(f"  {room.name}: {room.width} x {room.length} - {status}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_floor_plan()
