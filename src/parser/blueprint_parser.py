"""
Blueprint Parser - Core module for extracting room data from floor plans using AI Vision.

Supports multiple AI providers: OpenAI GPT-4o and Anthropic Claude 3.5 Sonnet.
This is the heart of Takeoff.ai's Phase 1 Proof of Concept.
"""

import os
import json
import base64
import tempfile
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass, asdict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Room:
    """Represents a room extracted from a blueprint."""
    name: str
    width: Optional[str] = None
    length: Optional[str] = None
    area: Optional[str] = None
    unit: str = "unknown"  # "imperial", "metric", or "unknown"
    confidence: str = "medium"  # "high", "medium", "low"


@dataclass
class BlueprintAnalysis:
    """Complete analysis result from a blueprint."""
    filename: str
    rooms: list[Room]
    total_area: Optional[str] = None
    unit_system: str = "unknown"
    warnings: list[str] = None
    raw_response: str = None
    model_used: str = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "rooms": [asdict(r) for r in self.rooms],
            "total_area": self.total_area,
            "unit_system": self.unit_system,
            "warnings": self.warnings,
            "model_used": self.model_used
        }
    
    def to_json(self, indent=2):
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class BlueprintParser:
    """
    Parses blueprint images using AI Vision to extract room information.
    Supports both OpenAI GPT-4o and Anthropic Claude 3.5 Sonnet.
    """
    
    # The prompt that instructs AI Vision how to analyze blueprints
    ANALYSIS_PROMPT = """You are an expert construction estimator analyzing a residential floor plan. Your PRIMARY task is to READ and EXTRACT the exact dimension labels shown on the blueprint.

STEP 1 - DETECT UNIT SYSTEM (CRITICAL):
First, determine if the blueprint uses METRIC or IMPERIAL units:
- METRIC indicators: measurements in meters (m), centimeters (cm), or millimeters (mm), area shown as m² or sq m
- IMPERIAL indicators: measurements in feet ('), inches ("), or "ft", area shown as sq ft

STEP 2 - FIND DIMENSION LABELS:
Carefully scan the entire image for dimension annotations. These typically appear as:
- Numbers with tick marks or arrows (e.g., 14'-6" or 4.5m)
- Dimension lines with measurements above or below them
- Room labels that include dimensions (e.g., BEDROOM 12x14 or 3.5m x 4.2m)
- Area labels inside rooms (e.g., 14.8 m² or 150 sq ft)
- Scale indicators
- Total dimensions along exterior walls

STEP 3 - EXTRACT EXACT MEASUREMENTS:
For each room where you can READ dimension labels:
- Use the EXACT numbers shown on the plan
- Keep measurements in their ORIGINAL unit system
- If area is shown directly (e.g., "14.8 m²"), use that value
- Mark confidence as "high" for directly read values

STEP 4 - ESTIMATE ONLY WHEN NECESSARY:
For rooms WITHOUT visible dimension labels:
- Use proportional comparison to rooms WITH labels
- Mark confidence as "medium" for proportional estimates
- Mark confidence as "low" only if no reference dimensions exist

Please return a JSON object with the following structure:
{
    "rooms": [
        {
            "name": "Room name (e.g., Living Room, Master Bedroom, Kitchen)",
            "width": "Width measurement as number only (e.g., 14 for feet or 4.5 for meters)",
            "length": "Length measurement as number only (e.g., 18 for feet or 5.2 for meters)",
            "area": "Area in original units (e.g., 252 for sq ft or 23.4 for m²)",
            "confidence": "high, medium, or low"
        }
    ],
    "total_area": "Sum of all room areas in original units",
    "unit_system": "imperial OR metric - based on what you see on the blueprint",
    "warnings": ["List any rooms where dimensions were estimated rather than read"]
}

IMPORTANT RULES:
1. ALWAYS identify the unit system FIRST by looking at the labels
2. If you see "m", "m²", or decimal dimensions like 4.02, 3.68 - it's METRIC
3. If you see feet/inches symbols (', ") or "sq ft" - it's IMPERIAL
4. Keep all measurements in their ORIGINAL units - do NOT convert
5. NEVER return 0 or null for dimensions
6. Include ALL rooms and spaces you can identify (including areas, halls, balconies)
7. Look for labels OUTSIDE room boundaries too (labels may be placed externally)
8. Be CONSISTENT - same room should always have same dimensions

Return ONLY the JSON object, no additional text."""

    # Supported AI providers
    PROVIDER_OPENAI = "openai"
    PROVIDER_CLAUDE = "claude"
    
    def __init__(self, api_key: Optional[str] = None, model: str = None, provider: str = None):
        """
        Initialize the parser.
        
        Args:
            api_key: API key for the provider. Defaults to env var based on provider.
            model: Model to use. Defaults to env var or provider's best model.
            provider: AI provider to use ('openai' or 'claude'). Defaults to AI_PROVIDER env var or 'openai'.
        """
        # Determine provider
        self.provider = provider or os.getenv("AI_PROVIDER", self.PROVIDER_OPENAI).lower()
        
        if self.provider == self.PROVIDER_CLAUDE:
            self._init_claude(api_key, model)
        else:
            self._init_openai(api_key, model)
    
    def _init_openai(self, api_key: Optional[str], model: Optional[str]):
        """Initialize OpenAI client."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=self.api_key)
    
    def _init_claude(self, api_key: Optional[str], model: Optional[str]):
        """Initialize Anthropic Claude client."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """
        Encode an image file to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (base64_data, media_type)
        """
        path = Path(image_path)
        
        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_types.get(suffix, 'image/png')
        
        # Read and encode
        with open(path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        return image_data, media_type
    
    def _call_openai(self, image_data: str, media_type: str) -> str:
        """Call OpenAI Vision API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.ANALYSIS_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0
        )
        return response.choices[0].message.content
    
    def _call_claude(self, image_data: str, media_type: str) -> str:
        """Call Anthropic Claude Vision API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": self.ANALYSIS_PROMPT
                        }
                    ]
                }
            ]
        )
        return response.content[0].text
    
    def parse(self, image_source: Union[str, bytes], filename: str = "blueprint") -> BlueprintAnalysis:
        """
        Parse a blueprint image and extract room information.
        
        Args:
            image_source: Either a file path (str) or raw image bytes
            filename: Name to use in the result (defaults to "blueprint")
            
        Returns:
            BlueprintAnalysis object with extracted room data
        """
        temp_file_path = None
        
        try:
            # Handle different input types
            if isinstance(image_source, bytes):
                # Save bytes to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    tmp.write(image_source)
                    temp_file_path = tmp.name
                image_data, media_type = self._encode_image(temp_file_path)
            else:
                # It's a file path
                image_data, media_type = self._encode_image(image_source)
                filename = Path(image_source).name
            
            # Call the appropriate AI provider
            if self.provider == self.PROVIDER_CLAUDE:
                raw_response = self._call_claude(image_data, media_type)
            else:
                raw_response = self._call_openai(image_data, media_type)
            
            # Parse the JSON response
            try:
                # Clean up the response (remove markdown code blocks if present)
                json_str = raw_response
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                
                data = json.loads(json_str.strip())
            except json.JSONDecodeError as e:
                # If JSON parsing fails, return an error analysis
                return BlueprintAnalysis(
                    filename=filename,
                    rooms=[],
                    warnings=[f"Failed to parse AI response: {str(e)}"],
                    raw_response=raw_response,
                    model_used=f"{self.provider}:{self.model}"
                )
            
            # Convert to Room objects
            rooms = []
            for room_data in data.get("rooms", []):
                room = Room(
                    name=room_data.get("name", "Unknown"),
                    width=room_data.get("width"),
                    length=room_data.get("length"),
                    area=room_data.get("area"),
                    unit=data.get("unit_system", "unknown"),
                    confidence=room_data.get("confidence", "medium")
                )
                rooms.append(room)
            
            # Create the analysis result
            analysis = BlueprintAnalysis(
                filename=filename,
                rooms=rooms,
                total_area=data.get("total_area"),
                unit_system=data.get("unit_system", "unknown"),
                warnings=data.get("warnings", []),
                raw_response=raw_response,
                model_used=f"{self.provider}:{self.model}"
            )
            
            return analysis
            
        finally:
            # Clean up temp file if we created one
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def parse_batch(self, image_paths: list[str], verbose: bool = True) -> list[BlueprintAnalysis]:
        """
        Parse multiple blueprint images.
        
        Args:
            image_paths: List of paths to blueprint images
            verbose: Whether to print progress
            
        Returns:
            List of BlueprintAnalysis objects
        """
        results = []
        for i, path in enumerate(image_paths):
            if verbose:
                print(f"Processing {i+1}/{len(image_paths)}: {path}")
            result = self.parse(path)
            results.append(result)
        return results
