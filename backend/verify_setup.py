#!/usr/bin/env python3
"""
Quick verification script to check if backend is properly set up.
Run this after installing dependencies to verify everything works.
"""
import sys
import importlib

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    try:
        if package_name:
            mod = importlib.import_module(module_name, package_name)
        else:
            mod = importlib.import_module(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {module_name} - {e}")
        return False

def main():
    print("Checking backend setup...")
    print("=" * 50)
    
    # Core dependencies
    print("\nCore Dependencies:")
    core_deps = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "httpx",
        "structlog",
        "pandas",
        "numpy",
    ]
    core_ok = all(check_import(dep) for dep in core_deps)
    
    # NBA API
    print("\nNBA API:")
    nba_ok = check_import("nba_api")
    
    # App modules
    print("\nApplication Modules:")
    app_modules = [
        ("app.main", "app"),
        ("app.services.espn_api_service", "app.services"),
        ("app.services.espn_mapping_service", "app.services"),
        ("app.services.context_collector", "app.services"),
        ("app.services.team_standings_service", "app.services"),
        ("app.services.news_context_service", "app.services"),
        ("app.services.live_game_context_service", "app.services"),
        ("app.services.feature_engineer", "app.services"),
        ("app.services.prop_engine", "app.services"),
    ]
    app_ok = all(check_import(mod, pkg) for mod, pkg in app_modules)
    
    print("\n" + "=" * 50)
    if core_ok and nba_ok and app_ok:
        print("✓ All checks passed! Backend is ready to run.")
        print("\nTo start the server:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend")
        return 0
    else:
        print("✗ Some checks failed. Please install missing dependencies:")
        print("  pip install -r backend/requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())

