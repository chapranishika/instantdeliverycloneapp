"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-06-17

Creates all tables for the Zepto clone:
  - departments (product categories)
  - products
  - users
  - user_events (behavioural events — ML training data)
  - orders + order_items
  - wishlist_items
  - promo_codes

Run: alembic upgrade head
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── departments ───────────────────────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id",   sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id",                sa.Integer(),     nullable=False),
        sa.Column("name",              sa.String(200),   nullable=False),
        sa.Column("price",             sa.Float(),       nullable=False),
        sa.Column("mrp",               sa.Float()),
        sa.Column("quantity_label",    sa.String(50)),
        sa.Column("image_url",         sa.String(500)),
        sa.Column("department_id",     sa.Integer()),
        sa.Column("aisle",             sa.String(100)),
        sa.Column("rating",            sa.Float(),       default=4.5),
        sa.Column("rating_count",      sa.Integer(),     default=0),
        sa.Column("delivery_time_mins",sa.Integer(),     default=10),
        sa.Column("is_available",      sa.Boolean(),     default=True),
        sa.Column("stock_count",       sa.Integer(),     default=100),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_department_id", "products", ["department_id"])

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",            sa.Integer(),    nullable=False),
        sa.Column("email",         sa.String(255),  nullable=False),
        sa.Column("name",          sa.String(200)),
        sa.Column("phone",         sa.String(20)),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("is_active",     sa.Boolean(),    default=True),
        sa.Column("created_at",    sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── user_events (behavioural log — raw ML training signal) ────────────────
    op.create_table(
        "user_events",
        sa.Column("id",          sa.BigInteger(),  nullable=False),
        sa.Column("user_id",     sa.Integer()),    # nullable: anonymous OK
        sa.Column("product_id",  sa.Integer()),
        sa.Column("event_type",  sa.String(50),   nullable=False),
        sa.Column("query",       sa.String(300)),
        sa.Column("page",        sa.String(100)),
        sa.Column("session_id",  sa.String(100)),
        sa.Column("ab_variant",  sa.String(50)),
        sa.Column("created_at",  sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_user_id",    "user_events", ["user_id"])
    op.create_index("ix_user_events_product_id", "user_events", ["product_id"])
    op.create_index("ix_user_events_session_id", "user_events", ["session_id"])
    op.create_index("ix_user_events_created_at", "user_events", ["created_at"])

    # ── orders ────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id",             sa.Integer(),  nullable=False),
        sa.Column("user_id",        sa.Integer()),
        sa.Column("status",         sa.String(50), default="placed"),
        sa.Column("total_amount",   sa.Float()),
        sa.Column("delivery_address", sa.String(500)),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("promo_code",     sa.String(50)),
        sa.Column("discount_amount",sa.Float(),   default=0),
        sa.Column("rider_id",       sa.Integer()),
        sa.Column("eta_minutes",    sa.Integer()),
        sa.Column("placed_at",      sa.DateTime()),
        sa.Column("delivered_at",   sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    # ── order_items ───────────────────────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("order_id",   sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("quantity",   sa.Integer()),
        sa.Column("unit_price", sa.Float()),
        sa.ForeignKeyConstraint(["order_id"],   ["orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── wishlist_items ────────────────────────────────────────────────────────
    op.create_table(
        "wishlist_items",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("user_id",    sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"],    ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )

    # ── promo_codes ───────────────────────────────────────────────────────────
    op.create_table(
        "promo_codes",
        sa.Column("id",               sa.Integer(),    nullable=False),
        sa.Column("code",             sa.String(50),   nullable=False),
        sa.Column("description",      sa.String(255)),
        sa.Column("discount_type",    sa.String(20)),
        sa.Column("discount_value",   sa.Float()),
        sa.Column("min_order_value",  sa.Float(),      default=0.0),
        sa.Column("max_discount",     sa.Float()),
        sa.Column("usage_limit",      sa.Integer()),
        sa.Column("usage_count",      sa.Integer(),    default=0),
        sa.Column("valid_until",      sa.DateTime()),
        sa.Column("is_active",        sa.Boolean(),    default=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])


def downgrade() -> None:
    op.drop_table("promo_codes")
    op.drop_table("wishlist_items")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("user_events")
    op.drop_table("users")
    op.drop_table("products")
    op.drop_table("departments")
