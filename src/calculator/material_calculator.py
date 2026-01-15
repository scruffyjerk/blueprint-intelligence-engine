"""
Takeoff.ai - Material Quantity Calculator

This module calculates material quantities based on room dimensions
extracted from blueprint parsing.
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class UnitSystem(Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class Dimensions:
    """Standardized dimensions in both metric and imperial."""
    width_m: float
    length_m: float
    height_m: float = 2.4  # Default ceiling height (8 ft)
    
    @property
    def width_ft(self) -> float:
        return self.width_m * 3.28084
    
    @property
    def length_ft(self) -> float:
        return self.length_m * 3.28084
    
    @property
    def height_ft(self) -> float:
        return self.height_m * 3.28084
    
    @property
    def floor_area_m2(self) -> float:
        return self.width_m * self.length_m
    
    @property
    def floor_area_sqft(self) -> float:
        return self.floor_area_m2 * 10.7639
    
    @property
    def wall_area_m2(self) -> float:
        """Total wall area (4 walls)."""
        perimeter = 2 * (self.width_m + self.length_m)
        return perimeter * self.height_m
    
    @property
    def wall_area_sqft(self) -> float:
        return self.wall_area_m2 * 10.7639


@dataclass
class MaterialQuantity:
    """Calculated material quantity for a specific material type."""
    material_type: str
    quantity: float
    unit: str
    coverage_per_unit: float
    units_needed: int
    waste_factor: float
    notes: str = ""


class DimensionParser:
    """Parse dimension strings into standardized Dimensions objects."""
    
    # Regex patterns for different dimension formats
    IMPERIAL_PATTERN = re.compile(
        r"(\d+)['\-]?\s*(\d+)?\"?\s*[xX×]\s*(\d+)['\-]?\s*(\d+)?\"?"
    )
    METRIC_PATTERN = re.compile(
        r"(\d+[.,]?\d*)\s*m?\s*[xX×]\s*(\d+[.,]?\d*)\s*m?"
    )
    AREA_METRIC_PATTERN = re.compile(
        r"(\d+[.,]?\d*)\s*m[²2]"
    )
    AREA_IMPERIAL_PATTERN = re.compile(
        r"(\d+[.,]?\d*)\s*(?:sq\.?\s*ft\.?|sqft|sf)"
    )
    
    @classmethod
    def parse(cls, dimension_str: str, unit_system: UnitSystem = None) -> Optional[Dimensions]:
        """Parse a dimension string into a Dimensions object."""
        if not dimension_str:
            return None
        
        # Clean the string
        dim_str = dimension_str.strip()
        
        # Try imperial format first (e.g., "12'-6" x 14'-0"")
        match = cls.IMPERIAL_PATTERN.search(dim_str)
        if match:
            width_ft = int(match.group(1)) + (int(match.group(2) or 0) / 12)
            length_ft = int(match.group(3)) + (int(match.group(4) or 0) / 12)
            return Dimensions(
                width_m=width_ft / 3.28084,
                length_m=length_ft / 3.28084
            )
        
        # Try metric format (e.g., "3.5 x 4.2" or "3,5 x 4,2")
        match = cls.METRIC_PATTERN.search(dim_str)
        if match:
            width = float(match.group(1).replace(',', '.'))
            length = float(match.group(2).replace(',', '.'))
            return Dimensions(width_m=width, length_m=length)
        
        return None
    
    @classmethod
    def parse_area(cls, area_str: str) -> Optional[float]:
        """Parse an area string and return area in square meters."""
        if not area_str:
            return None
        
        area_str = area_str.strip()
        
        # Try metric area (e.g., "14.8 m²")
        match = cls.AREA_METRIC_PATTERN.search(area_str)
        if match:
            return float(match.group(1).replace(',', '.'))
        
        # Try imperial area (e.g., "150 sq ft")
        match = cls.AREA_IMPERIAL_PATTERN.search(area_str)
        if match:
            sqft = float(match.group(1).replace(',', '.'))
            return sqft / 10.7639  # Convert to m²
        
        return None


class MaterialCalculator:
    """Calculate material quantities for construction/renovation projects."""
    
    # Material coverage rates (how much area one unit covers)
    MATERIAL_SPECS = {
        "flooring_hardwood": {
            "name": "Hardwood Flooring",
            "coverage_per_unit": 2.23,  # m² per box (24 sq ft)
            "unit": "box",
            "waste_factor": 0.10,  # 10% waste
        },
        "flooring_laminate": {
            "name": "Laminate Flooring",
            "coverage_per_unit": 2.32,  # m² per box (25 sq ft)
            "unit": "box",
            "waste_factor": 0.10,
        },
        "flooring_tile": {
            "name": "Ceramic Tile",
            "coverage_per_unit": 0.93,  # m² per box (10 sq ft)
            "unit": "box",
            "waste_factor": 0.15,  # 15% waste for cutting
        },
        "flooring_carpet": {
            "name": "Carpet",
            "coverage_per_unit": 11.15,  # m² per roll (12 ft x 10 ft)
            "unit": "roll",
            "waste_factor": 0.10,
        },
        "paint_wall": {
            "name": "Wall Paint",
            "coverage_per_unit": 37.16,  # m² per gallon (400 sq ft)
            "unit": "gallon",
            "waste_factor": 0.05,
            "coats": 2,
        },
        "paint_ceiling": {
            "name": "Ceiling Paint",
            "coverage_per_unit": 37.16,  # m² per gallon
            "unit": "gallon",
            "waste_factor": 0.05,
            "coats": 1,
        },
        "drywall": {
            "name": "Drywall Sheets",
            "coverage_per_unit": 2.97,  # m² per 4x8 sheet
            "unit": "sheet",
            "waste_factor": 0.10,
        },
        "insulation_batt": {
            "name": "Batt Insulation",
            "coverage_per_unit": 8.92,  # m² per bundle (96 sq ft)
            "unit": "bundle",
            "waste_factor": 0.05,
        },
        "baseboard": {
            "name": "Baseboard Trim",
            "coverage_per_unit": 2.44,  # m per piece (8 ft)
            "unit": "piece",
            "waste_factor": 0.10,
            "is_linear": True,
        },
        "crown_molding": {
            "name": "Crown Molding",
            "coverage_per_unit": 2.44,  # m per piece (8 ft)
            "unit": "piece",
            "waste_factor": 0.15,
            "is_linear": True,
        },
    }
    
    def __init__(self, ceiling_height_m: float = 2.4):
        """Initialize calculator with default ceiling height."""
        self.ceiling_height_m = ceiling_height_m
    
    def calculate_from_room(self, room_data: dict) -> Dict[str, MaterialQuantity]:
        """
        Calculate material quantities for a single room.
        
        Args:
            room_data: Room data from blueprint parser with 'width', 'length', 'area', 'unit'
        
        Returns:
            Dictionary of material type to MaterialQuantity
        """
        dimensions = None
        floor_area_m2 = None
        
        # Try to get dimensions from width/length
        if room_data.get('width') and room_data.get('length'):
            dim_str = f"{room_data['width']} x {room_data['length']}"
            dimensions = DimensionParser.parse(dim_str)
        
        # If no dimensions, try to get area directly
        if not dimensions and room_data.get('area'):
            floor_area_m2 = DimensionParser.parse_area(room_data['area'])
            if floor_area_m2:
                # Estimate dimensions assuming square room
                side = floor_area_m2 ** 0.5
                dimensions = Dimensions(width_m=side, length_m=side, height_m=self.ceiling_height_m)
        
        if not dimensions and not floor_area_m2:
            return {}
        
        if dimensions:
            dimensions.height_m = self.ceiling_height_m
            floor_area_m2 = dimensions.floor_area_m2
            wall_area_m2 = dimensions.wall_area_m2
            perimeter_m = 2 * (dimensions.width_m + dimensions.length_m)
        else:
            # Estimate from area
            side = floor_area_m2 ** 0.5
            wall_area_m2 = 4 * side * self.ceiling_height_m
            perimeter_m = 4 * side
        
        results = {}
        
        # Calculate flooring options
        for flooring_type in ['flooring_hardwood', 'flooring_laminate', 'flooring_tile', 'flooring_carpet']:
            results[flooring_type] = self._calculate_material(
                flooring_type, floor_area_m2
            )
        
        # Calculate paint
        results['paint_wall'] = self._calculate_material(
            'paint_wall', wall_area_m2
        )
        results['paint_ceiling'] = self._calculate_material(
            'paint_ceiling', floor_area_m2
        )
        
        # Calculate drywall (walls only, assuming ceiling exists)
        results['drywall'] = self._calculate_material(
            'drywall', wall_area_m2
        )
        
        # Calculate trim (linear measurements)
        results['baseboard'] = self._calculate_linear_material(
            'baseboard', perimeter_m
        )
        results['crown_molding'] = self._calculate_linear_material(
            'crown_molding', perimeter_m
        )
        
        return results
    
    def _calculate_material(self, material_type: str, area_m2: float) -> MaterialQuantity:
        """Calculate quantity for area-based materials."""
        spec = self.MATERIAL_SPECS[material_type]
        
        # Apply waste factor
        effective_area = area_m2 * (1 + spec['waste_factor'])
        
        # Apply coats if applicable (for paint)
        if 'coats' in spec:
            effective_area *= spec['coats']
        
        # Calculate units needed
        units_needed = effective_area / spec['coverage_per_unit']
        units_needed_rounded = max(1, int(units_needed + 0.99))  # Round up
        
        return MaterialQuantity(
            material_type=spec['name'],
            quantity=area_m2,
            unit=spec['unit'],
            coverage_per_unit=spec['coverage_per_unit'],
            units_needed=units_needed_rounded,
            waste_factor=spec['waste_factor'],
            notes=f"Covers {area_m2:.1f} m² ({area_m2 * 10.7639:.0f} sq ft)"
        )
    
    def _calculate_linear_material(self, material_type: str, length_m: float) -> MaterialQuantity:
        """Calculate quantity for linear materials (trim, molding)."""
        spec = self.MATERIAL_SPECS[material_type]
        
        # Apply waste factor
        effective_length = length_m * (1 + spec['waste_factor'])
        
        # Calculate units needed
        units_needed = effective_length / spec['coverage_per_unit']
        units_needed_rounded = max(1, int(units_needed + 0.99))  # Round up
        
        return MaterialQuantity(
            material_type=spec['name'],
            quantity=length_m,
            unit=spec['unit'],
            coverage_per_unit=spec['coverage_per_unit'],
            units_needed=units_needed_rounded,
            waste_factor=spec['waste_factor'],
            notes=f"Covers {length_m:.1f} m ({length_m * 3.28084:.0f} ft) perimeter"
        )
    
    def calculate_from_blueprint(self, blueprint_analysis: dict) -> Dict[str, Dict[str, MaterialQuantity]]:
        """
        Calculate material quantities for an entire blueprint.
        
        Args:
            blueprint_analysis: Full analysis from BlueprintParser
        
        Returns:
            Dictionary of room name to material quantities
        """
        results = {}
        
        for room in blueprint_analysis.get('rooms', []):
            room_name = room.get('name', 'Unknown Room')
            room_materials = self.calculate_from_room(room)
            if room_materials:
                results[room_name] = room_materials
        
        return results
    
    def get_totals(self, room_materials: Dict[str, Dict[str, MaterialQuantity]]) -> Dict[str, MaterialQuantity]:
        """
        Aggregate material quantities across all rooms.
        
        Args:
            room_materials: Output from calculate_from_blueprint
        
        Returns:
            Dictionary of material type to total MaterialQuantity
        """
        totals = {}
        
        for room_name, materials in room_materials.items():
            for material_type, quantity in materials.items():
                if material_type not in totals:
                    totals[material_type] = MaterialQuantity(
                        material_type=quantity.material_type,
                        quantity=0,
                        unit=quantity.unit,
                        coverage_per_unit=quantity.coverage_per_unit,
                        units_needed=0,
                        waste_factor=quantity.waste_factor
                    )
                
                totals[material_type].quantity += quantity.quantity
                totals[material_type].units_needed += quantity.units_needed
        
        # Update notes with totals
        for material_type, total in totals.items():
            if 'baseboard' in material_type or 'molding' in material_type:
                total.notes = f"Total: {total.quantity:.1f} m ({total.quantity * 3.28084:.0f} ft)"
            else:
                total.notes = f"Total: {total.quantity:.1f} m² ({total.quantity * 10.7639:.0f} sq ft)"
        
        return totals


def format_material_report(totals: Dict[str, MaterialQuantity], unit_system: str = "imperial") -> str:
    """Format material quantities as a readable report."""
    lines = [
        "=" * 60,
        "MATERIAL QUANTITY REPORT",
        "=" * 60,
        ""
    ]
    
    # Group by category
    categories = {
        "Flooring Options": ['flooring_hardwood', 'flooring_laminate', 'flooring_tile', 'flooring_carpet'],
        "Paint": ['paint_wall', 'paint_ceiling'],
        "Drywall": ['drywall'],
        "Trim": ['baseboard', 'crown_molding'],
    }
    
    for category, material_types in categories.items():
        lines.append(f"\n{category}")
        lines.append("-" * 40)
        
        for material_type in material_types:
            if material_type in totals:
                mat = totals[material_type]
                lines.append(f"  {mat.material_type}:")
                lines.append(f"    Quantity needed: {mat.units_needed} {mat.unit}(s)")
                lines.append(f"    {mat.notes}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)
