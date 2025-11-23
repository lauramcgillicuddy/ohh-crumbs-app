# 🔧 Ohh Crumbs - Technical Documentation

**Developer Reference Guide**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [File Structure](#file-structure)
4. [Feature Implementation Details](#feature-implementation-details)
5. [API Integration](#api-integration)
6. [Deployment](#deployment)

---

## 🏗️ Architecture Overview

### Tech Stack

- **Framework:** Streamlit (Python web framework)
- **Database:** SQLite (via SQLAlchemy ORM)
- **Data Visualization:** Plotly Express & Plotly Graph Objects
- **Data Processing:** Pandas
- **External APIs:**
  - Square API (POS integration)
  - Open Food Facts API (product barcode lookup)
  - OpenAI API (GPT-4 Vision for OCR)

### Application Structure

```
Streamlit Multi-Page App
├── app.py (main entry point, routing)
├── database.py (DB connection & initialization)
├── models.py (SQLAlchemy models)
├── styling.py (custom CSS & UI components)
└── Feature Pages:
    ├── dashboard.py
    ├── ingredients.py
    ├── recipes.py
    ├── production_log.py
    ├── production_planner.py (NEW)
    ├── expiry_tracking.py (NEW)
    ├── inventory_alerts.py
    ├── waste_tracking.py (NEW)
    ├── profit_analysis.py
    ├── cash_flow.py (NEW)
    ├── equipment_maintenance.py (NEW)
    └── suppliers.py
```

---

## 🗄️ Database Schema

### Existing Models

#### Ingredient
```python
- id: Integer (PK)
- name: String(200) UNIQUE
- unit: String(50)
- cost_per_unit: Float
- current_stock: Float
- supplier_id: Integer (FK → suppliers.id)
- supplier: String(200)
- supplier_lead_time_days: Integer
- allergens: Text (JSON)
- sub_ingredients: Text
- may_contain: Text (JSON)
- last_updated: DateTime
```

#### Recipe
```python
- id: Integer (PK)
- name: String(200) UNIQUE
- square_item_id: String(200)
- sale_price: Float
- category: String(100)
- description: Text
- storage_instructions: Text
- use_by_days: Integer
- created_at: DateTime
- updated_at: DateTime
```

#### RecipeItem (Junction Table)
```python
- id: Integer (PK)
- recipe_id: Integer (FK → recipes.id)
- ingredient_id: Integer (FK → ingredients.id)
- quantity: Float
```

#### ProductionBatch
```python
- id: Integer (PK)
- recipe_id: Integer (FK → recipes.id)
- quantity_produced: Float
- production_date: DateTime
- notes: Text
- expected_cost: Float (NEW)
- actual_cost: Float (NEW)
- created_at: DateTime
```

### New Models (Epic Features Update)

#### WastageLog
```python
- id: Integer (PK)
- ingredient_id: Integer (FK → ingredients.id, nullable)
- recipe_id: Integer (FK → recipes.id, nullable)
- quantity: Float
- unit: String(50)
- reason: String(200)  # 'expired', 'burnt', 'dropped', etc.
- cost: Float
- wastage_date: DateTime
- notes: Text
- created_at: DateTime
```

**Purpose:** Track all waste events for cost analysis and pattern identification.

#### IngredientBatch
```python
- id: Integer (PK)
- ingredient_id: Integer (FK → ingredients.id)
- quantity: Float
- unit: String(50)
- cost_per_unit: Float
- received_date: DateTime
- expiry_date: DateTime (nullable)
- batch_number: String(100, nullable)
- supplier_order_id: Integer (FK → supplier_orders.id, nullable)
- quantity_remaining: Float
- is_active: Boolean (default True)
- created_at: DateTime
```

**Purpose:** Track ingredient batches with expiry dates for FIFO management.

#### ProductionPlan
```python
- id: Integer (PK)
- recipe_id: Integer (FK → recipes.id)
- planned_date: DateTime
- planned_quantity: Float
- forecasted_demand: Float (nullable)
- confidence_score: Float (0-100)
- status: String(50)  # 'planned', 'in_progress', 'completed', 'cancelled'
- actual_quantity: Float (nullable)
- notes: Text
- created_at: DateTime
- updated_at: DateTime
```

**Purpose:** Store AI forecasting results and production schedules.

#### EquipmentLog
```python
- id: Integer (PK)
- equipment_name: String(200)
- equipment_type: String(100)  # 'oven', 'mixer', 'refrigerator', etc.
- maintenance_type: String(100)  # 'cleaning', 'repair', 'calibration', etc.
- maintenance_date: DateTime
- next_maintenance_date: DateTime (nullable)
- cost: Float
- performed_by: String(200, nullable)
- notes: Text
- created_at: DateTime
```

**Purpose:** Track equipment maintenance to prevent breakdowns.

#### UserRole (Foundation for future multi-user)
```python
- id: Integer (PK)
- username: String(100) UNIQUE
- display_name: String(200, nullable)
- role: String(50)  # 'admin', 'manager', 'staff', 'viewer'
- password_hash: String(200, nullable)
- email: String(200, nullable)
- is_active: Boolean (default True)
- created_at: DateTime
- last_login: DateTime (nullable)
```

**Purpose:** Multi-user support (not yet implemented in UI).

---

## 📁 File Structure

### Core Files

**app.py**
- Main entry point
- Page routing logic
- Password authentication gate
- Database initialization

**database.py**
- SQLAlchemy engine setup
- Session management
- DB initialization function

**models.py**
- All SQLAlchemy ORM models
- Database table definitions

**styling.py**
- Custom CSS injection
- Page header component
- Pastel pink theme variables

**utils.py**
- Helper functions
- Business logic (profit calculations, reorder thresholds)
- Auto-sync functions

### Feature Pages

Each page follows this pattern:
```python
def show_<feature_name>():
    inject_custom_css()
    render_page_header("Title", "Subtitle")
    session = get_session()
    try:
        # Feature logic with tabs
        tab1, tab2, tab3 = st.tabs([...])
        with tab1:
            # Feature implementation
    finally:
        close_session(session)
```

### Helper Modules

**allergens.py**
- Natasha's Law allergen categories
- Allergen extraction from ingredients

**common_ingredients.py**
- Allergen templates for common ingredients
- Auto-fill suggestions

**label_generator.py**
- Natasha's Law label generation
- HTML label formatting

**product_lookup.py**
- Open Food Facts API integration
- Barcode product lookup

**pdf_reports.py**
- PDF report generation (ReportLab)
- Sales and inventory reports

**receipt_parser.py**
- OCR receipt parsing (future use)

**square_api.py**
- Square API integration
- Sales sync logic
- Automatic ingredient deduction

**unit_conversions.py**
- Baking unit conversion reference

---

## 🎯 Feature Implementation Details

### 1. AI Demand Forecasting (production_planner.py)

**Algorithm:**
```python
def forecast_demand(session, recipe_id, days_back=30):
    # 1. Get historical sales data
    # 2. Calculate average daily demand (total_sold / total_days)
    # 3. Assign confidence score based on:
    #    - Days with sales (more = higher confidence)
    #    - Consistency (weekly patterns = higher confidence)
    # 4. Detect trend (compare first half vs second half of period)
    # 5. Return (avg_daily_demand, confidence, trend)
```

**Confidence Scoring:**
- < 3 days of sales: 20% confidence
- 3-7 days: 40%
- 7-14 days: 60%
- 14+ days: 80%
- +10% if clear weekly pattern detected
- +10% if increasing trend
- Capped at 100%

**Priority Calculation:**
```python
priority = avg_demand * (confidence / 100)
if trend == "increasing":
    priority *= 1.3
elif trend == "decreasing":
    priority *= 0.7
```

### 2. FIFO Management (expiry_tracking.py)

**Batch Tracking:**
- Each ingredient delivery logged as separate batch
- Batches ordered by expiry_date (oldest first)
- `quantity_remaining` tracks current stock in batch
- `is_active` = False when fully depleted

**Expiry Alerts:**
- Critical: < 3 days until expiry (default)
- Warning: 3-7 days until expiry (default)
- Thresholds user-configurable via sliders

**Integration:**
When logging new batches:
1. Create `IngredientBatch` record
2. Update `Ingredient.current_stock` (total across all batches)
3. Display batches in FIFO order for usage guidance

### 3. Batch Costing (production_log.py)

**Cost Tracking:**
```python
# When logging production:
expected_cost = recipe_ingredient_cost * quantity  # From recipe definition
actual_cost = current_ingredient_prices * quantity  # From current inventory

ProductionBatch(
    expected_cost=expected_cost,
    actual_cost=actual_cost
)
```

**Variance Analysis:**
```python
variance_pct = ((actual - expected) / expected) * 100

if abs(variance_pct) > 10:
    # Major alert
elif abs(variance_pct) > 5:
    # Monitor alert
else:
    # On track
```

### 4. Cash Flow Forecasting (cash_flow.py)

**Historical Analysis:**
```python
daily_cash_flow = {
    'revenue': sum(sales),
    'expenses': sum(supplier_orders + waste_costs + equipment_costs),
    'net_flow': revenue - expenses
}
```

**Projection:**
```python
avg_net_flow = mean(historical_net_flows)
future_balance = current_balance + (avg_net_flow * days_ahead)
```

**Warnings:**
- Negative projected balance = critical alert
- Balance declining >50% = warning
- Positive growth = success message

### 5. Seasonal Trends (dashboard.py)

**Monthly Analysis:**
```python
df['month'] = pd.to_datetime(df['date']).dt.month_name()
monthly_sales = df.groupby('month').agg({'amount': 'sum', 'quantity': 'sum'})
```

**Day of Week Analysis:**
```python
df['day_of_week'] = pd.to_datetime(df['date']).dt.day_name()
dow_sales = df.groupby('day_of_week').agg({'amount': 'mean'})
best_day = dow_sales.loc[dow_sales['amount'].idxmax()]
```

### 6. Waste Tracking (waste_tracking.py)

**Cost Calculation:**
- Ingredient waste: `quantity * cost_per_unit`
- Product waste: `quantity * recipe_ingredient_cost`

**Analytics:**
- Waste by reason (pie chart)
- Waste by type (ingredient vs product)
- Daily waste trends
- Week-over-week comparison

**Recommendations Engine:**
```python
recommendations = {
    "Expired": "Enable expiry tracking, reduce orders, implement FIFO",
    "Burnt": "Review oven settings, use timers",
    "Dropped/Spilled": "Improve workplace organization",
    # ... etc
}
```

### 7. Smart Reorder Automation (inventory_alerts.py)

**Reorder Point Calculation:**
```python
def calculate_reorder_threshold(session, ingredient):
    avg_daily_usage = get_daily_usage_rate(session, ingredient.id, days=14)
    lead_time = ingredient.supplier_lead_time_days
    safety_stock_days = 3
    reorder_point = avg_daily_usage * (lead_time + safety_stock_days)
    return reorder_point
```

**Auto-Order Generation:**
```python
suggested_qty = daily_usage * (lead_time + 7)  # Lead time + 1 week buffer

# Group by supplier
for supplier_id, items in suppliers_dict.items():
    create_order(supplier_id, items, total_cost)
```

### 8. Recipe Scaling (recipes.py)

**Scaling Logic:**
```python
for item in recipe.recipe_items:
    scaled_qty = item.quantity * scale_factor
    scaled_cost = scaled_qty * item.ingredient.cost_per_unit

    # Check availability
    if ingredient.current_stock >= scaled_qty:
        status = "available"
    else:
        status = "insufficient"
        shortage = scaled_qty - ingredient.current_stock
```

---

## 🔌 API Integration

### Square API

**Authentication:**
- Access token stored in Streamlit secrets
- Location ID required for transactions

**Sales Sync:**
```python
def process_square_orders_and_update_inventory(session, days_back=1):
    # 1. Fetch orders from Square API
    # 2. For each order:
    #    a. Check if already imported (via square_payment_id)
    #    b. Create SalesCache record
    #    c. Find matching recipe
    #    d. Deduct ingredients from inventory
    #    e. Update DailyUsage
    # 3. Return stats
```

**Recipe Matching:**
- Exact string match on `SalesCache.item_name` == `Recipe.name`
- Case-sensitive
- Must match exactly for auto-deduction

### Open Food Facts API

**Product Lookup:**
```python
def lookup_product_by_barcode(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(url)
    # Extract allergens, ingredients, brand, name
    # Map to Natasha's Law allergen format
```

**Allergen Mapping:**
- Open Food Facts uses different allergen names
- `map_to_natasha_allergens()` converts to UK standard

### OpenAI GPT-4 Vision

**OCR Extraction:**
```python
def extract_ingredients_from_photo(image_bytes):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    base64_image = base64.b64encode(image_bytes)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "Extract ingredients list from this photo"
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            }]
        }]
    )
    return response.choices[0].message.content
```

---

## 🚀 Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python migrate_epic_features.py

# Start app
streamlit run app.py
```

### Production Deployment

**Streamlit Cloud:**
1. Push to GitHub
2. Connect repository to Streamlit Cloud
3. Add secrets in dashboard:
   ```toml
   ADMIN_PASSWORD = "your_password"
   SQUARE_ACCESS_TOKEN = "your_token"
   SQUARE_LOCATION_ID = "your_location"
   OPENAI_API_KEY = "your_key"
   ```
4. Deploy

**Database:**
- SQLite works for single-user
- For multi-user, migrate to PostgreSQL:
  ```python
  DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ohh_crumbs.db")
  engine = create_engine(DATABASE_URL)
  ```

### Environment Variables

```bash
# Required
ADMIN_PASSWORD=<password>

# Optional (for features)
SQUARE_ACCESS_TOKEN=<token>
SQUARE_LOCATION_ID=<location_id>
OPENAI_API_KEY=<api_key>
```

---

## 🔧 Maintenance

### Database Migrations

When adding new models:
1. Update `models.py`
2. Create migration script:
   ```python
   from database import engine
   from models import Base
   Base.metadata.create_all(engine)
   ```
3. Run migration
4. Commit changes

### Adding New Features

1. Create new page file: `<feature_name>.py`
2. Define `show_<feature_name>()` function
3. Import in `app.py`
4. Add to navigation radio button list
5. Add routing logic
6. Update documentation

### Code Style

- Use `inject_custom_css()` for consistent styling
- Use `render_page_header(title, subtitle)` for headers
- Wrap DB operations in try/finally with `close_session()`
- Use `st.expander()` for collapsible content
- Use Streamlit's column layout for responsiveness

---

## 📊 Performance Considerations

### Database Queries

- Use SQLAlchemy joins to avoid N+1 queries
- Index frequently queried columns (name, date fields)
- Limit query results with `.limit()` for large datasets

### Caching

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def expensive_computation():
    # ...
```

Use for:
- API calls (Square, Open Food Facts)
- Heavy data processing
- Report generation

### Session State

Use `st.session_state` for:
- Temporary form data
- Multi-step workflows
- UI state (expanded/collapsed)

Don't use for:
- Large datasets (use database)
- Persistent data (use database)

---

## 🔐 Security

### Authentication

Current: Simple password gate
```python
if pw == st.secrets["ADMIN_PASSWORD"]:
    st.session_state.ok = True
```

Future: User roles via `UserRole` model

### API Keys

- Store in `.streamlit/secrets.toml` (local)
- Store in Streamlit Cloud secrets (production)
- Never commit to version control

### SQL Injection

- SQLAlchemy ORM prevents SQL injection
- Never use raw SQL with user input
- Always use parameterized queries

---

## 📝 Testing

### Manual Testing Checklist

- [ ] Add ingredient
- [ ] Create recipe
- [ ] Log production
- [ ] Check alerts update
- [ ] Sync Square sales
- [ ] Generate reports
- [ ] Test each new feature

### Future: Automated Tests

```python
# tests/test_forecasting.py
def test_demand_forecast():
    # Create mock sales data
    # Run forecast
    # Assert confidence and demand values
```

---

## 🐛 Known Issues & Limitations

1. **SQLite Concurrency:** Single-user only. Migrate to PostgreSQL for multi-user.
2. **Recipe Matching:** Square items must exactly match recipe names
3. **Timezone:** All times in UTC. May need localization.
4. **Large Datasets:** Charts may slow with 1000+ data points
5. **Mobile UI:** Optimized for desktop, mobile may need tweaks

---

## 🔮 Future Enhancements

### Planned Features
- Multi-user authentication (UserRole model ready)
- Email/SMS notifications for critical alerts
- Customer pre-orders system
- QR code generation for ingredient batches
- Advanced forecasting (ARIMA, seasonal decomposition)
- Inventory optimization algorithms
- Integration with accounting software (Xero, QuickBooks)

### Technical Debt
- Add unit tests
- Implement proper logging
- Error handling improvements
- Database migration framework (Alembic)
- API rate limiting
- Backup/restore functionality

---

## 📚 Resources

### Documentation
- Streamlit: https://docs.streamlit.io
- SQLAlchemy: https://docs.sqlalchemy.org
- Plotly: https://plotly.com/python
- Square API: https://developer.squareup.com

### Useful Links
- Natasha's Law: https://www.food.gov.uk/allergens
- Open Food Facts: https://world.openfoodfacts.org

---

**Built by:** Your sparkly algorithmic accomplice 💜✨
**For:** Ohh Crumbs Bakery
**Last Updated:** November 2025
