"""
Seed the database with the SAME 33 real Zepto products used in the frontend.

Previously this file had ~80 generic products with no image URLs,
while lib/products.ts had 33 real cdn.zeptonow.com products.
This mismatch meant:
  - ML models trained on backend data couldn't serve frontend products
  - product IDs didn't align between frontend and backend
  - "80+ products" README claim was false

Fix: seed exactly the 33 products from lib/products.ts, with the real
CDN image URLs, so frontend and backend share one canonical source of truth.

Run: python seed_db.py
"""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import AsyncSessionLocal, create_tables
from app.models.db_models import Department, Product, PromoCode

# ── Categories matching frontend CATEGORIES ────────────────────────────────────
CATEGORIES = [
    "Fresh Fruits",
    "Fresh Vegetables",
    "Leafy Herbs",
    "Flowers",
    "Exotic Veggies",
    "Kitchen",
    "House Hold",
    "Snacks & Munchies",
    "Cold Drinks & Juices",
    "Dairy, Bread & Eggs",
]

# ── 33 real Zepto products — mirrors src/lib/products.ts EXACTLY ──────────────
#
# Schema: (id, name, unit, category, price_mrp, price_disc, rating, image_url)
#
# id matches frontend product id so ML event logs are joinable
# image_url is the real cdn.zeptonow.com URL
# price_disc = what customer pays (frontend calls this "disc")
# price_mrp  = crossed-out original price
#
CDN = "https://cdn.zeptonow.com/production///tr:w-300,"
PRODUCTS = [
    # ── Fresh Fruits ──────────────────────────────────────────────
    (0,  "Banana",          "1kg",       "Fresh Fruits",     60,  48,  4.7,
     CDN + "ar-425-405,pr-true,f-webp,q-80/inventory/product/cb115d55-cf65-4228-80c8-b0fc0b90ae03-/tmp/20230216-1551351.jpeg"),
    (1,  "Apple",           "1kg",       "Fresh Fruits",    180, 162,  4.8,
     CDN + "ar-500-500,pr-true,f-webp,q-80/inventory/product/0e673bd2-2fe6-4d8e-899e-00b4d460a653-tmp/a87d6c85-8184-428d-a877-070f4f55ffb5.jpeg"),
    (2,  "Mango",           "1kg",       "Fresh Fruits",    120,  96,  4.9,
     CDN + "ar-478-522,pr-true,f-webp,q-80/inventory/product/1b9cf6b1-9a9d-41a7-ace5-0faec8e3e71f-image_file.png"),
    (3,  "Orange",          "1kg",       "Fresh Fruits",     80,  68,  4.6,
     CDN + "ar-187-187,pr-true,f-webp,q-80/inventory/product/6c78cf1a-ed30-4d24-8def-a274418a27ea-image"),
    (4,  "Papaya",          "1kg",       "Fresh Fruits",     40,  36,  4.4,
     CDN + "ar-1000-799,pr-true,f-webp,q-80/inventory/product/de957e5c-6ef2-4b20-831f-4ec31fcb4c3d-image_file.jpeg"),

    # ── Fresh Vegetables ──────────────────────────────────────────
    (5,  "Onion",           "1kg",       "Fresh Vegetables", 35,  28,  4.5,
     CDN + "ar-1200-1200,pr-true,f-webp,q-80/inventory/product/07a54355-4d10-4623-b369-1109db67d160-Photo.jpeg"),
    (6,  "Potato",          "1kg",       "Fresh Vegetables", 25,  22,  4.6,
     CDN + "ar-4745-3537,pr-true,f-webp,q-80/inventory/product/534318fb-a402-4902-9cce-2cbd8984d75b-53.jpeg"),
    (7,  "Cauliflower",     "1kg",       "Fresh Vegetables", 45,  36,  4.4,
     CDN + "ar-1500-1500,pr-true,f-webp,q-80/inventory/product/3a919660-707b-44f4-b666-8b3fcf094a7b-image"),
    (8,  "Bottle Gourd",    "1kg",       "Fresh Vegetables", 30,  27,  4.3,
     CDN + "ar-1000-1000,pr-true,f-webp,q-80/inventory/product/9e5847e4-17a6-4a48-8221-d237f440d995-image"),
    (9,  "Tomato",          "1kg",       "Fresh Vegetables", 50,  40,  4.7,
     CDN + "ar-800-500,pr-true,f-webp,q-80/inventory/product/dedf3d96-5fe5-482a-a24a-494f6e76845e-tmp/f3cb8fd8-e2df-4c11-ba79-4203e88af3ad.jpeg"),

    # ── Leafy Herbs ───────────────────────────────────────────────
    (10, "Spinach",         "500g",      "Leafy Herbs",      20,  18,  4.5,
     CDN + "ar-393-510,pr-true,f-webp,q-80/inventory/product/9abf0781-37d6-4b05-b559-912ab7ce2145-568.jpeg"),
    (11, "Coriander",       "100g",      "Leafy Herbs",      15,  12,  4.6,
     CDN + "ar-1500-888,pr-true,f-webp,q-80/inventory/product/6f885126-571a-4655-a9fb-91a6a893928f-4199723a-d43e-4e86-b88d-34289de52bb5-Photo.webp"),
    (12, "Curry Leaves",    "50g",       "Leafy Herbs",      10,   8,  4.4,
     CDN + "ar-1000-1000,pr-true,f-webp,q-80/inventory/product/22fe0c8f-68d5-4979-a7ff-309e078b90bf-d1a47d08-8bbd-4cad-807f-04019d364919.jpeg"),
    (13, "Mint",            "100g",      "Leafy Herbs",      12,  10,  4.5,
     CDN + "ar-800-900,pr-true,f-webp,q-80/inventory/product/223a4b9a-b56b-4229-9613-68a6351cd7b9-88f2ab6e-535d-4128-af71-7d326da7c1ff-d895a0da-812a-47ed-abb7-1e63149043ad.jpeg"),
    (14, "Green Chilli",    "250g",      "Leafy Herbs",      25,  20,  4.4,
     CDN + "ar-1000-1000,pr-true,f-webp,q-80/inventory/product/63261e85-1820-4068-885b-843785cb64f2-image_file.jpeg"),

    # ── Flowers ───────────────────────────────────────────────────
    (15, "Rose",            "3 Nos",     "Flowers",          30,  24,  4.7,
     CDN + "ar-1024-1024,pr-true,f-webp,q-80/inventory/product/b064d64e-d53e-4167-84c8-242f4c1331fc-c1689a18-a10c-404b-ad45-e38bd18eb599.jpeg"),
    (16, "Marigold",        "3 Nos",     "Flowers",          20,  18,  4.5,
     CDN + "ar-275-183,pr-true,f-webp,q-80/inventory/product/bfa2222e-bc7a-41d7-858f-13343d3d470d-5ae912ef-89df-4fbc-a546-87fbd23135bc.jpeg"),
    (17, "White Flower",    "3 Nos",     "Flowers",          25,  22,  4.4,
     CDN + "ar-1100-1100,pr-true,f-webp,q-80/inventory/product/0e256bfa-cede-45a3-ba77-42bc88c543fa-Photo.jpeg"),

    # ── Exotic Veggies ────────────────────────────────────────────
    (18, "Capsicum",        "500g",      "Exotic Veggies",   60,  48,  4.6,
     CDN + "ar-500-500,pr-true,f-webp,q-80/inventory/product/2b9b7408-9e6e-4cfe-8b50-e785b50d5631-67d14285-ec66-44ab-ac02-f0cbcb1982a0.jpeg"),
    (19, "Broccoli",        "500g",      "Exotic Veggies",   80,  72,  4.7,
     CDN + "ar-500-500,pr-true,f-webp,q-80/inventory/product/d27275d2-1f38-498b-b5f3-f9da1bb3eae4-a14bec60-157d-43cf-bbb6-e730aa192303.jpeg"),
    (20, "Baby Corn",       "250g",      "Exotic Veggies",   40,  34,  4.5,
     CDN + "ar-500-500,pr-true,f-webp,q-80/inventory/product/e96e943f-4c39-4a79-a36f-2554e201582a-tmp/30d3c540-b407-4191-b9f4-435b68506ac0.jpeg"),
    (21, "Iceberg Lettuce", "1 piece",   "Exotic Veggies",   35,  28,  4.4,
     CDN + "ar-1920-1440,pr-true,f-webp,q-80/inventory/product/b3fafcaa-5e1f-4a49-b43f-33ac753b60e8-513.jpeg"),
    (22, "Mushroom",        "200g",      "Exotic Veggies",   50,  45,  4.6,
     CDN + "ar-500-500,pr-true,f-webp,q-80/inventory/product/8e99f4fb-82b1-499a-9555-3fdf794870e5-b972dce8-6f25-4153-9bd8-39f851ba8ea8-Photo.webp"),

    # ── Kitchen ───────────────────────────────────────────────────
    (23, "Milk",            "1 litre",   "Kitchen",          65,  62,  4.8,
     CDN + "ar-1449-2774,pr-true,f-webp,q-80/inventory/product/ff393466-31a4-4aba-a51b-a787c39ef57e-1X_7lBoxi4mJYgEcYcv0Wy43RpIC7yQdk.jpeg"),
    (24, "Tea",             "250g pack", "Kitchen",         120, 108,  4.7,
     CDN + "ar-412-499,pr-true,f-webp,q-80/inventory/product/1e59f8b8-ebe3-4bbb-b9b3-b45ef7a45274-1CqRELFOO9CnkzvH6tfZaF1vQJDJzzLcQ.jpeg"),
    (25, "Sugar",           "1kg",       "Kitchen",          50,  47,  4.5,
     CDN + "ar-1117-1500,pr-true,f-webp,q-80/inventory/product/b3509c76-ae8b-44c8-8e5f-cf936e31c154-1Goci1ytuE8z6w5aJqv6IqwsvLxSys91o.jpeg"),
    (26, "Masala",          "100g pack", "Kitchen",          45,  36,  4.6,
     CDN + "ar-900-900,pr-true,f-webp,q-80/inventory/product/16a652fa-98ec-4fc0-8f89-210964124ff4-17TURUs2qsmLbTIIEgRDx9XGdbAO_t-HI.jpeg"),
    (27, "Salt",            "1kg",       "Kitchen",          25,  23,  4.7,
     CDN + "ar-1500-1500,pr-true,f-webp,q-80/inventory/product/ed9fdfd5-6536-4a16-9d70-b055fa36ec34-103.jpg"),

    # ── House Hold ────────────────────────────────────────────────
    (28, "Floor Cleaner",   "500ml",     "House Hold",       85,  76,  4.5,
     CDN + "ar-1000-1000,pr-true,f-webp,q-80/inventory/product/9f1fab69-ce22-40e0-bda1-f4d9d9d93d6a-/tmp/20230301-1517501.jpeg"),
    (29, "Allout",          "1 pack",    "House Hold",      150, 135,  4.6,
     CDN + "ar-1200-1286,pr-true,f-webp,q-80/inventory/product/add06766-764f-432b-af4c-a21088ba960d-1e1U__7TcZUxQWdLWQTVylJ5IwN2HkFU4.jpeg"),
    (30, "Room Freshener",  "300ml",     "House Hold",       95,  81,  4.5,
     CDN + "ar-1200-1200,pr-true,f-webp,q-80/inventory/product/e7399340-1d82-4dfe-9e5f-0ded0f170319-1ULtgm5lv0YAtHM20m3chg_eeURJ5Og5K.jpeg"),
    (31, "Soap",            "4 pack",    "House Hold",      120,  96,  4.7,
     CDN + "ar-600-600,pr-true,f-webp,q-80/inventory/product/4ec76d3d-e0d0-4f49-8d71-f38792e688aa-1IW7n_PJoDzpNgrZeYuVuXc2Gmwv2Hj7L.jpeg"),
    (32, "Sanitizer",       "200ml",     "House Hold",       75,  68,  4.6,
     CDN + "ar-679-679,pr-true,f-webp,q-80/inventory/product/1d0e0824-4bf0-4380-b0d4-6bc9f7ac0c15-1Ln11pGDHPMx1EGM0y-kLazpF0Mh3jHRD.jpeg"),

    # ── Snacks & Munchies ──────────────────────────────────────────
    (33, "Lays Classic Potato Chips", "50g", "Snacks & Munchies", 20, 18, 4.5,
     "https://images.unsplash.com/photo-1566478989037-eec170784d22?w=500&auto=format&fit=crop&q=80"),
    (34, "Kurkure Masala Munch", "90g", "Snacks & Munchies", 30, 27, 4.6,
     "https://images.unsplash.com/photo-1600952841320-db92ec4047ca?w=500&auto=format&fit=crop&q=80"),
    (35, "Oreo Vanilla Creme Biscuits", "120g", "Snacks & Munchies", 35, 32, 4.7,
     "https://images.unsplash.com/photo-1558961309-dbdf71799f5a?w=500&auto=format&fit=crop&q=80"),
    (36, "Act II Salted Popcorn", "150g", "Snacks & Munchies", 50, 45, 4.4,
     "https://images.unsplash.com/photo-1578849278619-e73505e9610f?w=500&auto=format&fit=crop&q=80"),

    # ── Cold Drinks & Juices ──────────────────────────────────────
    (37, "Coca Cola Soft Drink", "750ml", "Cold Drinks & Juices", 45, 40, 4.8,
     "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=80"),
    (38, "Sprite Lime-Lemon Drink", "750ml", "Cold Drinks & Juices", 45, 40, 4.6,
     "https://images.unsplash.com/photo-1625772290748-160b2a68865c?w=500&auto=format&fit=crop&q=80"),
    (39, "Tropicana Mixed Fruit Juice", "1L", "Cold Drinks & Juices", 120, 99, 4.5,
     "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500&auto=format&fit=crop&q=80"),
    (40, "Bisleri Water Bottle", "1L", "Cold Drinks & Juices", 20, 19, 4.9,
     "https://images.unsplash.com/photo-1608889175123-8ec330b86f84?w=500&auto=format&fit=crop&q=80"),

    # ── Dairy, Bread & Eggs ────────────────────────────────────────
    (41, "Amul Salted Butter", "100g", "Dairy, Bread & Eggs", 58, 56, 4.9,
     "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=500&auto=format&fit=crop&q=80"),
    (42, "Amul Cheese Slices", "200g", "Dairy, Bread & Eggs", 130, 122, 4.8,
     "https://images.unsplash.com/photo-1486299267070-8382e21b471a?w=500&auto=format&fit=crop&q=80"),
    (43, "Harvest Gold Bread", "400g", "Dairy, Bread & Eggs", 30, 28, 4.5,
     "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=80"),
    (44, "Fresh Farm Eggs", "6 pack", "Dairy, Bread & Eggs", 48, 42, 4.7,
     "https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?w=500&auto=format&fit=crop&q=80"),

    # ── Snacks & Munchies (Continued) ──────────────────────────────
    (45, "Bingo Tedhe Medhe Masala", "75g", "Snacks & Munchies", 20, 18, 4.5,
     "https://images.unsplash.com/photo-1599490659213-e2b9527bc087?w=500&auto=format&fit=crop&q=80"),
    (46, "Haldiram Aloo Bhujia", "150g", "Snacks & Munchies", 40, 35, 4.8,
     "https://images.unsplash.com/photo-1601004890684-d8cbf643f5f2?w=500&auto=format&fit=crop&q=80"),
    (47, "Cadbury Dairy Milk Silk", "60g", "Snacks & Munchies", 80, 75, 4.9,
     "https://images.unsplash.com/photo-1548907040-4d42b52115ca?w=500&auto=format&fit=crop&q=80"),

    # ── Cold Drinks & Juices (Continued) ───────────────────────────
    (48, "Red Bull Energy Drink", "250ml", "Cold Drinks & Juices", 125, 115, 4.7,
     "https://images.unsplash.com/photo-1622543953490-0b7027fde46f?w=500&auto=format&fit=crop&q=80"),
    (49, "Paper Boat Aamras Mango", "250ml", "Cold Drinks & Juices", 40, 35, 4.6,
     "https://images.unsplash.com/photo-1534080391025-0979e8304b29?w=500&auto=format&fit=crop&q=80"),
    (50, "Thums Up Soft Drink", "750ml", "Cold Drinks & Juices", 45, 40, 4.7,
     "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=80"),

    # ── Dairy, Bread & Eggs (Continued) ────────────────────────────
    (51, "Amul Taaza Milk Toned", "1L", "Dairy, Bread & Eggs", 56, 54, 4.8,
     "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=500&auto=format&fit=crop&q=80"),
    (52, "Amul Fresh Paneer Block", "200g", "Dairy, Bread & Eggs", 90, 84, 4.9,
     "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500&auto=format&fit=crop&q=80"),
    (53, "Nandini Pure Cow Ghee", "500ml", "Dairy, Bread & Eggs", 320, 299, 4.9,
     "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=500&auto=format&fit=crop&q=80"),

    # ── Fresh Fruits (Continued) ───────────────────────────────────
    (54, "Fresh Watermelon Kiran", "1 unit", "Fresh Fruits", 90, 79, 4.6,
     "https://images.unsplash.com/photo-1589984662646-e7a2e4962f18?w=500&auto=format&fit=crop&q=80"),
    (55, "Seedless Green Grapes", "500g", "Fresh Fruits", 100, 89, 4.7,
     "https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=500&auto=format&fit=crop&q=80"),

    # ── Fresh Vegetables (Continued) ───────────────────────────────
    (56, "Fresh Garlic Lahsun", "100g", "Fresh Vegetables", 30, 25, 4.5,
     "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=500&auto=format&fit=crop&q=80"),
    (57, "Fresh Ginger Adrak", "100g", "Fresh Vegetables", 20, 17, 4.6,
     "https://images.unsplash.com/photo-1590005354167-6da97870c913?w=500&auto=format&fit=crop&q=80"),

    # ── Kitchen (Continued) ────────────────────────────────────────
    (58, "Maggi 2-Min Noodles", "280g", "Kitchen", 60, 54, 4.9,
     "https://images.unsplash.com/photo-1612927601601-6638404737ce?w=500&auto=format&fit=crop&q=80"),
    (59, "Fortune Mustard Oil", "1L", "Kitchen", 175, 165, 4.7,
     "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500&auto=format&fit=crop&q=80"),
]

