"""
generate_large_catalog.py
=========================
Programmatically generates 5,060 unique products across 11 categories (including Zepto Cafe).
- Maps each item name to its exact correct image URL (no more apples as sweet potatoes!).
- Seeds the SQLite database (zepto.db) using fast bulk inserts.
- Writes products.ts for the React frontend and products.json for the ML scripts.
"""

import sys
import json
import random
from pathlib import Path
import sqlite3

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "backend" / "zepto.db"
FRONTEND_TS_PATH = ROOT / "frontend" / "src" / "lib" / "products.ts"
JSON_OUT_PATH = ROOT / "backend" / "data" / "processed" / "products.json"

random.seed(42)

# ── Categories Config ──
CATEGORIES = [
    { "type": "Fresh Fruits",    "emoji": "🍎", "color": "#FF6B6B", "icon": "fruit"    },
    { "type": "Fresh Vegetables","emoji": "🥕", "color": "#00A86B", "icon": "veg"      },
    { "type": "Leafy Herbs",     "emoji": "🌿", "color": "#22C55E", "icon": "herbs"    },
    { "type": "Flowers",         "emoji": "🌸", "color": "#EC4899", "icon": "flowers"  },
    { "type": "Exotic Veggies",  "emoji": "🥒", "color": "#8B5CF6", "icon": "exotic"   },
    { "type": "Kitchen",         "emoji": "🥛", "color": "#F59E0B", "icon": "kitchen"  },
    { "type": "House Hold",      "emoji": "🧽", "color": "#3B82F6", "icon": "household"},
    { "type": "Snacks & Munchies", "emoji": "🍿", "color": "#F97316", "icon": "snacks"  },
    { "type": "Cold Drinks & Juices", "emoji": "🥤", "color": "#06B6D4", "icon": "drinks" },
    { "type": "Dairy, Bread & Eggs", "emoji": "🧀", "color": "#EAB308", "icon": "dairy"  },
    { "type": "Zepto Cafe",      "emoji": "☕", "color": "#8B4513", "icon": "cafe"   },
]

