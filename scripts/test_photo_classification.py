import shutil
import sys
import json
import traceback  # <-- ADD THIS
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.paths import PICTURES
from backend.app.services.ai.photo_classifier import classify_photos

TEST_SKU = "TestClassification"

def main() -> int:
    test_dir = PICTURES / TEST_SKU
    
    if not test_dir.exists() or not any(test_dir.iterdir()):
        print(f"ERROR: Please place 3 to 5 real product photos into this folder:")
        print(f"  {test_dir}")
        print("Then run this script again.")
        test_dir.mkdir(parents=True, exist_ok=True)
        return 1

    image_paths = [f for f in test_dir.iterdir() if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    
    print(f"Found {len(image_paths)} photos in {test_dir.name}. Sending to Claude Vision...")
    
    try:
        classification = classify_photos(image_paths)
        
        print("\n--- Claude's Classification Result ---")
        import json
        print(json.dumps(classification, indent=4))
        print("-------------------------------------")
        
        if not classification:
            print("Classification failed or returned empty.")
            return 1
            
        print("\nPhoto classification test passed!")
        return 0
        
    except Exception as exc:
        print(f"\nTest failed with error: {type(exc).__name__}: {exc}")
        traceback.print_exc()  # <-- ADD THIS (Prints the exact line that failed)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())