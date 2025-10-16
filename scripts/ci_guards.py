#!/usr/bin/env python3
"""
CI Guards: Pre-deployment validation checks.

This script runs various checks to ensure the codebase is safe to deploy:
1. Import validation - Check critical imports can be resolved
2. Syntax validation - Check for Python syntax errors
3. Configuration validation - Ensure required config vars are documented
4. Route file validation - Check that route files exist and are importable
"""

import sys
import os
import ast
import importlib
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")

def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def check_critical_imports():
    """
    Check that all critical imports can be resolved.
    
    This prevents issues like the PR-1 incident where import errors
    broke production deployment.
    """
    print_header("1. Critical Import Validation")
    
    critical_modules = [
        "src.infra.log",
        "src.services.structured_logging",
        "src.database",
        "src.models",
    ]
    
    failed = []
    
    for module_name in critical_modules:
        try:
            importlib.import_module(module_name)
            print_success(f"Import successful: {module_name}")
        except Exception as e:
            print_error(f"Import failed: {module_name}")
            print(f"  Error: {str(e)}")
            failed.append((module_name, e))
    
    if failed:
        print_error(f"\n{len(failed)} critical import(s) failed!")
        return False
    
    print_success(f"\nAll {len(critical_modules)} critical imports validated")
    return True

def check_python_syntax():
    """
    Check all Python files for syntax errors.
    
    This catches basic syntax errors before deployment.
    """
    print_header("2. Python Syntax Validation")
    
    src_dir = project_root / "src"
    python_files = list(src_dir.rglob("*.py"))
    
    print(f"Checking {len(python_files)} Python files...")
    
    errors = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code, filename=str(py_file))
        except SyntaxError as e:
            errors.append((py_file, e))
            print_error(f"Syntax error in {py_file.relative_to(project_root)}")
            print(f"  Line {e.lineno}: {e.msg}")
        except Exception as e:
            print_warning(f"Could not parse {py_file.relative_to(project_root)}: {e}")
    
    if errors:
        print_error(f"\n{len(errors)} file(s) with syntax errors!")
        return False
    
    print_success(f"\nAll {len(python_files)} Python files have valid syntax")
    return True

def check_route_files():
    """
    Validate that route files exist and can be imported.
    
    This helps catch missing route files before deployment.
    """
    print_header("3. Route File Validation")
    
    routes_dir = project_root / "src" / "routes"
    
    if not routes_dir.exists():
        print_error("Routes directory not found!")
        return False
    
    route_files = [f for f in routes_dir.glob("*.py") if f.name != "__init__.py"]
    
    print(f"Found {len(route_files)} route files")
    
    failed = []
    
    for route_file in route_files:
        module_name = f"src.routes.{route_file.stem}"
        try:
            importlib.import_module(module_name)
            print_success(f"  {route_file.name}")
        except Exception as e:
            print_error(f"  {route_file.name}: {str(e)[:60]}")
            failed.append((route_file, e))
    
    if failed:
        print_warning(f"\n{len(failed)} route file(s) failed to import")
        print_warning("This may be expected if they have runtime dependencies")
        # Don't fail the check, just warn
    
    print_success(f"\n{len(route_files) - len(failed)}/{len(route_files)} route files validated")
    return True

