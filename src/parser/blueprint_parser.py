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
    ANALYSIS_PROMPT = """Analyze this residential floor plan image. Your task is to identify all rooms and extract their dimensions.

Please return a JSON object with the following structure:
{
    "rooms": [
        {
            "name": "Room name (e.g., Living Room, Master Bedroom, Kitchen)",
            "width": "Width measurement as shown (e.g., '14'-6\"' or '4.5m')",
            "length": "Length measurement as shown (e.g., '18'-0\"' or '5.2m')",
            "area": "Area if shown on plan (e.g., '252 sq ft' or '23.4 m²')",
            "confidence": "high/medium/low based on how clearly you can read the dimensions"
        }
    ],
    "total_area": "Total square footage/meters if shown on the plan",
    "unit_system": "imperial or metric based on the measurements shown",
    "warnings": ["List any rooms where dimensions are unclear or missing"]
}

Important guidelines:
1. Include ALL rooms you can identify, even if dimensions are not visible
2. For rooms without visible dimensions, set width/length to null but still include the room
3. Use the exact measurements as shown on the blueprint (don't convert units)
4. If a room has area shown but not dimensions, include the area
5. Be conservative - if you're unsure about a measurement, mark confidence as "low"
6. Common room types: Living Room, Dining Room, Kitchen, Bedroom, Bathroom, Master Bedroom, Master Bath, Closet, Garage, Laundry, Office, Den, Foyer, Hallway

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
                temperature=0.1  # Low temperature for more consistent outputs
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