CAT_GENERATOR_CONFIG = {
    "Fresh Fruits": {
        "items": ["Apple", "Banana", "Mango", "Orange", "Papaya", "Watermelon", "Grapes", "Pomegranate", "Pineapple", "Guava", "Kiwi", "Pear", "Plum", "Peach", "Coconut", "Strawberry", "Muskmelon", "Dragonfruit", "Figs", "Apricots", "Custard Apple", "Sweet Lime", "Cherry"],
        "brands": ["Freshness", "Zespri", "Organic Farm", "Nature's Gift", "Premium Select", "Safe Harvest", "Farm Fresh", "YumFruit", "GreenLife"],
        "variants": ["Royal Gala", "Shimla Premium", "Alphonso Export", "Kesar Sweet", "Nagpur Juicy", "Coorg Special", "Seedless Green", "Red Globe", "Taiwan Red", "Kiran Sweet", "Imported Golden", "Standard", "Organic Cleaned", "Honey Sweet"],
        "units": ["1kg", "500g", "1 unit", "1 pack (4 Nos)", "250g"],
        "price_range": (30, 299),
    },
    "Fresh Vegetables": {
        "items": ["Onion", "Potato", "Tomato", "Cauliflower", "Bottle Gourd", "Cabbage", "Lady Finger", "Brinjal", "Bitter Gourd", "Ridge Gourd", "Cucumber", "Carrot", "Radish", "Beetroot", "Sweet Potato", "Pumpkin", "Beans", "Peas", "Colocasia", "Drumstick"],
        "brands": ["Farm Fresh", "Organic India", "Daily Harvest", "Green Earth", "Natural Growers", "PureVegetables", "ValleyPride"],
        "variants": ["Red Nashik", "Agra Special", "Desi Ripe", "Hybrid Green", "Tender Local", "Fresh Cut", "Premium Cleaned", "Organic Selected", "Hill Grown"],
        "units": ["1kg", "500g", "250g", "1 unit"],
        "price_range": (15, 110),
    },
    "Leafy Herbs": {
        "items": ["Spinach", "Coriander", "Curry Leaves", "Mint", "Green Chilli", "Lemongrass", "Methi Fenugreek", "Palak", "Dill Leaves", "Spring Onion", "Basil", "Parsley", "Thyme", "Oregano"],
        "brands": ["Green Leaf", "Fresh Herbs", "Organic Meadows", "Sprout & Herb", "Urban Farms"],
        "variants": ["Triple Washed", "Aromatic Green", "Fiery Spicy", "Tender Organic", "Hydroponic Premium", "Local Natural"],
        "units": ["100g", "50g", "250g", "500g"],
        "price_range": (8, 50),
    },
    "Flowers": {
        "items": ["Rose", "Marigold", "White Flower", "Jasmine", "Hibiscus", "Lotus", "Carnations", "Gerberas", "Orchids", "Lilies", "Sunflowers", "Chrysanthemum"],
        "brands": ["Puja Special", "Fragrant Blooms", "Devotional Flowers", "Florist Select", "TempleOfferings"],
        "variants": ["Red Puja Premium", "Yellow Garland Hand-knotted", "White Serene Devotional", "Assorted Puja Mix Special", "Fresh Cut Gifting Luxury", "Orange Garland"],
        "units": ["3 Nos", "1 pack (100g)", "1 unit", "12 Nos bouquet", "500g garland"],
        "price_range": (15, 399),
    },
    "Exotic Veggies": {
        "items": ["Capsicum", "Broccoli", "Baby Corn", "Iceberg Lettuce", "Mushroom", "Zucchini", "Cherry Tomatoes", "Asparagus", "Avocado", "Red Cabbage", "Brussels Sprouts", "Celery", "Leek", "Sweet Pepper"],
        "brands": ["Gourmet Select", "Exotic Greens", "Greenhouse Premium", "Imported Harvest", "FineDineVeg"],
        "variants": ["Yellow Bell Juicy", "Red Bell Sweet", "Green Crisp Fresh", "Tender Imported Select", "Button Fresh White", "Portobello Large", "Hydroponic Crunchy"],
        "units": ["250g", "500g", "1 unit", "200g pack"],
        "price_range": (35, 250),
    },
    "Kitchen": {
        "items": ["Milk", "Tea", "Sugar", "Masala", "Salt", "Atta Flour", "Rice Basmati", "Toor Dal", "Mustard Oil", "Ghee", "Noodles", "Ketchup", "Honey", "Pickle", "Pasta", "Salt Pink", "Olive Oil", "Soy Sauce", "Poha Flat Rice", "Besan Gram Flour"],
        "brands": ["Amul", "Tata", "Aashirvaad", "Fortune", "Maggi", "Kissan", "Dabur", "Patanjali", "Red Label", "Taj Mahal", "Catch", "Everest", "Rajdhani"],
        "variants": ["Premium Quality", "Iodized Healthy", "Whole Wheat Sharbati", "Long Grain Classic", "Kachi Ghani Cold-pressed", "Cow Ghee A2", "Masala Instant Noodles", "Tomato Ketchup Tangy", "Pure Organic Raw", "Poha Thick"],
        "units": ["1kg", "1 litre", "250g", "500g", "5kg bag", "4 pack", "200g"],
        "price_range": (20, 699),
    },
    "House Hold": {
        "items": ["Floor Cleaner", "Allout", "Room Freshener", "Soap", "Sanitizer", "Dishwash Liquid", "Detergent Powder", "Toilet Cleaner", "Garbage Bags", "Kitchen Roll", "Tissues", "Handwash Refill", "Scrub Pad", "Glass Cleaner"],
        "brands": ["Lizol", "Surf Excel", "Harpic", "Pril", "Comfort", "Godrej", "Allout", "Dettol", "Selpak", "Vim", "Colin"],
        "variants": ["Citrus Fresh Active", "Lavender Mist Soothing", "Lemon Power Grease Buster", "Germ Protection Safe", "Eucalyptus Fragrant", "Ultra Whitening Power", "Rose Fresh Gentle", "Assorted pack"],
        "units": ["500ml", "1 pack", "300ml", "4 pack", "200ml", "1L bottle", "1kg pack"],
        "price_range": (35, 450),
    },
    "Snacks & Munchies": {
        "items": ["Potato Chips", "Puffed Snacks", "Cookies", "Popcorn", "Chocolates", "Biscuits", "Namkeen", "Bhujia", "Nachos", "Tortilla Chips", "Peanuts", "Wafers", "Choco Fudge", "Pop Rings", "Corn Chips"],
        "brands": ["Lays", "Kurkure", "Bingo", "Haldiram", "Pringles", "Doritos", "Cadbury", "Amul", "Oreo", "Act II", "Britannia", "Parle", "Sunfeast", "Unibic"],
        "variants": ["Classic Salted Original", "Masala Munch Tangy", "Tomato Tangy Spicy", "Sour Cream Onion Premium", "Cream & Onion Savory", "Cheddar Cheese Rich", "Butter Salted Crunchy", "Dark Cocoa Smooth", "Chocolate Mint Delicacy", "Spicy Chilli Fiery", "Barbeque Smoky", "Peri Peri Hot", "Pudina Chatpata Local"],
        "units": ["50g", "75g", "100g", "150g", "200g"],
        "price_range": (10, 199),
    },
    "Cold Drinks & Juices": {
        "items": ["Soft Drink", "Soda", "Energy Drink", "Mango Drink", "Fruit Juice", "Mineral Water", "Tonic Water", "Ginger Ale", "Coconut Water", "Lemonade Drink", "Apple Cider"],
        "brands": ["Coca Cola", "Pepsi", "Sprite", "Thums Up", "Red Bull", "Paper Boat", "Tropicana", "Real", "Bisleri", "Schweppes", "Raw Pressery", "Fanta"],
        "variants": ["Original Taste Classic", "Zero Sugar Diet", "Lime Lemon Refreshing", "Charged Spicy Cola", "Classic Energy Booster", "Aamras Mango Pulp", "Mixed Fruit Nectar", "Orange Pulp Sweet", "Pure Mineral Water", "Club Soda Carbonated"],
        "units": ["750ml", "250ml", "1L", "500ml", "2L bottle"],
        "price_range": (20, 180),
    },
    "Dairy, Bread & Eggs": {
        "items": ["Butter", "Cheese Slices", "White Bread", "Farm Eggs", "Toned Milk", "Paneer Block", "Cow Ghee", "Yogurt Cup", "Curd Pack", "Brown Bread", "Mozzarella Cheese", "Buttermilk Packet"],
        "brands": ["Amul", "Nandini", "Mother Dairy", "Britannia", "Harvest Gold", "English Oven", "Epigamia", "Gowardhan"],
        "variants": ["Pasteurized Salted Cream", "Processed Cheese Slices", "Fresh Baked Sandwich Bread", "High Protein Farm Eggs", "Toned Fresh Milk", "Soft Cottage Cheese Paneer", "Pure Clarified Ghee", "Mango Yogurt Creamy", "Desi Curd Natural", "Whole Wheat Brown Bread"],
        "units": ["100g", "200g", "400g", "6 pack", "1L", "500ml", "150g cup"],
        "price_range": (20, 499),
    },
    "Zepto Cafe": {
        "items": ["Cappuccino", "Cafe Latte", "Cold Coffee", "Filter Coffee", "Hot Chocolate", "Masala Chai", "Ginger Tea", "Veg Samosa", "Amul Bun Maska", "Paneer Tikka Sandwich", "Cheese Corn Grilled Sandwich", "Butter Croissant", "Chocolate Croissant", "Veg Puff", "Paneer Puff", "Egg Puff", "Chocolate Chip Cookie", "Fudge Brownie", "Banana Walnut Cake", "Blueberry Muffin", "Cardamom Tea", "Espresso Shot", "Iced Americano"],
        "brands": ["Zepto Cafe", "Chaayos Special", "Blue Tokai Roast", "Le15 Patisserie", "Sassy Teaspoon", "Third Wave Co."],
        "variants": ["Hot Brewing", "Chilled Creamy", "Freshly Baked", "Spicy Indian", "Melt-in-mouth", "Golden Crispy", "Classic", "Premium Gourmet", "Artisanal Crafted"],
        "units": ["1 cup", "250ml", "1 unit", "Pack of 2", "150g", "1 serving"],
        "price_range": (35, 260),
    }
}

