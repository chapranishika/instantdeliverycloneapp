"""
Notebook 01 - Exploratory Data Analysis
Instacart Market Basket Dataset
Run: jupyter nbconvert --to notebook --execute 01_eda.py
Or just run cells in Jupyter after converting with p2j
"""

# ============================================================
# CELL 1 - Imports & Setup
# ============================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

DATA_DIR = Path("../backend/data/raw")
PROCESSED_DIR = Path("../backend/data/processed")
PROCESSED_DIR.mkdir(exist_ok=True)

print("Libraries loaded. Using Instacart dataset.")
print("Download from: https://www.kaggle.com/c/instacart-market-basket-analysis/data")

# ============================================================
# CELL 2 - Load Data
# ============================================================
def load_instacart_data():
    """Load all Instacart CSV files."""
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    order_products_train = pd.read_csv(DATA_DIR / "order_products__train.csv")
    order_products_prior = pd.read_csv(DATA_DIR / "order_products__prior.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    departments = pd.read_csv(DATA_DIR / "departments.csv")
    aisles = pd.read_csv(DATA_DIR / "aisles.csv")

    # Merge all order products
    order_products = pd.concat([order_products_prior, order_products_train], ignore_index=True)

    # Enrich products
    products = products.merge(departments, on="department_id")
    products = products.merge(aisles, on="aisle_id")

    print(f"Orders:           {orders.shape[0]:,}")
    print(f"Users:            {orders['user_id'].nunique():,}")
    print(f"Products:         {products.shape[0]:,}")
    print(f"Order-products:   {order_products.shape[0]:,}")
    print(f"Departments:      {departments.shape[0]}")

    return orders, order_products, products, departments, aisles

orders, order_products, products, departments, aisles = load_instacart_data()

# ============================================================
# CELL 3 - Generate Synthetic Data (if Kaggle data not present)
# ============================================================
def generate_synthetic_data(n_users=5000, n_products=500, n_orders=50000):
    """
    Generate realistic synthetic Instacart-style data for development.
    Use real Kaggle data for final training.
    """
    np.random.seed(42)
    rng = np.random.default_rng(42)

    dept_names = ["produce", "dairy eggs", "snacks", "beverages", "frozen",
                  "bakery", "meat seafood", "household", "personal care",
                  "pantry", "breakfast", "canned goods"]
    dept_ids = list(range(1, len(dept_names) + 1))

    departments_df = pd.DataFrame({"department_id": dept_ids, "department": dept_names})

    # Products with realistic names
    product_templates = {
        "produce": ["Organic Bananas", "Bag of Organic Apples", "Organic Baby Spinach",
                    "Organic Avocado", "Strawberries", "Raspberries", "Organic Blueberries",
                    "Organic Cucumber", "Organic Lemon", "Organic Garlic"],
        "dairy eggs": ["Total 2% Greek Yogurt", "Organic Whole Milk", "Free Range Large Eggs",
                       "Unsalted Butter", "String Cheese", "Organic Cream Cheese"],
        "snacks": ["Organic Tortilla Chips", "Popcorn", "Mixed Nuts", "Dark Chocolate",
                   "Granola Bars", "Rice Cakes"],
        "beverages": ["Sparkling Water", "Orange Juice", "Cold Brew Coffee",
                      "Coconut Water", "Kombucha"],
        "frozen": ["Organic Edamame", "Frozen Pizza", "Ice Cream", "Veggie Burgers",
                   "Frozen Berries"],
    }

    prod_rows = []
    pid = 1
    for dept_id, dept_name in zip(dept_ids, dept_names):
        templates = product_templates.get(dept_name, [f"{dept_name} item {i}" for i in range(8)])
        for i in range(n_products // len(dept_names)):
            name = templates[i % len(templates)] if i < len(templates) else f"{templates[0]} {i}"
            price = round(rng.uniform(15, 250), 2)
            prod_rows.append({"product_id": pid, "product_name": name,
                               "department_id": dept_id, "aisle_id": dept_id,
                               "price": price, "department": dept_name, "aisle": dept_name})
            pid += 1

    products_df = pd.DataFrame(prod_rows)

    # Orders
    user_ids = rng.integers(1, n_users + 1, size=n_orders)
    order_ids = np.arange(1, n_orders + 1)
    dow = rng.integers(0, 7, size=n_orders)
    hour = rng.integers(6, 23, size=n_orders)

    orders_df = pd.DataFrame({
        "order_id": order_ids,
        "user_id": user_ids,
        "order_dow": dow,
        "order_hour_of_day": hour,
        "days_since_prior_order": rng.integers(0, 30, size=n_orders),
        "eval_set": rng.choice(["prior", "train"], size=n_orders, p=[0.9, 0.1])
    })

    # Simulate purchase behaviour - popular products bought more
    product_popularity = rng.exponential(1.0, size=len(products_df))
    product_popularity /= product_popularity.sum()

    op_rows = []
    for oid in order_ids:
        basket_size = rng.integers(2, 15)
        chosen = rng.choice(products_df["product_id"].values, size=basket_size,
                            replace=False, p=product_popularity)
        for pos, prod in enumerate(chosen):
            op_rows.append({
                "order_id": oid,
                "product_id": int(prod),
                "add_to_cart_order": pos + 1,
                "reordered": int(rng.random() > 0.6)
            })

    op_df = pd.DataFrame(op_rows)

    print(f"Generated synthetic: {n_users} users, {len(products_df)} products, "
          f"{n_orders} orders, {len(op_df)} interactions")

    return orders_df, op_df, products_df, departments_df

# Use synthetic if real data not available
if not (DATA_DIR / "orders.csv").exists():
    print("\nKaggle data not found. Using synthetic data for development.")
    orders, order_products, products, departments, _ = generate_synthetic_data()
    aisles = departments.rename(columns={"department": "aisle", "department_id": "aisle_id"})
    # Save synthetic
    DATA_DIR.mkdir(exist_ok=True)
    orders.to_csv(DATA_DIR / "orders.csv", index=False)
    order_products.to_csv(DATA_DIR / "order_products.csv", index=False)
    products.to_csv(DATA_DIR / "products.csv", index=False)

# ============================================================
# CELL 4 - Core EDA: Order Patterns
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Instacart Order Patterns EDA", fontsize=16, fontweight='bold')

# Orders per user distribution
user_order_counts = orders.groupby("user_id").size()
axes[0, 0].hist(user_order_counts.clip(upper=50), bins=50, color="#E91E8C", alpha=0.8, edgecolor='white')
axes[0, 0].set_title("Orders per user (clipped at 50)")
axes[0, 0].set_xlabel("Number of orders")
axes[0, 0].set_ylabel("Users")

# Orders by day of week
dow_map = {0:"Sun",1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat"}
dow_counts = orders["order_dow"].value_counts().sort_index()
axes[0, 1].bar([dow_map[i] for i in dow_counts.index], dow_counts.values,
               color="#534AB7", alpha=0.9, edgecolor='white')
axes[0, 1].set_title("Orders by day of week")
axes[0, 1].set_ylabel("Orders")

# Orders by hour of day
hour_counts = orders["order_hour_of_day"].value_counts().sort_index()
axes[1, 0].plot(hour_counts.index, hour_counts.values, color="#E91E8C", linewidth=2.5, marker='o', markersize=4)
axes[1, 0].fill_between(hour_counts.index, hour_counts.values, alpha=0.15, color="#E91E8C")
axes[1, 0].set_title("Orders by hour of day")
axes[1, 0].set_xlabel("Hour")
axes[1, 0].set_ylabel("Orders")

# Basket size distribution
basket_sizes = order_products.groupby("order_id").size()
axes[1, 1].hist(basket_sizes.clip(upper=30), bins=30, color="#1D9E75", alpha=0.8, edgecolor='white')
axes[1, 1].set_title("Basket size distribution")
axes[1, 1].set_xlabel("Items per order")
axes[1, 1].set_ylabel("Orders")
axes[1, 1].axvline(basket_sizes.median(), color='red', linestyle='--', linewidth=1.5,
                   label=f"Median: {basket_sizes.median():.0f}")
axes[1, 1].legend()

plt.tight_layout()
plt.savefig(PROCESSED_DIR / "eda_order_patterns.png", dpi=150, bbox_inches='tight')
plt.show()

print(f"\nKey stats:")
print(f"  Median basket size:     {basket_sizes.median():.0f} items")
print(f"  Mean basket size:       {basket_sizes.mean():.1f} items")
print(f"  Median orders/user:     {user_order_counts.median():.0f}")
print(f"  Reorder rate:           {order_products['reordered'].mean():.1%}")

# ============================================================
# CELL 5 - Product Analysis
# ============================================================
product_purchase_counts = (
    order_products.groupby("product_id").size()
    .reset_index(name="purchase_count")
    .merge(products[["product_id","product_name","department"]], on="product_id")
    .sort_values("purchase_count", ascending=False)
)

print("\nTop 20 most purchased products:")
print(product_purchase_counts.head(20)[["product_name","department","purchase_count"]].to_string(index=False))

# Department share
dept_share = (
    order_products.merge(products[["product_id","department"]], on="product_id")
    .groupby("department").size().sort_values(ascending=False)
)

fig, ax = plt.subplots(figsize=(12, 5))
dept_share.head(15).plot(kind='bar', ax=ax, color="#E91E8C", alpha=0.85, edgecolor='white')
ax.set_title("Purchase volume by department", fontsize=13, fontweight='bold')
ax.set_xlabel("Department")
ax.set_ylabel("Total purchases")
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig(PROCESSED_DIR / "eda_department_share.png", dpi=150, bbox_inches='tight')
plt.show()

# ============================================================
# CELL 6 - Build Interaction Matrix & Save
# ============================================================
# Join orders + order_products to get user_id per interaction
interactions = order_products.merge(orders[["order_id","user_id"]], on="order_id")

# User-item interaction matrix: purchase_count per (user, product)
user_item = (
    interactions.groupby(["user_id","product_id"]).size()
    .reset_index(name="purchase_count")
)

# Sparsity analysis
n_users = user_item["user_id"].nunique()
n_items = user_item["product_id"].nunique()
n_interactions = len(user_item)
sparsity = 1 - n_interactions / (n_users * n_items)

print(f"\nInteraction matrix stats:")
print(f"  Users:        {n_users:,}")
print(f"  Products:     {n_items:,}")
print(f"  Interactions: {n_interactions:,}")
print(f"  Sparsity:     {sparsity:.4%}")

# Filter: keep users with >= 5 interactions, products with >= 10 interactions
active_users = user_item.groupby("user_id")["purchase_count"].sum()
active_users = active_users[active_users >= 5].index
frequent_products = user_item.groupby("product_id")["purchase_count"].sum()
frequent_products = frequent_products[frequent_products >= 10].index

user_item_filtered = user_item[
    user_item["user_id"].isin(active_users) &
    user_item["product_id"].isin(frequent_products)
].copy()

print(f"\nAfter filtering:")
print(f"  Users:        {user_item_filtered['user_id'].nunique():,}")
print(f"  Products:     {user_item_filtered['product_id'].nunique():,}")
print(f"  Interactions: {len(user_item_filtered):,}")

# Save
user_item_filtered.to_parquet(PROCESSED_DIR / "user_item_interactions.parquet", index=False)
products.to_parquet(PROCESSED_DIR / "products_enriched.parquet", index=False)
product_purchase_counts.to_parquet(PROCESSED_DIR / "product_popularity.parquet", index=False)

print(f"\nSaved to {PROCESSED_DIR}")
print("EDA complete. Run 02_collaborative_filtering.py next.")
