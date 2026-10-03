import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_PYTHON_VERSION = (3, 12)

REQUIRED_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("sqlalchemy", "sqlalchemy"),
    ("alembic", "alembic"),
    ("pillow", "PIL"),
    ("opencv-python", "cv2"),
    ("loguru", "loguru"),
    ("pydantic", "pydantic"),
    ("pydantic-settings", "pydantic_settings"),
    ("python-dotenv", "dotenv"),
    ("anthropic", "anthropic"),
    ("httpx", "httpx"),
    ("rapidfuzz", "rapidfuzz"),
]

REQUIRED_APP_MODULES = [
    "backend.app.core.config",
    "backend.app.core.paths",
    "backend.app.core.logging",
    "backend.app.services.discovery.models",
    "backend.app.services.discovery.image_scanner",
    "backend.app.services.discovery.product_grouper",
    "backend.app.services.discovery.manifest_builder",
]


def check_python_version() -> bool:
    if sys.version_info < REQUIRED_PYTHON_VERSION:
        print(
            "Python version check failed. "
            f"Expected Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}+, "
            f"but found {sys.version_info.major}.{sys.version_info.minor}."
        )
        return False

    print(
        "Python version check passed: "
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    return True


def check_required_packages() -> bool:
    all_ok = True

    print("\nChecking dependencies:")

    for requirement_name, module_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
            print(f"  [OK]   {requirement_name}")
        except Exception as exc:
            all_ok = False
            print(f"  [FAIL] {requirement_name} -> {exc}")

    return all_ok


def check_app_modules() -> bool:
    all_ok = True

    print("\nChecking ListingAI application modules:")

    for module_name in REQUIRED_APP_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"  [OK]   {module_name}")
        except Exception as exc:
            all_ok = False
            print(f"  [FAIL] {module_name} -> {exc}")

    return all_ok


def main() -> int:
    print("ListingAI package verification")
    print("=" * 40)

    python_ok = check_python_version()
    packages_ok = check_required_packages()
    app_modules_ok = check_app_modules()

    if python_ok and packages_ok and app_modules_ok:
        print("\nPackage verification complete.")
        return 0

    print("\nPackage verification failed. Fix the items above before continuing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
