"""
verify_products.py — run from project root.

Checks that backend/seed_db.py and frontend/src/lib/products.ts
define exactly the same 33 products with the same IDs.

Exit 0 on success, exit 1 on mismatch.
"""
import re, sys, os, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

if os.path.exists("backend/data/processed/products.json"):
    with open("backend/data/processed/products.json", encoding="utf-8") as f:
        backend_ids = sorted([p["id"] for p in json.load(f)])
    source_name = "data/processed/products.json"
else:
    with open("backend/seed_db.py", encoding="utf-8") as f:
        backend_ids = sorted([int(m) for m in re.findall(r'^\s+\((\d+),', f.read(), re.M)])
    source_name = "seed_db.py"

with open("frontend/src/lib/products.ts", encoding="utf-8") as f:
    frontend_ids = sorted([int(m) for m in re.findall(r'\{ id:\s*(\d+),\s*name:', f.read())])

print(f"Backend ({source_name})  : {len(backend_ids)} products, IDs {backend_ids[0]}–{backend_ids[-1]}")
print(f"Frontend lib/products.ts : {len(frontend_ids)} products, IDs {frontend_ids[0]}–{frontend_ids[-1]}")

if backend_ids == frontend_ids:
    print(f"\n✅  PASS — {len(backend_ids)} products, IDs perfectly aligned")
    sys.exit(0)
else:
    backend_only  = sorted(set(backend_ids)  - set(frontend_ids))
    frontend_only = sorted(set(frontend_ids) - set(backend_ids))
    print("\n❌  MISMATCH — fix before deploying!")
    if backend_only:  print(f"  In backend only:  {backend_only}")
    if frontend_only: print(f"  In frontend only: {frontend_only}")
    sys.exit(1)
