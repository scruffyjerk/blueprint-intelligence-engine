"""
Takeoff.ai - FastAPI Backend API

This API provides endpoints for blueprint parsing, material calculation,
and cost estimation.
"""

import os
import sys
import base64
import tempfile
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import BlueprintParser
from calculator import (
    MaterialCalculator,
    CostEstimator,
    QualityTier,
    Region,
    compare_quality_tiers
)

# Initialize FastAPI app
app = FastAPI(
    title="Takeoff.ai API",
    description="AI-powered blueprint parsing and construction cost estimation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
parser = BlueprintParser()
calculator = MaterialCalculator(ceiling_height_m=2.4)


# ============================================================================
# Pydantic Models
# ============================================================================

class QualityTierEnum(str, Enum):
    budget = "budget"
    standard = "standard"
    premium = "premium"
    luxury = "luxury"


class RegionEnum(str, Enum):
    us_national = "us_national"
    us_northeast = "us_northeast"
    us_southeast = "us_southeast"
    us_midwest = "us_midwest"
    us_southwest = "us_southwest"
    us_west = "us_west"


class RoomData(BaseModel):
    name: str
    width: Optional[str] = None
    length: Optional[str] = None
    area: Optional[str] = None
    unit: str = "imperial"
    confidence: str = "medium"


class BlueprintAnalysis(BaseModel):
    filename: str
    rooms: List[RoomData]
    total_area: Optional[str] = None
    unit_system: str
    warnings: List[str] = []
    model_used: str


class MaterialQuantityResponse(BaseModel):
    material_type: str
    quantity: float
    unit: str
    units_needed: int
    waste_factor: float
    notes: str


class CostEstimateItem(BaseModel):
    material_type: str
    display_name: str
    quality_tier: str
    units_needed: int
    unit: str
    material_cost: float
    labor_cost: float
    total_cost: float
    price_per_unit: float
    brand_example: str


class ProjectEstimateResponse(BaseModel):
    project_name: str
    timestamp: str
    region: str
    estimates: List[CostEstimateItem]
    subtotal_materials: float
    subtotal_labor: float
    contingency_percent: float
    contingency_amount: float
    total_estimate: float
    notes: List[str]


class QualityComparisonResponse(BaseModel):
    budget: float
    standard: float
    premium: float
    luxury: float


class FullAnalysisResponse(BaseModel):
    blueprint_analysis: BlueprintAnalysis
    material_totals: Dict[str, MaterialQuantityResponse]
    cost_estimate: ProjectEstimateResponse
    quality_comparison: QualityComparisonResponse


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/api/v1/parse", response_model=BlueprintAnalysis)
async def parse_blueprint(file: UploadFile = File(...)):
    """
    Parse a blueprint image and extract room information.
    
    Accepts: PNG, JPG, JPEG, WEBP images
    Returns: Extracted room data with dimensions
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Parse the blueprint
            analysis = parser.parse(tmp_path)
            
                        # Convert to response model
            rooms = [
                RoomData(
                    name=room.name,
                    width=room.width,
                    length=room.length,
                    area=room.area,
                    unit=room.unit,
                    confidence=room.confidence
                )
                for room in analysis.rooms
            ]
            
            return BlueprintAnalysis(
                filename=file.filename,
                rooms=rooms,
                total_area=analysis.total_area,
                unit_system=analysis.unit_system,
                warnings=analysis.warnings,
                model_used=analysis.model_used
            )
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/calculate", response_model=Dict[str, MaterialQuantityResponse])
async def calculate_materials(analysis: BlueprintAnalysis):
    """
    Calculate material quantities from parsed blueprint data.
    
    Returns: Material quantities for flooring, paint, drywall, trim
    """
    try:
        # Convert to dict format expected by calculator
        blueprint_dict = {
            'rooms': [room.dict() for room in analysis.rooms]
        }
        
        # Calculate materials
        room_materials = calculator.calculate_from_blueprint(blueprint_dict)
        totals = calculator.get_totals(room_materials)
        
        # Convert to response format
        response = {}
        for key, mat in totals.items():
            response[key] = MaterialQuantityResponse(
                material_type=mat.material_type,
                quantity=mat.quantity,
                unit=mat.unit,
                units_needed=mat.units_needed,
                waste_factor=mat.waste_factor,
                notes=mat.notes
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/estimate", response_model=ProjectEstimateResponse)
async def estimate_costs(
    materials: Dict[str, MaterialQuantityResponse],
    project_name: str = Query("My Project"),
    quality_tier: QualityTierEnum = Query(QualityTierEnum.standard),
    region: RegionEnum = Query(RegionEnum.us_national),
    include_labor: bool = Query(True),
    contingency_percent: float = Query(0.10)
):
    """
    Generate cost estimates from material quantities.
    
    Returns: Detailed cost breakdown with labor and contingency
    """
    try:
        # Convert quality tier and region
        tier = QualityTier(quality_tier.value)
        reg = Region(region.value)
        
        # Initialize estimator
        estimator = CostEstimator(
            quality_tier=tier,
            region=reg,
            include_labor=include_labor,
            contingency_percent=contingency_percent
        )
        
        # Convert materials to MaterialQuantity objects
        from calculator.material_calculator import MaterialQuantity
        material_totals = {}
        for key, mat in materials.items():
            material_totals[key] = MaterialQuantity(
                material_type=mat.material_type,
                quantity=mat.quantity,
                unit=mat.unit,
                coverage_per_unit=1.0,  # Not used for estimation
                units_needed=mat.units_needed,
                waste_factor=mat.waste_factor,
                notes=mat.notes
            )
        
        # Generate estimate
        estimate = estimator.estimate_project(project_name, material_totals)
        
        # Convert to response format
        estimate_items = [
            CostEstimateItem(
                material_type=item.material_type,
                display_name=item.display_name,
                quality_tier=item.quality_tier.value,
                units_needed=item.units_needed,
                unit=item.unit,
                material_cost=item.material_cost,
                labor_cost=item.labor_cost,
                total_cost=item.total_cost,
                price_per_unit=item.price_per_unit,
                brand_example=item.brand_example
            )
            for item in estimate.estimates
        ]
        
        return ProjectEstimateResponse(
            project_name=estimate.project_name,
            timestamp=estimate.timestamp,
            region=estimate.region.value,
            estimates=estimate_items,
            subtotal_materials=estimate.subtotal_materials,
            subtotal_labor=estimate.subtotal_labor,
            contingency_percent=estimate.contingency_percent,
            contingency_amount=estimate.contingency_amount,
            total_estimate=estimate.total_estimate,
            notes=estimate.notes
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze", response_model=FullAnalysisResponse)
async def full_analysis(
    file: UploadFile = File(...),
    project_name: str = Query("My Project"),
    quality_tier: QualityTierEnum = Query(QualityTierEnum.standard),
    region: RegionEnum = Query(RegionEnum.us_national),
    include_labor: bool = Query(True),
    contingency_percent: float = Query(0.10)
):
    """
    Complete end-to-end analysis: parse blueprint, calculate materials, estimate costs.
    
    This is the main endpoint for the Takeoff.ai application.
    
    Returns: Full analysis with blueprint data, materials, costs, and quality comparison
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Step 1: Parse the blueprint
            analysis = parser.parse(tmp_path)
            
                rooms = [
                RoomData(
                    name=room.name,
                    width=room.width,
                    length=room.length,
                    area=room.area,
                    unit=room.unit,
                    confidence=room.confidence
                )
                for room in analysis.rooms
            ]
            
            blueprint_analysis = BlueprintAnalysis(
                filename=file.filename,
                rooms=rooms,
                total_area=analysis.total_area,
                unit_system=analysis.unit_system,
                warnings=analysis.warnings,
                model_used=analysis.model_used
            )
            
            # Step 2: Calculate materials
            blueprint_dict = {'rooms': [room.dict() for room in rooms]}
            room_materials = calculator.calculate_from_blueprint(blueprint_dict)
            totals = calculator.get_totals(room_materials)
            
            material_response = {}
            for key, mat in totals.items():
                material_response[key] = MaterialQuantityResponse(
                    material_type=mat.material_type,
                    quantity=mat.quantity,
                    unit=mat.unit,
                    units_needed=mat.units_needed,
                    waste_factor=mat.waste_factor,
                    notes=mat.notes
                )
            
            # Step 3: Estimate costs
            tier = QualityTier(quality_tier.value)
            reg = Region(region.value)
            
            estimator = CostEstimator(
                quality_tier=tier,
                region=reg,
                include_labor=include_labor,
                contingency_percent=contingency_percent
            )
            
            estimate = estimator.estimate_project(project_name, totals)
            
            estimate_items = [
                CostEstimateItem(
                    material_type=item.material_type,
                    display_name=item.display_name,
                    quality_tier=item.quality_tier.value,
                    units_needed=item.units_needed,
                    unit=item.unit,
                    material_cost=item.material_cost,
                    labor_cost=item.labor_cost,
                    total_cost=item.total_cost,
                    price_per_unit=item.price_per_unit,
                    brand_example=item.brand_example
                )
                for item in estimate.estimates
            ]
            
            cost_estimate = ProjectEstimateResponse(
                project_name=estimate.project_name,
                timestamp=estimate.timestamp,
                region=estimate.region.value,
                estimates=estimate_items,
                subtotal_materials=estimate.subtotal_materials,
                subtotal_labor=estimate.subtotal_labor,
                contingency_percent=estimate.contingency_percent,
                contingency_amount=estimate.contingency_amount,
                total_estimate=estimate.total_estimate,
                notes=estimate.notes
            )
            
            # Step 4: Quality tier comparison
            comparisons = compare_quality_tiers(totals, reg)
            quality_comparison = QualityComparisonResponse(
                budget=comparisons[QualityTier.BUDGET].total_estimate,
                standard=comparisons[QualityTier.STANDARD].total_estimate,
                premium=comparisons[QualityTier.PREMIUM].total_estimate,
                luxury=comparisons[QualityTier.LUXURY].total_estimate
            )
            
            return FullAnalysisResponse(
                blueprint_analysis=blueprint_analysis,
                material_totals=material_response,
                cost_estimate=cost_estimate,
                quality_comparison=quality_comparison
            )
            
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
