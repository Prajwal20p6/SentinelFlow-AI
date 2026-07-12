import os
import re
import sys

def get_imports():
    import_pat = re.compile(r'^(?:import\s+(\w+)|from\s+(\w+)\s+import)')
    packages = set()
    
    backend_dir = os.path.join(os.getcwd(), 'backend')
    for root, dirs, files in os.walk(backend_dir):
        if '__pycache__' in root or 'venv' in root or '.pytest_cache' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            match = import_pat.match(line.strip())
                            if match:
                                pkg = match.group(1) or match.group(2)
                                if pkg:
                                    packages.add(pkg)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
    # Filter out local application modules
    app_modules = {'app', 'alembic', 'enkryptai'}
    third_party = sorted([p for p in packages if p not in app_modules])
    return third_party

if __name__ == '__main__':
    pkgs = get_imports()
    print("=== UNIQUE PACKAGES FOUND ===")
    for p in pkgs:
        print(p)
    print(f"Total package count: {len(pkgs)}")