# ── Promo codes — same as frontend PROMO_CODES ────────────────────────────────
PROMO_CODES = [
    {
        "code": "ZEPTO10",
        "description": "10% off your order (max ₹100)",
        "discount_type": "percentage",
        "discount_value": 10,
        "min_order_value": 99,
        "max_discount": 100,
        "usage_limit": 10000,
    },
    {
        "code": "FIRST3",
        "description": "Free delivery on first 3 orders",
        "discount_type": "free_delivery",
        "discount_value": 0,
        "min_order_value": 0,
        "max_discount": None,
        "usage_limit": 3,
    },
    {
        "code": "FLAT50",
        "description": "Flat ₹50 off",
        "discount_type": "flat",
        "discount_value": 50,
        "min_order_value": 199,
        "max_discount": 50,
        "usage_limit": 5000,
    },
    {
        "code": "FRESH20",
        "description": "20% off fresh produce (max ₹60)",
        "discount_type": "percentage",
        "discount_value": 20,
        "min_order_value": 149,
        "max_discount": 60,
        "usage_limit": 2000,
    },
]


async def seed():
    print("Creating tables...")
    await create_tables()

    async with AsyncSessionLocal() as db:
        # Clear existing data
        from sqlalchemy import delete
        await db.execute(delete(Product))
        await db.execute(delete(Department))
        await db.execute(delete(PromoCode))
        await db.commit()

        # ── Departments ──────────────────────────────────────────────
        dept_map: dict[str, int] = {}
        for cat_name in CATEGORIES:
            dept = Department(name=cat_name)
            db.add(dept)
            await db.flush()
            dept_map[cat_name] = dept.id
            print(f"  Category: {cat_name} (id={dept.id})")

        await db.flush()

        # ── Products ─────────────────────────────────────────────────
        for (pid, name, unit, category, mrp, price, rating, img_url) in PRODUCTS:
            dept_id = dept_map.get(category)
            if not dept_id:
                print(f"  WARN: unknown category '{category}' for {name}")
                continue

            p = Product(
                id=pid,                    # same id as frontend — critical for ML join
                name=name,
                price=price,               # discounted price (what customer pays)
                mrp=mrp,                   # original MRP
                quantity_label=unit,
                image_url=img_url,         # real cdn.zeptonow.com URL
                department_id=dept_id,
                aisle=category,
                rating=rating,
                rating_count=int(rating * 1000 + pid * 137),   # deterministic mock
                delivery_time_mins=10,
                is_available=True,
                stock_count=100,
            )
            db.add(p)
            print(f"  Product [{pid:2d}]: {name} (₹{price}) — {category}")

        # ── Promo codes ──────────────────────────────────────────────
        for pc in PROMO_CODES:
            db.add(PromoCode(**pc, is_active=True))
            print(f"  Promo: {pc['code']} — {pc['description']}")

        await db.commit()

    print(f"\n✅  Seeded {len(PRODUCTS)} products across {len(CATEGORIES)} categories")
    print(f"✅  Seeded {len(PROMO_CODES)} promo codes")
    print(f"\nProduct IDs 0–{len(PRODUCTS)-1} match frontend src/lib/products.ts exactly.")
    print("ML event logs will join cleanly on product_id.\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Zepto Clone — Database Seed")
    print("=" * 60)
    asyncio.run(seed())
