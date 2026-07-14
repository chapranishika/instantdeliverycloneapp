"""
Backend test suite — real business logic tests.
Covers: auth flow, bcrypt hashing, JWT, promo math, checkout, cart validation.
Uses in-memory SQLite — no Supabase connection required.
"""
import asyncio, os, pytest, pytest_asyncio
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"]   = "test-secret-only"
os.environ["REDIS_URL"]    = ""

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ── Shared engine (single in-memory DB across all tests) ─────────────────────
_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Create all tables once, seed test data."""
    from app.models.db_models import Base, Department, Product, PromoCode
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as db:
        dept = Department(name="Fresh Fruits")
        db.add(dept)
        await db.flush()
        p1 = Product(id=101, name="Banana",     price=60.0,  mrp=75.0,
                     department_id=dept.id, rating=4.7, rating_count=100,
                     delivery_time_mins=10, is_available=True,  stock_count=100,
                     quantity_label="1kg")
        p2 = Product(id=102, name="Apple",      price=150.0, mrp=180.0,
                     department_id=dept.id, rating=4.8, rating_count=80,
                     delivery_time_mins=10, is_available=True,  stock_count=50,
                     quantity_label="1kg")
        p3 = Product(id=103, name="OutOfStock", price=50.0,  mrp=60.0,
                     department_id=dept.id, rating=4.0, rating_count=10,
                     delivery_time_mins=10, is_available=False, stock_count=0,
                     quantity_label="500g")
        # Promo codes
        promo1 = PromoCode(code="SAVE10", discount_type="percentage",
                           discount_value=10.0, min_order_value=100.0,
                           max_discount=50.0,  is_active=True)
        promo2 = PromoCode(code="FLAT30", discount_type="flat",
                           discount_value=30.0, min_order_value=200.0,
                           max_discount=None,  is_active=True)
        promo3 = PromoCode(code="DEAD",   discount_type="percentage",
                           discount_value=50.0, min_order_value=0.0,
                           max_discount=None,  is_active=False)
        db.add_all([p1, p2, p3, promo1, promo2, promo3])
        await db.commit()
    yield

@pytest_asyncio.fixture(scope="session")
async def app(setup_db):
    """FastAPI app with DB override pointing to our test engine."""
    from app.main import app as fa
    from app import db as db_module
    # Patch the session factory to use our test engine
    db_module.database.AsyncSessionLocal = _Session
    return fa

@pytest_asyncio.fixture(scope="session")
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as c:
        yield c

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Health check
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: bcrypt — SHA-256 must NOT be used
# ═══════════════════════════════════════════════════════════════════════════════
def test_bcrypt_not_sha256():
    from app.core.security import hash_password, verify_password
    import hashlib
    plain = "TestPass999"
    hashed = hash_password(plain)
    sha256 = hashlib.sha256(plain.encode()).hexdigest()
    assert hashed != sha256,         "❌ Still using SHA-256 — must be bcrypt"
    assert hashed.startswith("$2"),  "❌ Not a bcrypt hash"
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: JWT sign and verify
# ═══════════════════════════════════════════════════════════════════════════════
def test_jwt():
    from app.core.security import create_access_token, decode_access_token, get_user_id_from_token
    token = create_access_token({"sub": "7", "email": "a@b.com"})
    assert len(token.split(".")) == 3,     "❌ JWT must have 3 parts"
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["email"] == "a@b.com"
    assert "exp" in payload,               "❌ JWT must include expiry"
    assert get_user_id_from_token(token) == 7
    assert decode_access_token("bad.tok.en") is None
    assert get_user_id_from_token("garbage") is None

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Register → Login → /auth/me
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_auth_flow(client):
    # Register
    r = await client.post("/api/v1/auth/register", json={
        "email": "nish@zepto.com", "password": "SecurePass123",
        "name": "Nish", "phone": "9999999999"
    })
    assert r.status_code == 200, f"Register failed: {r.text}"
    data = r.json()
    assert "access_token" in data, "❌ No JWT returned from register"
    assert data["token_type"] == "bearer"
    assert data["email"] == "nish@zepto.com"

    # Duplicate email must fail
    r2 = await client.post("/api/v1/auth/register", json={
        "email": "nish@zepto.com", "password": "OtherPass123", "name": "Dup"
    })
    assert r2.status_code == 400, "❌ Duplicate email should return 400"

    # Login with correct password
    r3 = await client.post("/api/v1/auth/login", json={
        "email": "nish@zepto.com", "password": "SecurePass123"
    })
    assert r3.status_code == 200, f"Login failed: {r3.text}"
    token = r3.json().get("access_token")
    assert token, "❌ No JWT returned from login"

    # Wrong password → 401
    r4 = await client.post("/api/v1/auth/login", json={
        "email": "nish@zepto.com", "password": "WrongPass000"
    })
    assert r4.status_code == 401, "❌ Wrong password should be 401"

    # /auth/me with valid token
    r5 = await client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
    assert r5.status_code == 200
    assert r5.json()["email"] == "nish@zepto.com"

    # /auth/me with garbage token → 401
    r6 = await client.get("/api/v1/auth/me",
                          headers={"Authorization": "Bearer garbage.bad.token"})
    assert r6.status_code == 401, "❌ Invalid token must return 401"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Products — unavailable items must be excluded
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_products_excludes_unavailable(client):
    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "OutOfStock" not in names, "❌ Unavailable product must not appear"
    assert "Banana" in names
    assert "Apple" in names

@pytest.mark.asyncio
async def test_product_not_found(client):
    r = await client.get("/api/v1/products/99999")
    assert r.status_code == 404

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Short password rejected
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_short_password_rejected(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "short@test.com", "password": "abc", "name": "Short"
    })
    assert r.status_code in (400, 422), "❌ Short password must be rejected"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Promo — percentage with cap (most important business logic)
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_promo_percentage_capped(client):
    """SAVE10 = 10% off, capped at ₹50. Order ₹600 → 10% = ₹60 → capped ₹50."""
    r = await client.post("/api/v1/checkout", json={
        "user_id": None,
        "cart_items": [
            {"product_id": 101, "quantity": 5},   # 5×60 = ₹300
            {"product_id": 102, "quantity": 2},   # 2×150 = ₹300
        ],
        "delivery_address": "123 Test St, Mumbai",
        "promo_code": "SAVE10",
    })
    assert r.status_code == 200, f"Checkout failed: {r.text}"
    data = r.json()
    assert data["discount"] == 50.0, \
        f"❌ Expected ₹50 discount (capped), got ₹{data['discount']}"
    assert data["total"] == 550.0, \
        f"❌ Expected ₹550 total, got ₹{data['total']}"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Promo — flat discount
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_promo_flat(client):
    """FLAT30 = ₹30 off on orders ≥ ₹200. Order ₹300 → total ₹270."""
    r = await client.post("/api/v1/checkout", json={
        "user_id": None,
        "cart_items": [{"product_id": 102, "quantity": 2}],  # 2×150 = ₹300
        "delivery_address": "123 Test St",
        "promo_code": "FLAT30",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["discount"] == 30.0, f"❌ Expected ₹30, got ₹{data['discount']}"
    assert data["total"] == 270.0

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: Promo — below minimum order value
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_promo_below_minimum(client):
    """FLAT30 needs ₹200 min. Order ₹60 → ₹0 discount."""
    r = await client.post("/api/v1/checkout", json={
        "user_id": None,
        "cart_items": [{"product_id": 101, "quantity": 1}],  # ₹60
        "delivery_address": "123 Test St",
        "promo_code": "FLAT30",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["discount"] == 0.0, \
        f"❌ Promo must not apply below minimum, got ₹{data['discount']}"
    assert data["total"] == 60.0

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: Promo — inactive code gives zero discount
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_promo_inactive(client):
    """DEAD is is_active=False — must give ₹0 discount."""
    r = await client.post("/api/v1/checkout", json={
        "user_id": None,
        "cart_items": [{"product_id": 102, "quantity": 2}],  # ₹300
        "delivery_address": "123 Test St",
        "promo_code": "DEAD",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["discount"] == 0.0, "❌ Inactive promo must give no discount"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: Checkout without promo
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_checkout_no_promo(client):
    r = await client.post("/api/v1/checkout", json={
        "user_id": None,
        "cart_items": [{"product_id": 101, "quantity": 3}],  # 3×60 = ₹180
        "delivery_address": "123 Test St",
        "promo_code": None,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 180.0
    assert data["discount"] == 0.0
    assert data["order_id"] is not None
    assert data["status"] == "confirmed"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: Cart validation
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_cart_validation(client):
    r = await client.post("/api/v1/cart/validate", json=[
        {"product_id": 101,   "quantity": 2},   # Banana — in stock
        {"product_id": 103,   "quantity": 1},   # OutOfStock
        {"product_id": 99999, "quantity": 1},   # Doesn't exist
    ])
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["available"] is True,  "❌ Banana should be available"
    assert items[1]["available"] is False, "❌ OutOfStock must not be available"
    assert items[2]["available"] is False, "❌ Non-existent must not be available"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 13: Search empty query rejected
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_search_empty_rejected(client):
    r = await client.get("/api/v1/search?q=")
    assert r.status_code in (400, 422), "❌ Empty search query must be rejected"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 14: Trending excludes unavailable products
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_trending_no_unavailable(client):
    r = await client.get("/api/v1/recommend/global/trending")
    assert r.status_code == 200
    names = [p["name"] for p in r.json().get("products", [])]
    assert "OutOfStock" not in names, "❌ Trending must exclude unavailable"

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 15: Event tracking
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_event_tracking(client):
    r = await client.post("/api/v1/events", json={
        "event_type": "view", "product_id": 101,
        "session_id": "sess-abc123", "page": "/product/101",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "logged"
