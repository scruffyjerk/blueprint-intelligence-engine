# Blueprint Accuracy Improvements — Technical Brief
_Written by Rex — 2026-03-31_
_For: Dev Agent_

## Current State

`src/parser/blueprint_parser.py` — solid foundation:
- Supports GPT-4o Vision + Claude 3.5 Sonnet
- Good structured prompt with unit detection + confidence scoring
- ✅ Works well on clean, high-res PDFs/exports

**Gap:** Zero image pre-processing. Low-quality scans (photos of blueprints, faded prints, skewed uploads) go straight to the API with no enhancement.

---

## Phase 1: Image Pre-Processing (Do This First)

**File to create:** `src/preprocessing/image_enhancer.py`

Add this pipeline BEFORE sending to vision model:

```python
import cv2
import numpy as np
from PIL import Image

def enhance_blueprint(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # 1. Deskew (fix rotation from scanner/camera)
    img = deskew(img)
    
    # 2. Contrast enhancement (CLAHE — better than global contrast)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img = clahe.apply(img)
    
    # 3. Denoise
    img = cv2.fastNlMeansDenoising(img, h=10)
    
    # 4. Sharpen lines
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    img = cv2.filter2D(img, -1, kernel)
    
    # 5. Upscale if too small (vision models work better at higher res)
    h, w = img.shape
    if max(h, w) < 1500:
        scale = 1500 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    return img

def deskew(img):
    coords = np.column_stack(np.where(img < 128))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
```

Wire into `BlueprintParser.parse()` before `_encode_image()`.

**Dependencies to add to requirements.txt:**
```
opencv-python-headless
Pillow
```

---

## Phase 2: Prompt Improvements

Current prompt is good but missing:

1. **Scale bar detection** — explicitly ask the model to find and use the scale bar
   - Add: "Look for a scale bar (e.g., '0____10 feet' or '1:100'). Use it to validate your dimension readings."

2. **Confidence calibration** — current "high/medium/low" isn't being used downstream
   - Add post-processing: if >30% of rooms are "low" confidence, flag the whole upload for manual review

3. **Multi-page handling** — blueprints often come as multi-page PDFs
   - Add PDF → image conversion per page, process each, merge results
   - Library: `pdf2image` (uses poppler)

---

## Phase 3: Accuracy Validation (When You Have Users)

Once real blueprints are flowing:

1. Build a test set of 20-30 blueprints where you know the correct measurements
2. Run current model vs enhanced model, measure % improvement
3. Use Roboflow to start annotating — rooms, walls, dimension labels
4. Fine-tune a smaller vision model on this dataset (LLaVA or Qwen-VL)

This becomes Takeoff.ai's defensible moat.

---

## Priority Order

1. ✅ **Add `image_enhancer.py`** — biggest bang, least effort
2. ✅ **Update `requirements.txt`** — opencv, pillow, pdf2image
3. ✅ **Wire pre-processing into `blueprint_parser.py`**
4. ✅ **Add scale bar instruction to ANALYSIS_PROMPT**
5. ⏳ **PDF multi-page support** — medium effort, high value
6. ⏳ **Confidence threshold alerting** — flag low-confidence results to user

---

## Files to Touch

- `src/preprocessing/image_enhancer.py` — CREATE (new file)
- `src/parser/blueprint_parser.py` — UPDATE (add pre-processing call + prompt tweak)
- `requirements.txt` — UPDATE (add opencv-python-headless, pdf2image)

_Ping #takeoff-ai when Phase 1 is done. Andre wants to test on real low-quality samples._
