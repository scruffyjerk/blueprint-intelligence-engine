"""
Takeoff.ai - FastAPI Backend API

This API provides endpoints for blueprint parsing, material calculation,
and cost estimation.
"""

import os
import sys
import base64
import tempfile
from typing import Optional, List, Dict, Union
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    LaborAvailability,
    compare_quality_tiers
)
from api.pdf_generator import PDFReportGenerator
from api.stripe_integration import (
    create_checkout_session,
    create_customer_portal_session,
    get_subscription_from_session,
    get_subscription_status,
    handle_webhook_event,
    verify_webhook_signature,
    get_pricing_info,
    PRICE_IDS,
)
from api.user_store import user_store
from api.supabase_store import supabase_store

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
pdf_generator = PDFReportGenerator()


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


class LaborAvailabilityEnum(str, Enum):
    low = "low"        # Labor shortage - +15% labor cost
    average = "average"  # Normal market - no adjustment
    high = "high"      # Labor surplus - -10% labor cost


class RoomData(BaseModel):
    name: str
    width: Optional[Union[str, int, float]] = None
    length: Optional[Union[str, int, float]] = None
    area: Optional[Union[str, int, float]] = None
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


# PDF Report Request Models
class RoomInput(BaseModel):
    name: str
    dimensions: Dict[str, float] = {}
    area: float = 0
    confidence: float = 0.5