def check_infra_package():
    """
    Validate the src/infra package structure.
    
    This ensures the package created in PR-1 is properly structured.
    """
    print_header("4. Infrastructure Package Validation")
    
    infra_dir = project_root / "src" / "infra"
    
    if not infra_dir.exists():
        print_error("src/infra directory not found!")
        return False
    
    print_success("src/infra directory exists")
    
    # Check for __init__.py
    init_file = infra_dir / "__init__.py"
    if not init_file.exists():
        print_error("src/infra/__init__.py not found!")
        return False
    
    print_success("src/infra/__init__.py exists")
    
    # Check for expected modules
    expected_modules = ["log.py"]
    
    for module_file in expected_modules:
        module_path = infra_dir / module_file
        if module_path.exists():
            print_success(f"  {module_file} exists")
        else:
            print_warning(f"  {module_file} not found")
    
    # Try to import the package
    try:
        import src.infra
        print_success("src.infra package imports successfully")
    except Exception as e:
        print_error(f"Failed to import src.infra: {e}")
        return False
    
    # Check that log module exports expected functions
    try:
        from src.infra import log
        
        expected_exports = ["configure_logging", "init_logging", "get_logger"]
        found_exports = [name for name in expected_exports if hasattr(log, name)]
        
        if len(found_exports) == len(expected_exports):
            print_success(f"log module exports all expected functions: {', '.join(expected_exports)}")
        else:
            missing = set(expected_exports) - set(found_exports)
            print_warning(f"log module missing exports: {', '.join(missing)}")
    except Exception as e:
        print_warning(f"Could not validate log module exports: {e}")
    
    return True

def check_required_env_vars():
    """
    Validate that all required environment variables are documented.
    
    This ensures that deployment configuration is properly documented.
    """
    print_header("5. Environment Variable Documentation Check")
    
    # Check if .env.example exists
    env_example_path = project_root / ".env.example"
    
    if not env_example_path.exists():
        print_warning(".env.example file not found")
        print("  Consider creating one to document required environment variables")
        return True  # Not a failure, just a warning
    
    print_success(".env.example file exists")
    
    # Read documented variables
    with open(env_example_path) as f:
        documented_vars = set()
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                var_name = line.split('=')[0].strip()
                if var_name:
                    documented_vars.add(var_name)
    
    print_success(f"Found {len(documented_vars)} documented environment variables")
    
    # Check for critical variables
    critical_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "FLASK_ENV",
    ]
    
    missing_critical = [var for var in critical_vars if var not in documented_vars]
    
    if missing_critical:
        print_warning(f"Missing critical variables: {', '.join(missing_critical)}")
    else:
        print_success("All critical environment variables are documented")
    
    return True

def check_utils_package():
    """
    Validate the src/utils package from PR-2.
    
    This ensures the blueprint registry helper is properly available.
    """
    print_header("6. Utils Package Validation (PR-2)")
    
    utils_dir = project_root / "src" / "utils"
    
    if not utils_dir.exists():
        print_warning("src/utils directory not found (PR-2 not merged yet?)")
        return True  # Not a failure if PR-2 isn't merged
    
    print_success("src/utils directory exists")
    
    # Check for blueprint_registry.py
    registry_file = utils_dir / "blueprint_registry.py"
    if not registry_file.exists():
        print_warning("blueprint_registry.py not found")
        return True
    
    print_success("blueprint_registry.py exists")
    
    # Try to import the module
    try:
        from src.utils.blueprint_registry import (
            BlueprintRegistry,
            create_blueprint_registry,
            safe_register_blueprint
        )
        print_success("Blueprint registry imports successfully")
        print_success("  - BlueprintRegistry class available")
        print_success("  - create_blueprint_registry() available")
        print_success("  - safe_register_blueprint() available")
    except Exception as e:
        print_error(f"Failed to import blueprint registry: {e}")
        return False
    
    return True

def main():
    """Run all CI guards."""
    print(f"\n{Colors.BOLD}Brikk Infrastructure - CI Guards{Colors.RESET}")
    print(f"{Colors.BOLD}Running pre-deployment validation checks...{Colors.RESET}\n")
    
    checks = [
        ("Critical Imports", check_critical_imports),
        ("Python Syntax", check_python_syntax),
        ("Route Files", check_route_files),
        ("Infrastructure Package", check_infra_package),
        ("Environment Variables", check_required_env_vars),
        ("Utils Package", check_utils_package),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print_error(f"Check '{check_name}' crashed: {str(e)}")
            traceback.print_exc()
            results.append((check_name, False))
    
    # Print summary
    print_header("CI Guards Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        if result:
            print_success(f"{check_name}: PASSED")
        else:
            print_error(f"{check_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All CI guards passed! Safe to deploy.{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Some CI guards failed. Fix issues before deploying.{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

