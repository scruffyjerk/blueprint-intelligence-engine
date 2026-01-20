# Blueprint Intelligence Engine

AI-powered blueprint parsing engine that extracts room layouts and dimensions from residential floor plans, then calculates material quantities and cost estimates.

## Overview

The Blueprint Intelligence Engine (BIE) is a tool designed to:

1. **Accept** residential floor plan uploads (PDF/image formats)
2. **Parse** blueprints using GPT-4 Vision to identify rooms and dimensions
3. **Calculate** material estimates for flooring, drywall, and paint
4. **Display** results with cost ranges (low/mid/high)

This project has two potential products:
- **Consumer App**: A web application for homeowners and contractors
- **White-Label API**: A B2B API product for integration into other platforms

## Project Status

**Current Phase:** Phase 0 - Setup & Foundation

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | 🟡 In Progress | Setup & Foundation |
| Phase 1 | ⚪ Not Started | Proof of Concept |
| Phase 2 | ⚪ Not Started | MVP Development |
| Phase 3 | ⚪ Not Started | Launch & Iterate |
| Phase 4 | ⚪ Not Started | White-Label API |

## Project Structure

```
blueprint-intelligence-engine/
├── data/
│   ├── blueprints/          # Raw blueprint files (PDF, PNG, JPG)
│   ├── processed/           # Pre-processed images
│   └── ground_truth/        # Manual annotations for testing
├── src/
│   ├── preprocessing/       # Image preprocessing modules
│   ├── parsing/             # AI parsing logic
│   ├── calculation/         # Material calculation engine
│   └── api/                 # API wrapper (Phase 4)
├── tests/                   # Test scripts
├── notebooks/               # Jupyter notebooks for experimentation
├── docs/                    # Documentation
├── .env.example             # Example environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Tesseract OCR
- Poppler (for PDF processing)
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/scruffyjerk/blueprint-intelligence-engine.git
   cd blueprint-intelligence-engine
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr poppler-utils

   # macOS
   brew install tesseract poppler
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

### Running the Pipeline

```bash
python src/poc_pipeline.py --input data/blueprints/sample.pdf
```

## Technical Stack

| Component | Technology |
|-----------|------------|
| AI Model | GPT-4 Vision (gpt-4o / gpt-4.1-mini) |
| OCR | Tesseract |
| Image Processing | OpenCV, Pillow |
| PDF Processing | pdf2image, Poppler |
| Backend (MVP) | FastAPI |
| Frontend (MVP) | React |

## Success Metrics

| Metric | PoC Target | MVP Target |
|--------|------------|------------|
| Room Detection Accuracy | 70% | 85% |
| Dimension Extraction Accuracy | 50% | 70% |
| Processing Time | < 60s | < 30s |
| Cost Per Blueprint | < $0.15 | < $0.10 |

## Contributing

This is currently a private project in development. Contribution guidelines will be added when the project opens for collaboration.

## License

TBD

## Acknowledgments

Built with assistance from AI tools including Manus, Claude, and GitHub Copilot.
# Trigger redeploy Tue Jan 20 18:26:28 EST 2026
