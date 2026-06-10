
import sys
import os
import importlib
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_routes():
    route_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "routes")
    files = [f for f in os.listdir(route_dir) if f.endswith(".py") and f != "__init__.py"]
    
    print(f"Verifying {len(files)} route modules...")
    
    success_count = 0
    errors = []
    
    for filename in files:
        module_name = f"app.routes.{filename[:-3]}"
        try:
            # Try to import the module
            importlib.import_module(module_name)
            print(f"[OK] {filename}")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] {filename}: {e}")
            errors.append(f"{filename}: {str(e)}\n{traceback.format_exc()}")
            
    print(f"\nVerification Complete: {success_count}/{len(files)} passed.")
    
    if errors:
        print("\nErrors found:")
        for err in errors:
            print("-" * 40)
            print(err)

if __name__ == "__main__":
    verify_routes()
