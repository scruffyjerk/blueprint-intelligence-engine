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


class RoomType(Enum):
    """Room types for category-specific calculations."""
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    OTHER = "other"


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
    coverage_per_unit: float = 1.0
    units_needed: int = 1
    waste_factor: float = 0.0
    notes: str = ""
    category: str = "general"
    room_type: str = ""


class RoomTypeDetector:
    """Detect room type from room name."""
    
    KITCHEN_KEYWORDS = ['kitchen', 'kitchenette', 'galley']
    BATHROOM_KEYWORDS = ['bathroom', 'bath', 'restroom', 'powder room', 'half bath', 
                         'full bath', 'master bath', 'ensuite', 'wc', 'lavatory']
    BEDROOM_KEYWORDS = ['bedroom', 'master bedroom', 'guest room', 'nursery']
    LIVING_KEYWORDS = ['living room', 'living area', 'family room', 'great room', 
                       'sitting room', 'den', 'lounge']
    DINING_KEYWORDS = ['dining room', 'dining area', 'breakfast nook', 'eat-in']
    
    @classmethod
    def detect(cls, room_name: str) -> RoomType:
        """Detect room type from room name."""
        name_lower = room_name.lower().strip()
        
        for keyword in cls.KITCHEN_KEYWORDS:
            if keyword in name_lower:
                return RoomType.KITCHEN
        
        for keyword in cls.BATHROOM_KEYWORDS:
            if keyword in name_lower:
                return RoomType.BATHROOM
        
        for keyword in cls.BEDROOM_KEYWORDS:
            if keyword in name_lower:
                return RoomType.BEDROOM
        
        for keyword in cls.LIVING_KEYWORDS:
            if keyword in name_lower:
                return RoomType.LIVING_ROOM
        
        for keyword in cls.DINING_KEYWORDS:
            if keyword in name_lower:
                return RoomType.DINING_ROOM
        
        return RoomType.OTHER


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
        # ==================== FLOORING ====================
        "flooring_hardwood": {
            "name": "Hardwood Flooring",
            "coverage_per_unit": 2.23,  # m² per box (24 sq ft)
            "unit": "box",
            "waste_factor": 0.10,  # 10% waste
            "category": "flooring",
        },
        "flooring_laminate": {
            "name": "Laminate Flooring",
            "coverage_per_unit": 2.32,  # m² per box (25 sq ft)
            "unit": "box",
            "waste_factor": 0.10,
            "category": "flooring",
        },
        "flooring_tile": {
            "name": "Ceramic Tile",
            "coverage_per_unit": 0.93,  # m² per box (10 sq ft)
            "unit": "box",
            "waste_factor": 0.15,  # 15% waste for cutting
            "category": "flooring",
        },
        "flooring_carpet": {
            "name": "Carpet",
            "coverage_per_unit": 11.15,  # m² per roll (12 ft x 10 ft)
            "unit": "roll",
            "waste_factor": 0.10,
            "category": "flooring",
        },
        
        # ==================== PAINT ====================
        "paint_wall": {
            "name": "Wall Paint",
            "coverage_per_unit": 37.16,  # m² per gallon (400 sq ft)
            "unit": "gallon",
            "waste_factor": 0.05,
            "coats": 2,
            "category": "paint",
        },
        "paint_ceiling": {
            "name": "Ceiling Paint",
            "coverage_per_unit": 37.16,  # m² per gallon
            "unit": "gallon",
            "waste_factor": 0.05,
            "coats": 1,
            "category": "paint",
        },
        
        # ==================== DRYWALL ====================
        "drywall": {
            "name": "Drywall Sheets",
            "coverage_per_unit": 2.97,  # m² per 4x8 sheet
            "unit": "sheet",
            "waste_factor": 0.10,
            "category": "drywall",
        },
        "insulation_batt": {
            "name": "Batt Insulation",
            "coverage_per_unit": 8.92,  # m² per bundle (96 sq ft)
            "unit": "bundle",
            "waste_factor": 0.05,
            "category": "insulation",
        },
        
        # ==================== TRIM ====================
        "baseboard": {
            "name": "Baseboard Trim",
            "coverage_per_unit": 2.44,  # m per piece (8 ft)
            "unit": "piece",
            "waste_factor": 0.10,
            "is_linear": True,
            "category": "trim",
        },
        "crown_molding": {
            "name": "Crown Molding",
            "coverage_per_unit": 2.44,  # m per piece (8 ft)
            "unit": "piece",
            "waste_factor": 0.15,
            "is_linear": True,
            "category": "trim",
        },
        
        # ==================== KITCHEN ====================
        "cabinets_base": {
            "name": "Base Cabinets",
            "coverage_per_unit": 0.3048,  # m per linear ft (1 ft)
            "unit": "linear ft",
            "waste_factor": 0.0,
            "is_linear": True,
            "category": "kitchen",
        },
        "cabinets_wall": {
            "name": "Wall Cabinets",
            "coverage_per_unit": 0.3048,  # m per linear ft (1 ft)
            "unit": "linear ft",
            "waste_factor": 0.0,
            "is_linear": True,
            "category": "kitchen",
        },
        "countertop_laminate": {
            "name": "Laminate Countertop",
            "coverage_per_unit": 0.0929,  # m² per sq ft
            "unit": "sq ft",
            "waste_factor": 0.10,
            "category": "kitchen",
        },
        "countertop_granite": {
            "name": "Granite Countertop",
            "coverage_per_unit": 0.0929,  # m² per sq ft
            "unit": "sq ft",
            "waste_factor": 0.10,
            "category": "kitchen",
        },
        "countertop_quartz": {
            "name": "Quartz Countertop",
            "coverage_per_unit": 0.0929,  # m² per sq ft
            "unit": "sq ft",
            "waste_factor": 0.10,
            "category": "kitchen",
        },
        "backsplash_tile": {
            "name": "Tile Backsplash",
            "coverage_per_unit": 0.0929,  # m² per sq ft
            "unit": "sq ft",
            "waste_factor": 0.15,
            "category": "kitchen",
        },
        "kitchen_sink": {
            "name": "Kitchen Sink",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "kitchen",
        },
        "kitchen_faucet": {
            "name": "Kitchen Faucet",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "kitchen",
        },
        
        # ==================== BATHROOM ====================
        "vanity_cabinet": {
            "name": "Bathroom Vanity",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
        },
        "toilet": {
            "name": "Toilet",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
        },
        "bathroom_faucet": {
            "name": "Bathroom Faucet",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
        },
        "shower_tile": {
            "name": "Shower/Tub Tile",
            "coverage_per_unit": 0.0929,  # m² per sq ft
            "unit": "sq ft",
            "waste_factor": 0.15,
            "category": "bathroom",
        },
        "shower_door": {
            "name": "Shower Door",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
        },
        "bathtub": {
            "name": "Bathtub",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
        },
        "bathroom_exhaust_fan": {
            "name": "Exhaust Fan",
            "coverage_per_unit": 1,
            "unit": "unit",
            "waste_factor": 0.0,
            "is_fixture": True,
            "category": "bathroom",
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
        
        # Detect room type
        room_name = room_data.get('name', '')
        room_type = RoomTypeDetector.detect(room_name)
        
        results = {}
        
        # ==================== GENERAL MATERIALS (all rooms) ====================
        
        # Calculate flooring options
        for flooring_type in ['flooring_hardwood', 'flooring_laminate', 'flooring_tile', 'flooring_carpet']:
            results[flooring_type] = self._calculate_material(
                flooring_type, floor_area_m2, room_type.value
            )
        
        # Calculate paint
        results['paint_wall'] = self._calculate_material(
            'paint_wall', wall_area_m2, room_type.value
        )
        results['paint_ceiling'] = self._calculate_material(
            'paint_ceiling', floor_area_m2, room_type.value
        )
        
        # Calculate drywall (walls only, assuming ceiling exists)
        results['drywall'] = self._calculate_material(
            'drywall', wall_area_m2, room_type.value
        )
        
        # Calculate trim (linear measurements)
        results['baseboard'] = self._calculate_linear_material(
            'baseboard', perimeter_m, room_type.value
        )
        results['crown_molding'] = self._calculate_linear_material(
            'crown_molding', perimeter_m, room_type.value
        )
        
        # ==================== KITCHEN-SPECIFIC MATERIALS ====================
        if room_type == RoomType.KITCHEN:
            # Estimate cabinet run = ~60% of perimeter for base, ~40% for wall
            base_cabinet_run_m = perimeter_m * 0.60
            wall_cabinet_run_m = perimeter_m * 0.40
            
            results['cabinets_base'] = self._calculate_linear_material(
                'cabinets_base', base_cabinet_run_m, room_type.value
            )
            results['cabinets_wall'] = self._calculate_linear_material(
                'cabinets_wall', wall_cabinet_run_m, room_type.value
            )
            
            # Countertop area = base cabinet run * 25" depth (0.635m)
            countertop_area_m2 = base_cabinet_run_m * 0.635
            results['countertop_quartz'] = self._calculate_material(
                'countertop_quartz', countertop_area_m2, room_type.value
            )
            
            # Backsplash area = base cabinet run * 18" height (0.457m)
            backsplash_area_m2 = base_cabinet_run_m * 0.457
            results['backsplash_tile'] = self._calculate_material(
                'backsplash_tile', backsplash_area_m2, room_type.value
            )
            
            # Fixtures (1 each per kitchen)
            results['kitchen_sink'] = self._calculate_fixture('kitchen_sink', 1, room_type.value)
            results['kitchen_faucet'] = self._calculate_fixture('kitchen_faucet', 1, room_type.value)
        
        # ==================== BATHROOM-SPECIFIC MATERIALS ====================
        if room_type == RoomType.BATHROOM:
            # Determine bathroom type based on size
            is_full_bath = floor_area_m2 > 4.0  # > ~43 sq ft
            is_large_bath = floor_area_m2 > 7.0  # > ~75 sq ft
            
            # Vanity (1 per bathroom)
            results['vanity_cabinet'] = self._calculate_fixture('vanity_cabinet', 1, room_type.value)
            results['bathroom_faucet'] = self._calculate_fixture('bathroom_faucet', 1, room_type.value)
            
            # Toilet (1 per bathroom)
            results['toilet'] = self._calculate_fixture('toilet', 1, room_type.value)
            
            # Exhaust fan (1 per bathroom)
            results['bathroom_exhaust_fan'] = self._calculate_fixture('bathroom_exhaust_fan', 1, room_type.value)
            
            if is_full_bath:
                # Shower/tub tile - estimate 60 sq ft for standard shower surround
                shower_tile_area_m2 = 5.57  # ~60 sq ft
                results['shower_tile'] = self._calculate_material(
                    'shower_tile', shower_tile_area_m2, room_type.value
                )
                
                # Shower door or bathtub
                if is_large_bath:
                    # Large bath might have separate shower and tub
                    results['shower_door'] = self._calculate_fixture('shower_door', 1, room_type.value)
                    results['bathtub'] = self._calculate_fixture('bathtub', 1, room_type.value)
                else:
                    # Standard full bath - tub/shower combo
                    results['bathtub'] = self._calculate_fixture('bathtub', 1, room_type.value)
        
        return results
    
    def _calculate_material(self, material_type: str, area_m2: float, room_type: str = "") -> MaterialQuantity:
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
            notes=f"Covers {area_m2:.1f} m² ({area_m2 * 10.7639:.0f} sq ft)",
            category=spec.get('category', 'general'),
            room_type=room_type
        )
    
    def _calculate_linear_material(self, material_type: str, length_m: float, room_type: str = "") -> MaterialQuantity:
        """Calculate quantity for linear materials (trim, molding, cabinets)."""
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
            notes=f"Covers {length_m:.1f} m ({length_m * 3.28084:.0f} ft)",
            category=spec.get('category', 'general'),
            room_type=room_type
        )
    
    def _calculate_fixture(self, material_type: str, count: int, room_type: str = "") -> MaterialQuantity:
        """Calculate quantity for fixtures (unit-based items)."""
        spec = self.MATERIAL_SPECS[material_type]
        
        return MaterialQuantity(
            material_type=spec['name'],
            quantity=count,
            unit=spec['unit'],
            coverage_per_unit=1,
            units_needed=count,
            waste_factor=0.0,
            notes=f"{count} unit(s)",
            category=spec.get('category', 'general'),
            room_type=room_type
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
                        waste_factor=quantity.waste_factor,
                        category=quantity.category
                    )
                
                totals[material_type].quantity += quantity.quantity
                totals[material_type].units_needed += quantity.units_needed
        
        # Update notes with totals
        for material_type, total in totals.items():
            spec = self.MATERIAL_SPECS.get(material_type, {})
            if spec.get('is_linear'):
                total.notes = f"Total: {total.quantity:.1f} m ({total.quantity * 3.28084:.0f} ft)"
            elif spec.get('is_fixture'):
                total.notes = f"Total: {total.units_needed} unit(s)"
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
        "Kitchen": ['cabinets_base', 'cabinets_wall', 'countertop_laminate', 'countertop_granite', 
                   'countertop_quartz', 'backsplash_tile', 'kitchen_sink', 'kitchen_faucet'],
        "Bathroom": ['vanity_cabinet', 'toilet', 'bathroom_faucet', 'shower_tile', 
                    'shower_door', 'bathtub', 'bathroom_exhaust_fan'],
    }
    
    for category_name, material_keys in categories.items():
        category_items = [(k, totals[k]) for k in material_keys if k in totals]
        if not category_items:
            continue
        
        lines.append(f"\n{category_name}")
        lines.append("-" * 40)
        
        for key, qty in category_items:
            if unit_system == "imperial":
                if qty.unit in ['box', 'roll', 'sheet', 'bundle', 'piece', 'gallon', 'unit', 'linear ft', 'sq ft']:
                    lines.append(f"  {qty.material_type}: {qty.units_needed} {qty.unit}")
                else:
                    lines.append(f"  {qty.material_type}: {qty.units_needed} {qty.unit}")
            else:
                lines.append(f"  {qty.material_type}: {qty.units_needed} {qty.unit}")
            
            if qty.notes:
                lines.append(f"    ({qty.notes})")
    
    return "\n".join(lines)