class MaterialInput(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    unit_cost: float
    material_cost: float
    labor_cost: float
    total_cost: float


class CostBreakdownInput(BaseModel):
    materials_subtotal: float
    labor_subtotal: float
    subtotal: float
    contingency_amount: float
    grand_total: float


class TierComparisonInput(BaseModel):
    tier: str
    grand_total: float


class PDFReportRequest(BaseModel):
    project_name: str = "Construction Estimate"
    filename: str = "blueprint.jpg"
    rooms: List[RoomInput]
    materials: List[MaterialInput]
    cost_breakdown: CostBreakdownInput
    tier_comparisons: List[TierComparisonInput]
    selected_tier: str = "standard"
    total_area: float = 0
    contingency_percent: float = 10
    labor_availability: str = "average"


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
    contingency_percent: float = Query(0.10),
    labor_availability: LaborAvailabilityEnum = Query(LaborAvailabilityEnum.average)
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
            
            # Convert labor availability
            labor_avail = LaborAvailability(labor_availability.value)
            
            estimator = CostEstimator(
                quality_tier=tier,
                region=reg,
                include_labor=include_labor,
                contingency_percent=contingency_percent,
                labor_availability=labor_avail
            )
            
            estimate = estimator.estimate_project(project_name, totals)
            
            estimate_items = []
            for item in estimate.estimates:
                # Handle quality_tier - could be Enum or string
                tier_value = item.quality_tier.value if hasattr(item.quality_tier, 'value') else str(item.quality_tier)
                estimate_items.append(CostEstimateItem(
                    material_type=item.material_type,
                    display_name=item.display_name,
                    quality_tier=tier_value,
                    units_needed=item.units_needed,
                    unit=item.unit,
                    material_cost=item.material_cost,
                    labor_cost=item.labor_cost,
                    total_cost=item.total_cost,
                    price_per_unit=item.price_per_unit,
                    brand_example=item.brand_example
                ))
            
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
            comparisons = compare_quality_tiers(totals, reg, include_labor, contingency_percent, labor_avail)
            quality_comparison = QualityComparisonResponse(
                budget=comparisons['budget'],
                standard=comparisons['standard'],
                premium=comparisons['premium'],
                luxury=comparisons['luxury']
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


@app.post("/api/v1/generate-pdf")
async def generate_pdf_report(request: PDFReportRequest):
    """
    Generate a PDF report from analysis results.
    
    Returns: PDF file as a downloadable stream
    """
    try:
        # Convert request data to the format expected by PDF generator
        rooms = [room.dict() for room in request.rooms]
        materials = [mat.dict() for mat in request.materials]
        cost_breakdown = request.cost_breakdown.dict()
        tier_comparisons = [tier.dict() for tier in request.tier_comparisons]
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_report(
            project_name=request.project_name,
            rooms=rooms,
            materials=materials,
            cost_breakdown=cost_breakdown,
            tier_comparisons=tier_comparisons,
            selected_tier=request.selected_tier,
            total_area=request.total_area,
            contingency_percent=request.contingency_percent,
            filename=request.filename,
            labor_availability=request.labor_availability
        )
        
        # Create filename for download
        safe_project_name = "".join(c for c in request.project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        download_filename = f"{safe_project_name or 'estimate'}_report.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Stripe & Subscription Endpoints
# ============================================================================

class CreateCheckoutRequest(BaseModel):
    plan: str  # "pro" or "agency"
    interval: str  # "monthly" or "annual"
    success_url: str
    cancel_url: str
    email: Optional[str] = None


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class UsageCheckRequest(BaseModel):
    user_id: str  # Email or anonymous ID


class UsageResponse(BaseModel):
    allowed: bool
    current_usage: int
    limit: int
    remaining: int
    plan: str
    message: Optional[str] = None


@app.get("/api/v1/pricing")
async def get_pricing():
    """
    Get pricing information for all plans.
    
    Returns: Pricing details for Free, Pro, and Agency plans
    """
    return get_pricing_info()


@app.post("/api/v1/create-checkout-session", response_model=CreateCheckoutResponse)
async def create_checkout(request: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for subscription.
    
    Returns: Checkout URL to redirect user to Stripe
    """
    try:
        # Validate plan and interval
        if request.plan not in ["pro", "agency"]:
            raise HTTPException(status_code=400, detail="Invalid plan. Must be 'pro' or 'agency'")
        if request.interval not in ["monthly", "annual"]:
            raise HTTPException(status_code=400, detail="Invalid interval. Must be 'monthly' or 'annual'")
        
        result = create_checkout_session(
            plan=request.plan,
            interval=request.interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=request.email
        )
        
        return CreateCheckoutResponse(
            checkout_url=result["checkout_url"],
            session_id=result["session_id"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/checkout-success")
async def checkout_success(session_id: str = Query(...)):
    """
    Handle successful checkout - retrieve subscription details.
    
    Called after user completes Stripe Checkout.
    """
    try:
        result = get_subscription_from_session(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Update user in our store
        if result.get("customer_id"):
            # Try to find or create user
            # In production, you'd have the user's email from the session
            user_store.update_subscription(
                user_id=result.get("customer_id"),  # Use customer ID as user ID for now
                plan=result.get("plan", "pro"),
                stripe_customer_id=result.get("customer_id"),
                stripe_subscription_id=result.get("subscription_id"),
                subscription_status="active",
                subscription_interval=result.get("interval"),
                current_period_end=result.get("current_period_end")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/create-portal-session")
async def create_portal(customer_id: str = Query(...), return_url: str = Query(...)):
    """
    Create a Stripe Customer Portal session for managing subscription.
    
    Returns: Portal URL for subscription management
    """
    try:
        portal_url = create_customer_portal_session(customer_id, return_url)
        return {"portal_url": portal_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives events from Stripe for subscription updates.
    Updates both the legacy user_store and the new Supabase store.
    """
    try:
        payload = await request.body()
        
        # Verify signature if webhook secret is configured
        if stripe_signature:
            verification = verify_webhook_signature(payload, stripe_signature)
            if not verification.get("success"):
                # Log but don't fail - allows testing without signature
                print(f"Webhook signature verification failed: {verification.get('error')}")
        
        # Parse the event
        import json
        from datetime import datetime
        event = json.loads(payload)
        
        # Handle the event
        result = handle_webhook_event(event)
        event_data = event.get("data", {}).get("object", {})
        
        # Update Supabase store based on event
        if result.get("action") == "subscription_created":
            customer_id = result.get("customer_id")
            customer_email = result.get("customer_email")
            subscription_id = result.get("subscription_id")
            plan = result.get("plan", "pro")
            interval = result.get("interval", "monthly")
            
            # Get period end from event data
            period_end = None
            if subscription_id:
                try:
                    import stripe
                    sub = stripe.Subscription.retrieve(subscription_id)
                    period_end = datetime.fromtimestamp(sub.current_period_end)
                except:
                    pass
            
            if customer_id and customer_email:
                # Update Supabase
                supabase_store.handle_checkout_completed(
                    customer_id=customer_id,
                    customer_email=customer_email,
                    subscription_id=subscription_id,
                    plan=plan,
                    interval=interval,
                    current_period_end=period_end
                )
                
                # Also update legacy store for backwards compatibility
                user = user_store.get_user_by_email(customer_email) or user_store.create_user(email=customer_email)
                user_store.update_subscription(
                    user_id=user.id,
                    plan=plan,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    subscription_status="active",
                    subscription_interval=interval
                )
        
        elif result.get("action") == "subscription_updated":
            subscription_id = result.get("subscription_id")
            status = result.get("status", "active")
            cancel_at_period_end = result.get("cancel_at_period_end", False)
            
            # Get period end from event data
            period_end = None
            if event_data.get("current_period_end"):
                period_end = datetime.fromtimestamp(event_data["current_period_end"])
            
            if subscription_id:
                supabase_store.handle_subscription_updated(
                    subscription_id=subscription_id,
                    status=status,
                    cancel_at_period_end=cancel_at_period_end,
                    current_period_end=period_end
                )
        
        elif result.get("action") == "subscription_cancelled":
            subscription_id = result.get("subscription_id")
            customer_id = result.get("customer_id")
            
            if subscription_id:
                # Update Supabase
                supabase_store.handle_subscription_deleted(subscription_id)
            
            # Also update legacy store
            if customer_id:
                user = user_store.get_user_by_stripe_customer(customer_id)
                if user:
                    user_store.cancel_subscription(user.id)
        
        return {"received": True, "result": result}
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/check-usage", response_model=UsageResponse)
async def check_usage(request: UsageCheckRequest):
    """
    Check a user's current usage without incrementing.
    
    Returns: Usage info including remaining estimates
    Uses Supabase store with fallback to legacy store.
    """
    # Try Supabase first
    usage = supabase_store.check_usage(request.user_id)
    
    # If no data from Supabase, try legacy store
    if usage.get("plan") == "free" and usage.get("current_usage", 0) == 0:
        legacy_usage = user_store.check_usage(request.user_id)
        if legacy_usage.get("current_usage", 0) > 0:
            usage = legacy_usage
    
    return UsageResponse(
        allowed=usage.get("remaining", 0) != 0,
        current_usage=usage.get("current_usage", 0),
        limit=usage.get("limit", 3),
        remaining=usage.get("remaining", 3),
        plan=usage.get("plan", "free")
    )


@app.post("/api/v1/increment-usage")
async def increment_usage(request: UsageCheckRequest):
    """
    Increment a user's usage count (call before processing an estimate).
    
    Returns: Whether the request is allowed and usage info
    Uses Supabase store with fallback to legacy store.
    """
    # Try Supabase first
    result = supabase_store.increment_usage(request.user_id)
    
    # Also increment in legacy store for backwards compatibility
    user_store.increment_usage(request.user_id)
    
    return result


@app.get("/api/v1/subscription-status")
async def get_user_subscription(user_id: str = Query(...)):
    """
    Get a user's subscription status.
    
    Returns: Subscription details including plan and usage
    Uses Supabase store with fallback to legacy store.
    """
    # Try Supabase first
    result = supabase_store.get_user_subscription_info(user_id)
    
    # If Supabase has data, return it
    if result.get("customer_id") or result.get("is_active"):
        return result
    
    # Fallback to legacy store
    return user_store.get_user_subscription_info(user_id)


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