PREFIXES = ["", "Organic", "Premium Select", "Natural", "Farm Fresh", "Pure", "Gourmet", "Freshly Handpicked", "Artisanal", "Heritage", "Standard"]

def get_image_for_product(category: str, name: str) -> str:
    lower_name = name.lower()
    
    # 1. Fresh Fruits
    if category == "Fresh Fruits":
        if "apple" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-500-500,pr-true,f-webp,q-80/inventory/product/0e673bd2-2fe6-4d8e-899e-00b4d460a653-tmp/a87d6c85-8184-428d-a877-070f4f55ffb5.jpeg"
        if "banana" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-425-405,pr-true,f-webp,q-80/inventory/product/cb115d55-cf65-4228-80c8-b0fc0b90ae03-/tmp/20230216-1551351.jpeg"
        if "mango" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-478-522,pr-true,f-webp,q-80/inventory/product/1b9cf6b1-9a9d-41a7-ace5-0faec8e3e71f-image_file.png"
        if "orange" in lower_name or "lime" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-187-187,pr-true,f-webp,q-80/inventory/product/6c78cf1a-ed30-4d24-8def-a274418a27ea-image"
        if "papaya" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1000-799,pr-true,f-webp,q-80/inventory/product/de957e5c-6ef2-4b20-831f-4ec31fcb4c3d-image_file.jpeg"
        if "watermelon" in lower_name or "muskmelon" in lower_name:
            return "https://images.unsplash.com/photo-1589984662646-e7a2e4962f18?w=500&auto=format&fit=crop&q=80"
        if "grapes" in lower_name:
            return "https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=500&auto=format&fit=crop&q=80"
        if "strawberry" in lower_name or "cherry" in lower_name or "berry" in lower_name:
            return "https://images.unsplash.com/photo-1464965911861-746a04b4bca6?w=500&auto=format&fit=crop&q=80"
        if "pineapple" in lower_name:
            return "https://images.unsplash.com/photo-1550258987-190a2d41a8ba?w=500&auto=format&fit=crop&q=80"
        if "coconut" in lower_name:
            return "https://images.unsplash.com/photo-1525385133772-2abdff267862?w=500&auto=format&fit=crop&q=80"
        if "pomegranate" in lower_name:
            return "https://images.unsplash.com/photo-1527844007623-1d0172e2cf3d?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1610348725531-843dff563e2c?w=500&auto=format&fit=crop&q=80"
        
    # 2. Fresh Vegetables
    if category == "Fresh Vegetables":
        if "onion" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1200-1200,pr-true,f-webp,q-80/inventory/product/07a54355-4d10-4623-b369-1109db67d160-Photo.jpeg"
        if "sweet potato" in lower_name:
            return "https://images.unsplash.com/photo-1596003906949-67221c37965c?w=500&auto=format&fit=crop&q=80"
        if "potato" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-4745-3537,pr-true,f-webp,q-80/inventory/product/534318fb-a402-4902-9cce-2cbd8984d75b-53.jpeg"
        if "tomato" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1500-1500,pr-true,f-webp,q-80/inventory/product/3a919660-707b-44f4-b666-8b3fcf094a7b-image"
        if "cauliflower" in lower_name or "cabbage" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1000-1000,pr-true,f-webp,q-80/inventory/product/9e5847e4-17a6-4a48-8221-d237f440d995-image"
        if "bottle gourd" in lower_name or "gourd" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-800-500,pr-true,f-webp,q-80/inventory/product/dedf3d96-5fe5-482a-a24a-494f6e76845e-tmp/f3cb8fd8-e2df-4c11-ba79-4203e88af3ad.jpeg"
        if "garlic" in lower_name:
            return "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=500&auto=format&fit=crop&q=80"
        if "ginger" in lower_name:
            return "https://images.unsplash.com/photo-1590005354167-6da97870c913?w=500&auto=format&fit=crop&q=80"
        if "cucumber" in lower_name:
            return "https://images.unsplash.com/photo-1447175008436-054170c2e979?w=500&auto=format&fit=crop&q=80"
        if "beetroot" in lower_name:
            return "https://images.unsplash.com/photo-1590779033100-9f60a05a013d?w=500&auto=format&fit=crop&q=80"
        if "lady finger" in lower_name:
            return "https://images.unsplash.com/photo-1447175008436-054170c2e979?w=500&auto=format&fit=crop&q=80"
        # Fallback veggie image
        return "https://images.unsplash.com/photo-1566385101042-1a0104b7b92f?w=500&auto=format&fit=crop&q=80"

    # 3. Leafy Herbs
    if category == "Leafy Herbs":
        if "spinach" in lower_name or "palak" in lower_name or "methi" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-393-510,pr-true,f-webp,q-80/inventory/product/9abf0781-37d6-4b05-b559-912ab7ce2145-568.jpeg"
        if "chilli" in lower_name or "spring onion" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1000-1000,pr-true,f-webp,q-80/inventory/product/63261e85-1820-4068-885b-843785cb64f2-image_file.jpeg"
        return "https://cdn.zeptonow.com/production///tr:w-450,ar-1500-888,pr-true,f-webp,q-80/inventory/product/6f885126-571a-4655-a9fb-91a6a893928f-4199723a-d43e-4e86-b88d-34289de52bb5-Photo.webp"

    # 4. Flowers
    if category == "Flowers":
        if "rose" in lower_name or "hibiscus" in lower_name or "lily" in lower_name or "lilies" in lower_name or "orchid" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1024-1024,pr-true,f-webp,q-80/inventory/product/b064d64e-d53e-4167-84c8-242f4c1331fc-c1689a18-a10c-404b-ad45-e38bd18eb599.jpeg"
        if "marigold" in lower_name or "sunflower" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-275-183,pr-true,f-webp,q-80/inventory/product/bfa2222e-bc7a-41d7-858f-13343d3d470d-5ae912ef-89df-4fbc-a546-87fbd23135bc.jpeg"
        return "https://cdn.zeptonow.com/production///tr:w-300,ar-1100-1100,pr-true,f-webp,q-80/inventory/product/0e256bfa-cede-45a3-ba77-42bc88c543fa-Photo.jpeg"

    # 5. Exotic Veggies
    if category == "Exotic Veggies":
        if "capsicum" in lower_name or "pepper" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-500-500,pr-true,f-webp,q-80/inventory/product/2b9b7408-9e6e-4cfe-8b50-e785b50d5631-67d14285-ec66-44ab-ac02-f0cbcb1982a0.jpeg"
        if "broccoli" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-500-500,pr-true,f-webp,q-80/inventory/product/d27275d2-1f38-498b-b5f3-f9da1bb3eae4-a14bec60-157d-43cf-bbb6-e730aa192303.jpeg"
        if "baby corn" in lower_name or "zucchini" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-500-500,pr-true,f-webp,q-80/inventory/product/e96e943f-4c39-4a79-a36f-2554e201582a-tmp/30d3c540-b407-4191-b9f4-435b68506ac0.jpeg"
        if "lettuce" in lower_name or "cabbage" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1920-1440,pr-true,f-webp,q-80/inventory/product/b3fafcaa-5e1f-4a49-b43f-33ac753b60e8-513.jpeg"
        if "mushroom" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-500-500,pr-true,f-webp,q-80/inventory/product/8e99f4fb-82b1-499a-9555-3fdf794870e5-b972dce8-6f25-4153-9bd8-39f851ba8ea8-Photo.webp"
        if "avocado" in lower_name:
            return "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1592417817098-8f3d6eb19675?w=500&auto=format&fit=crop&q=80"

    # 6. Kitchen
    if category == "Kitchen":
        if "milk" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1449-2774,pr-true,f-webp,q-80/inventory/product/ff393466-31a4-4aba-a51b-a787c39ef57e-1X_7lBoxi4mJYgEcYcv0Wy43RpIC7yQdk.jpeg"
        if "tea" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-412-499,pr-true,f-webp,q-80/inventory/product/1e59f8b8-ebe3-4bbb-b9b3-b45ef7a45274-1CqRELFOO9CnkzvH6tfZaF1vQJDJzzLcQ.jpeg"
        if "sugar" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1117-1500,pr-true,f-webp,q-80/inventory/product/b3509c76-ae8b-44c8-8e5f-cf936e31c154-1Goci1ytuE8z6w5aJqv6IqwsvLxSys91o.jpeg"
        if "masala" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-900-900,pr-true,f-webp,q-80/inventory/product/16a652fa-98ec-4fc0-8f89-210964124ff4-17TURUs2qsmLbTIIEgRDx9XGdbAO_t-HI.jpeg"
        if "salt" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1500-1500,pr-true,f-webp,q-80/inventory/product/ed9fdfd5-6536-4a16-9d70-b055fa36ec34-103.jpg"
        if "noodles" in lower_name or "pasta" in lower_name:
            return "https://images.unsplash.com/photo-1612927601601-6638404737ce?w=500&auto=format&fit=crop&q=80"
        if "oil" in lower_name or "ghee" in lower_name:
            return "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&auto=format&fit=crop&q=80"

    # 7. House Hold
    if category == "House Hold":
        if "floor" in lower_name or "toilet" in lower_name or "glass" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1000-1000,pr-true,f-webp,q-80/inventory/product/9f1fab69-ce22-40e0-bda1-f4d9d9d93d6a-/tmp/20230301-1517501.jpeg"
        if "detergent" in lower_name or "wash" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1200-1286,pr-true,f-webp,q-80/inventory/product/add06766-764f-432b-af4c-a21088ba960d-1e1U__7TcZUxQWdLWQTVylJ5IwN2HkFU4.jpeg"
        if "allout" in lower_name or "freshener" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-1200-1200,pr-true,f-webp,q-80/inventory/product/e7399340-1d82-4dfe-9e5f-0ded0f170319-1ULtgm5lv0YAtHM20m3chg_eeURJ5Og5K.jpeg"
        if "soap" in lower_name:
            return "https://cdn.zeptonow.com/production///tr:w-300,ar-600-600,pr-true,f-webp,q-80/inventory/product/4ec76d3d-e0d0-4f49-8d71-f38792e688aa-1IW7n_PJoDzpNgrZeYuVuXc2Gmwv2Hj7L.jpeg"
        return "https://cdn.zeptonow.com/production///tr:w-300,ar-679-679,pr-true,f-webp,q-80/inventory/product/1d0e0824-4bf0-4380-b0d4-6bc9f7ac0c15-1Ln11pGDHPMx1EGM0y-kLazpF0Mh3jHRD.jpeg"

    # 8. Snacks & Munchies
    if category == "Snacks & Munchies":
        if "chips" in lower_name or "nachos" in lower_name or "tortilla" in lower_name or "rings" in lower_name:
            return "https://images.unsplash.com/photo-1566478989037-eec170784d22?w=500&auto=format&fit=crop&q=80"
        if "puffs" in lower_name or "savory" in lower_name or "namkeen" in lower_name or "bhujia" in lower_name:
            return "https://images.unsplash.com/photo-1600952841320-db92ec4047ca?w=500&auto=format&fit=crop&q=80"
        if "cookies" in lower_name or "biscuits" in lower_name or "wafers" in lower_name:
            return "https://images.unsplash.com/photo-1558961309-dbdf71799f5a?w=500&auto=format&fit=crop&q=80"
        if "popcorn" in lower_name:
            return "https://images.unsplash.com/photo-1578849278619-e73505e9610f?w=500&auto=format&fit=crop&q=80"
        if "chocolate" in lower_name or "fudge" in lower_name or "silk" in lower_name:
            return "https://images.unsplash.com/photo-1548907040-4d42b52115ca?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1599490659213-e2b9527bc087?w=500&auto=format&fit=crop&q=80"

    # 9. Cold Drinks & Juices
    if category == "Cold Drinks & Juices":
        if "soft drink" in lower_name or "cola" in lower_name or "soda" in lower_name or "fanta" in lower_name or "sprite" in lower_name:
            return "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=80"
        if "juice" in lower_name or "mango" in lower_name or "cider" in lower_name or "lemonade" in lower_name:
            return "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500&auto=format&fit=crop&q=80"
        if "water" in lower_name:
            return "https://images.unsplash.com/photo-1608889175123-8ec330b86f84?w=500&auto=format&fit=crop&q=80"
        if "energy" in lower_name or "red bull" in lower_name:
            return "https://images.unsplash.com/photo-1622543953490-0b7027fde46f?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1625772290748-160b2a68865c?w=500&auto=format&fit=crop&q=80"

    # 10. Dairy, Bread & Eggs
    if category == "Dairy, Bread & Eggs":
        if "butter" in lower_name or "ghee" in lower_name:
            return "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=500&auto=format&fit=crop&q=80"
        if "cheese" in lower_name:
            return "https://images.unsplash.com/photo-1486299267070-8382e21b471a?w=500&auto=format&fit=crop&q=80"
        if "bread" in lower_name:
            return "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=80"
        if "eggs" in lower_name:
            return "https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?w=500&auto=format&fit=crop&q=80"
        if "milk" in lower_name or "toned" in lower_name:
            return "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=500&auto=format&fit=crop&q=80"
        if "paneer" in lower_name or "curd" in lower_name or "yogurt" in lower_name:
            return "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=500&auto=format&fit=crop&q=80"

    # 11. Zepto Cafe
    if category == "Zepto Cafe":
        if "coffee" in lower_name or "cappuccino" in lower_name or "latte" in lower_name or "americano" in lower_name or "espresso" in lower_name:
            return "https://images.unsplash.com/photo-1541167760496-1628856ab772?w=500&auto=format&fit=crop&q=80"
        if "croissant" in lower_name:
            return "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500&auto=format&fit=crop&q=80"
        if "chai" in lower_name or "tea" in lower_name:
            return "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500&auto=format&fit=crop&q=80"
        if "sandwich" in lower_name:
            return "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=500&auto=format&fit=crop&q=80"
        if "samosa" in lower_name or "maska" in lower_name or "puff" in lower_name:
            return "https://images.unsplash.com/photo-1601050690597-df056fb4ce78?w=500&auto=format&fit=crop&q=80"
        if "cookie" in lower_name or "muffin" in lower_name:
            return "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=500&auto=format&fit=crop&q=80"
        if "brownie" in lower_name or "cake" in lower_name:
            return "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=500&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1541167760496-1628856ab772?w=500&auto=format&fit=crop&q=80"

    return "https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&auto=format&fit=crop&q=80"

