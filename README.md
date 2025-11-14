# 🍰 Ohh Crumbs — Bakery Dashboard

Internal dashboard for **Ohh Crumbs** bakery to manage ingredients, recipes, stock alerts, supplier data, and profit tracking — all connected with Square.

Built with [Streamlit](https://streamlit.io), it’s designed for quick daily use on mobile or desktop.

---

## 🚀 Features
- 📊 **Dashboard** — key stats and totals at a glance  
- 🥖 **Ingredients & Recipes** — track usage, costs, and yields  
- 🔔 **Inventory Alerts** — know when stock runs low  
- 💰 **Profit Analysis** — see margins and revenue trends  
- 📦 **Suppliers** — manage vendor details  
- 🔗 **Square Integration** — sync product and sales data securely  

---

## 🧁 Local setup (optional)
```bash
pip install -r requirements.txt
export DATABASE_URL="sqlite:///bakery.db"
streamlit run app.py
```

---

## 🚀 Deploy to Streamlit Cloud

### 1. Push to GitHub
Make sure your code is pushed to GitHub (already done if you're reading this!)

### 2. Go to Streamlit Cloud
Visit [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub

### 3. Deploy Your App
- Click **"New app"**
- Select your repository: `ohh-crumbs-app`
- Set **Main file path**: `app.py`
- Click **"Deploy"**

### 4. Configure Secrets
In the Streamlit Cloud dashboard, go to **App settings** → **Secrets** and add:

```toml
# Database (use a hosted PostgreSQL or SQLite via mounted storage)
DATABASE_URL = "your-database-url-here"

# Optional: Password protection
ADMIN_PASSWORD = "your-secure-password"

# Square API (if using Square integration)
SQUARE_ACCESS_TOKEN = "your-square-token"
SQUARE_LOCATION_ID = "your-location-id"
```

### 5. Database Options
- **Neon** (free PostgreSQL): [neon.tech](https://neon.tech)
- **Supabase** (free PostgreSQL): [supabase.com](https://supabase.com)
- **Railway** (PostgreSQL): [railway.app](https://railway.app)

Your app will be live at: `https://your-app-name.streamlit.app`
