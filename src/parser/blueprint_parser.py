"""
Blueprint Parser - Core module for extracting room data from floor plans using GPT-4 Vision.

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
    Parses blueprint images using GPT-4 Vision to extract room information.
    """
    
    # The prompt that instructs GPT-4 Vision how to analyze blueprints
    ANALYSIS_PROMPT = """You are an expert construction estimator analyzing a residential floor plan. Your PRIMARY task is to READ and EXTRACT the exact dimension labels shown on the blueprint.

STEP 1 - FIND DIMENSION LABELS (CRITICAL):
Carefully scan the entire image for dimension annotations. These typically appear as:
- Numbers with tick marks or arrows (e.g., "14'-6\"" or "4.5m")
- Dimension lines with measurements above or below them
- Room labels that include dimensions (e.g., "BEDROOM 12x14")
- Scale indicators (e.g., "1/4\" = 1'-0\"")
- Total dimensions along exterior walls

STEP 2 - EXTRACT EXACT MEASUREMENTS:
For each room where you can READ dimension labels:
- Use the EXACT numbers shown on the plan
- Convert all measurements to feet (decimal format)
- Mark confidence as "high"

STEP 3 - ESTIMATE ONLY WHEN NECESSARY:
For rooms WITHOUT visible dimension labels:
- Use proportional comparison to rooms WITH labels
- If a room appears 75% the width of a labeled 16' room, estimate 12'
- Mark confidence as "medium" for proportional estimates
- Mark confidence as "low" only if no reference dimensions exist

Please return a JSON object with the following structure:
{
    "rooms": [
        {
            "name": "Room name (e.g., Living Room, Master Bedroom, Kitchen)",
            "width": "Width measurement as number only (e.g., 14 or 4.5)",
            "length": "Length measurement as number only (e.g., 18 or 5.2)",
            "area": "Calculated area in sq ft (width x length)",
            "confidence": "high if read from labels, medium if proportional estimate, low if default estimate",
            "dimension_source": "labeled/proportional/estimated"
        }
    ],
    "total_area": "Sum of all room areas",
    "unit_system": "imperial or metric based on the measurements shown",
    "scale_found": "The scale indicator if visible (e.g., 1/4\" = 1'-0\"), or null if not found",
    "warnings": ["List rooms where dimensions were estimated, not read from labels"]
}

DEFAULT ROOM SIZES (use ONLY when no labels or proportions available):
- Kitchen: 12x12 (144 sq ft)
- Bathroom (full): 8x10 (80 sq ft)
- Bathroom (half/powder): 5x6 (30 sq ft)  
- Master Bedroom: 14x16 (224 sq ft)
- Bedroom: 11x12 (132 sq ft)
- Living Room: 16x18 (288 sq ft)
- Dining Room: 11x12 (132 sq ft)
- Walk-in Closet: 6x8 (48 sq ft)
- Closet: 3x6 (18 sq ft)
- Laundry: 6x8 (48 sq ft)

CRITICAL RULES:
1. ALWAYS look for dimension labels FIRST - most professional blueprints have them
2. NEVER return 0 or null for dimensions
3. Use imperial units (feet) unless the plan clearly shows metric
4. For width and length, provide just the number (e.g., "12" not "12 ft")
5. Include ALL rooms you can identify
6. Be CONSISTENT - if you identify a room as 12x14, always report it as 12x14

Return ONLY the JSON object, no additional text."""

    def __init__(self, api_key: Optional[str] = None, model: str = None):
        """
        Initialize the parser.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use. Defaults to OPENAI_MODEL env var or 'gpt-4o'.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env file.")
        
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=self.api_key)
    
    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """
        Encode an image file to base64.
        
        Returns:
            Tuple of (base64_string, media_type)
        """
        path = Path(image_path)
        
        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_types.get(suffix, "image/jpeg")
        
        # Read and encode
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        return image_data, media_type
    
    def parse(self, image_input: Union[str, bytes, Path]) -> BlueprintAnalysis:
        """
        Parse a blueprint image and extract room information.
        
        Args:
            image_input: Path to the blueprint image file, or raw image bytes.
            
        Returns:
            BlueprintAnalysis object with extracted data.
        """
        temp_file_path = None
        
        try:
            # Handle both bytes and file paths
            if isinstance(image_input, bytes):
                # Direct bytes input - save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    tmp.write(image_input)
                    temp_file_path = tmp.name
                path = Path(temp_file_path)
                filename = "uploaded_image.png"
            else:
                path = Path(image_input)
                filename = path.name
                if not path.exists():
                    raise FileNotFoundError(f"Blueprint image not found: {image_input}")
            
            # Encode the image
            image_data, media_type = self._encode_image(path)
            
            # Call GPT-4 Vision
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
                                    "detail": "high"  # Use high detail for better accuracy
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0  # Zero temperature for deterministic, consistent outputs
            )
            
            # Extract the response
            raw_response = response.choices[0].message.content
            
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
                    model_used=self.model
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
                model_used=self.model
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
            image_paths: List of paths to blueprint images.
            verbose: Whether to print progress.
            
        Returns:
            List of BlueprintAnalysis objects.
        """
        results = []
        total = len(image_paths)
        
        for i, path in enumerate(image_paths, 1):
            if verbose:
                print(f"[{i}/{total}] Parsing: {Path(path).name}...")
            
            try:
                analysis = self.parse(path)
                results.append(analysis)
                if verbose:
                    print(f"         Found {len(analysis.rooms)} rooms")
            except Exception as e:
                if verbose:
                    print(f"         ERROR: {str(e)}")
                results.append(BlueprintAnalysis(
                    filename=Path(path).name,
                    rooms=[],
                    warnings=[f"Processing error: {str(e)}"]
                ))
        
        return results


def main():
    """Test the parser with a sample blueprint."""
    import sys
    
    # Check for command line argument
    if len(sys.argv) < 2:
        print("Usage: python blueprint_parser.py <path_to_blueprint_image>")
        print("\nExample: python blueprint_parser.py ../data/blueprints/01_roomsketcher_apartment_metric.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print(f"\n{'='*60}")
    print("TAKEOFF.AI - Blueprint Parser v0.1")
    print(f"{'='*60}\n")
    
    try:
        parser = BlueprintParser()
        print(f"Analyzing: {image_path}")
        print(f"Model: {parser.model}\n")
        
        analysis = parser.parse(image_path)
        
        print("RESULTS:")
        print("-" * 40)
        print(analysis.to_json())
        
        print("\n" + "-" * 40)
        print(f"Total rooms found: {len(analysis.rooms)}")
        print(f"Unit system: {analysis.unit_system}")
        if analysis.warnings:
            print(f"Warnings: {', '.join(analysis.warnings)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