# ── Generate 5,060 Products ──
print("Generating 5,060 unique products...")
generated_products = []
product_id_counter = 0
seen_names = set()

items_per_category = 460

for cat_info in CATEGORIES:
    category_name = cat_info["type"]
    cfg = CAT_GENERATOR_CONFIG[category_name]
    
    cat_count = 0
    attempts = 0
    
    while cat_count < items_per_category and attempts < 20000:
        attempts += 1
        prefix = random.choice(PREFIXES)
        brand = random.choice(cfg["brands"])
        item = random.choice(cfg["items"])
        variant = random.choice(cfg["variants"])
        unit = random.choice(cfg["units"])
        
        parts = [prefix, brand, variant, item] if prefix else [brand, variant, item]
        name = " ".join(filter(None, parts))
        
        if name in seen_names:
            continue
            
        seen_names.add(name)
        
        mrp = random.randint(cfg["price_range"][0], cfg["price_range"][1])
        discount_pct = random.uniform(0.05, 0.30)
        price = int(mrp * (1 - discount_pct))
        
        if mrp - price < 2 and mrp > 15:
            price = mrp - random.randint(2, 5)
            
        rating = round(random.uniform(4.2, 4.9), 1)
        description = f"High-quality {variant.lower()} {item.lower()} brought to you by {brand}. Sourced responsibly, fresh, and packaged sanitarily."
        
        # Get the EXACT matching image URL for the item type
        image_url = get_image_for_product(category_name, item)
        
        product = {
            "id": product_id_counter,
            "name": name,
            "unit": unit,
            "type": category_name,
            "price": mrp,
            "disc": price,
            "rating": rating,
            "country": "India",
            "description": description,
            "src": image_url,
            "quantity": 0
        }
        
        generated_products.append(product)
        product_id_counter += 1
        cat_count += 1
        
    print(f"  Generated {cat_count} items for category '{category_name}'")

