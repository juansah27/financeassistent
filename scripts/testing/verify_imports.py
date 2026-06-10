try:
    from app.db import crud_new_features
    from app.routes import analytics
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
