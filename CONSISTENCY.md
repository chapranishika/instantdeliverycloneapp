# Product Data Consistency Contract

## The Problem This Solves

In e-commerce ML systems, a common bug is **product ID drift** — the frontend
and backend use different IDs for the same product. This means:

- Click events logged with frontend product ID 5 don't join to the backend's
  product ID 5 if they refer to different items
- ML models trained on backend data can't serve meaningful recommendations
  for frontend products
- A/B test metrics are meaningless because the control and treatment products
  don't match

## Our Contract

**Single source of truth: `frontend/src/lib/products.ts`**

The 33 real Zepto CDN products defined in `PRODUCTS[]` are the canonical list.
`backend/seed_db.py` mirrors them exactly:

| Field              | Frontend (`products.ts`) | Backend (`seed_db.py`)  |
|--------------------|--------------------------|-------------------------|
| Product ID         | `id: number`             | `id` (primary key)      |
| Display name       | `name: string`           | `name`                  |
| Category           | `type: string`           | `category` → `Department` |
| MRP                | `price: number`          | `mrp`                   |
| Discounted price   | `disc: number`           | `price`                 |
| Image URL          | `src: string`            | `image_url`             |
| Unit label         | `unit: string`           | `quantity_label`        |
| Rating             | `rating: number`         | `rating`                |

## Why product IDs 0–32 and not 1–33?

Frontend uses 0-indexed IDs matching the original Zepto project data model.
The backend seeds with the same IDs so that event logs like:

```sql
SELECT p.name, COUNT(*) as views
FROM user_events e
JOIN products p ON e.product_id = p.id
WHERE e.event_type = 'view'
GROUP BY p.name
ORDER BY views DESC;
```

...work correctly without any ID translation layer.

## What happens if you add a new product?

1. Add it to `frontend/src/lib/products.ts` with the next available ID
2. Add the same entry to `backend/seed_db.py` PRODUCTS list
3. Run `python seed_db.py` to repopulate
4. Re-run `python ml_research/03_content_embeddings.py` to rebuild FAISS index

## Verification

```bash
# Verify frontend and backend product counts match
python - << 'PYEOF'
import re

with open("backend/seed_db.py") as f:
    backend_count = len(re.findall(r'^\s+\(\d+,', f.read(), re.M))

with open("frontend/src/lib/products.ts") as f:
    frontend_count = len(re.findall(r'^\s+\{ id:', f.read(), re.M))

print(f"Backend products:  {backend_count}")
print(f"Frontend products: {frontend_count}")
assert backend_count == frontend_count, "MISMATCH — fix before deploying!"
print("✓ Counts match")
PYEOF
```

Expected output:
```
Backend products:  33
Frontend products: 33
✓ Counts match
```


## Correct Verification Script

```bash
python3 verify_products.py
```