# ── Write products.json (for ML scripts) ──
print(f"Writing JSON catalogue to {JSON_OUT_PATH}...")
JSON_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(JSON_OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(generated_products, f, indent=2)

# ── Write products.ts (for Frontend React) ──
print(f"Writing TS catalogue to {FRONTEND_TS_PATH}...")
FRONTEND_TS_PATH.parent.mkdir(parents=True, exist_ok=True)

trending_ids = random.sample(range(5060), 10)
for_you_ids = random.sample(range(5060), 10)
fresh_ids = random.sample([p["id"] for p in generated_products if "Fruits" in p["type"] or "Vegetables" in p["type"]], 10)
kitchen_hh_ids = random.sample([p["id"] for p in generated_products if "Kitchen" in p["type"] or "House Hold" in p["type"]], 10)

categories_json = json.dumps(CATEGORIES, indent=2)
promo_codes_code = """
export const PROMO_CODES: Record<string, {label: string; type: 'pct'|'flat'|'free_del'; val: number; max: number}> = {
  ZEPTO10:  { label: '10% off (max ₹100)', type: 'pct',      val: 10, max: 100 },
  FIRST3:   { label: 'Free delivery',       type: 'free_del', val: 0,  max: 0   },
  FLAT50:   { label: 'Flat ₹50 off',        type: 'flat',     val: 50, max: 50  },
  FRESH20:  { label: '20% off (max ₹60)',   type: 'pct',      val: 20, max: 60  },
};
"""

with open(FRONTEND_TS_PATH, "w", encoding="utf-8") as f:
    f.write("/**\n * Zepto Clone — Large Product Catalogue (5,060 items generated programmatically)\n */\n\n")
    f.write("export interface Product {\n  id: number;\n  name: string;\n  unit: string;\n  type: string;\n  price: number;\n  disc: number;\n  src: string;\n  quantity: number;\n  rating: number;\n  country: string;\n  description: string;\n}\n\n")
    
    f.write("export const PRODUCTS: Product[] = [\n")
    for p in generated_products:
        escaped_name = p["name"].replace("'", "\\'")
        escaped_desc = p["description"].replace("'", "\\'")
        f.write(f"  {{ id: {p['id']}, name: '{escaped_name}', unit: '{p['unit']}', type: '{p['type']}', price: {p['price']}, disc: {p['disc']}, rating: {p['rating']}, country: '{p['country']}', description: '{escaped_desc}', src: '{p['src']}', quantity: 0 }},\n")
    f.write("];\n\n")
    
    f.write(f"export const CATEGORIES = {categories_json};\n\n")
    f.write("export const TYPES = CATEGORIES.map(c => c.type);\n\n")
    f.write(f"export const TRENDING_IDS = {trending_ids};\n")
    f.write(f"export const FOR_YOU_IDS = {for_you_ids};\n")
    f.write(f"export const FRESH_IDS = {fresh_ids};\n")
    f.write(f"export const KITCHEN_HH_IDS = {kitchen_hh_ids};\n\n")
    f.write(promo_codes_code + "\n")
    f.write("export const getById = (id: number) => PRODUCTS.find(p => p.id === id);\n")
    f.write("export const getByType = (type: string) => PRODUCTS.filter(p => p.type === type);\n")
    f.write("export const discPct = (p: Product) => Math.round((p.price - p.disc) / p.price * 100);\n")
    f.write("export const getCatConf = (type: string) => CATEGORIES.find(c => c.type === type);\n\n")
    f.write("export const MOCK_ORDERS = [\n  { id: 'ZPT1001', date: '2 Jun 2026', total: 172, items: [0, 5, 9], status: 'Delivered' },\n  { id: 'ZPT0988', date: '29 May 2026', total: 263, items: [1, 23, 24], status: 'Delivered' },\n];\n")

print("✓ Static frontend files written successfully!")

# ── Bulk Seed the SQLite Database ──
print(f"Connecting to database at {DB_PATH} for seeding...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Clear and recreate tables
cursor.execute("DROP TABLE IF EXISTS products;")
cursor.execute("DROP TABLE IF EXISTS departments;")
cursor.execute("DROP TABLE IF EXISTS promo_codes;")

cursor.execute("""
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL
);
""")

cursor.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    department_id INTEGER,
    aisle VARCHAR(100),
    price FLOAT NOT NULL,
    mrp FLOAT,
    image_url VARCHAR(500),
    quantity_label VARCHAR(50),
    is_available BOOLEAN DEFAULT 1,
    stock_count INTEGER DEFAULT 100,
    rating FLOAT DEFAULT 4.0,
    rating_count INTEGER DEFAULT 0,
    delivery_time_mins INTEGER DEFAULT 10,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(department_id) REFERENCES departments(id)
);
""")

cursor.execute("""
CREATE TABLE promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,
    discount_value FLOAT NOT NULL,
    min_order_value FLOAT DEFAULT 0.0,
    max_discount FLOAT,
    usage_limit INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1
);
""")

# Insert Departments
print("Inserting departments...")
dept_ids = {}
for i, cat in enumerate(CATEGORIES, 1):
    cursor.execute("INSERT INTO departments (id, name) VALUES (?, ?);", (i, cat["type"]))
    dept_ids[cat["type"]] = i

# Insert Products in bulk
print("Inserting 5,060 products in bulk...")
product_tuples = []
for p in generated_products:
    product_tuples.append((
        p["id"],
        p["name"],
        p["description"],
        dept_ids[p["type"]],
        p["type"],
        p["disc"],      # price = discounted price
        p["price"],     # mrp = original MRP
        p["src"],       # image_url
        p["unit"],      # quantity_label
        1,              # is_available
        100,            # stock_count
        p["rating"],
        int(p["rating"] * 1000 + p["id"] * 137),  # rating_count
        random.choice([8, 10, 12])  # delivery_time_mins
    ))

cursor.executemany("""
INSERT INTO products (
    id, name, description, department_id, aisle, price, mrp, image_url, quantity_label,
    is_available, stock_count, rating, rating_count, delivery_time_mins
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", product_tuples)

# Insert Promo Codes
print("Inserting promo codes...")
promo_codes = [
    ("ZEPTO10", "10% off your order (max ₹100)", "percentage", 10, 99, 100, 10000),
    ("FIRST3", "Free delivery on first 3 orders", "free_delivery", 0, 0, None, 3),
    ("FLAT50", "Flat ₹50 off", "flat", 50, 199, 50, 2000),
    ("FRESH20", "20% off fresh produce (max ₹60)", "percentage", 20, 149, 60, 2000),
]
for pc in promo_codes:
    cursor.execute("""
    INSERT INTO promo_codes (code, description, discount_type, discount_value, min_order_value, max_discount, usage_limit)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, pc)

conn.commit()
conn.close()

print("✓ SQLite database seeded successfully!")
print("============================================================")
print("✅  5,060 PRODUCTS CATALOGUE GENERATION & SEEDING COMPLETE")
print("============================================================")
