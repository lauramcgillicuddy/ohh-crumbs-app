# 🍰 Ohh Crumbs - Complete Feature Guide

**Your Complete Bakery Management System**

---

## 📚 Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Features](#core-features)
4. [Advanced Features](#advanced-features)
5. [Tips & Best Practices](#tips--best-practices)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

Ohh Crumbs is a comprehensive bakery management system built for **Emma's Ohh Crumbs Bakery**. It handles everything from inventory tracking to financial forecasting, helping you run your bakery more efficiently and profitably.

### What Can It Do?

- 📦 **Track inventory** with smart reorder alerts
- 🍰 **Manage recipes** with cost calculations and allergen tracking
- 📊 **Monitor sales** with Square POS integration
- 🤖 **Predict demand** with AI-powered forecasting
- 💰 **Forecast cash flow** to avoid financial surprises
- ⏰ **Track expiry dates** to reduce waste
- 🗑️ **Log waste** to identify cost savings
- 🔧 **Maintain equipment** to prevent breakdowns
- 📈 **Analyze trends** to optimize your business

---

## 🚀 Getting Started

### First Time Setup

1. **Run the migration** to set up new database tables:
   ```bash
   python migrate_epic_features.py
   ```

2. **Launch the app**:
   ```bash
   streamlit run app.py
   ```

3. **Add your first items**:
   - Start with **Suppliers** (add your ingredient suppliers)
   - Then **Ingredients** (add what you use)
   - Then **Recipes** (your menu items)
   - Finally, connect to **Square** for automatic sales sync

---

## 🏠 Core Features

### 1. Dashboard

**What it does:** Your business overview at a glance

**Key Features:**
- Revenue, profit, margin, and sales metrics
- Daily sales trend charts
- Top selling items
- **NEW: Seasonal trends** (monthly comparisons, day of week analysis)
- Business recommendations

**How to use:**
- Select time period (7, 14, 30, 60, 90 days)
- View trends and identify patterns
- Download PDF reports

**Tips:**
- Check daily to spot trends early
- Use seasonal trends to plan production
- Best/worst days help with staffing decisions

---

### 2. Ingredients

**What it does:** Manage your inventory with smart tracking

**Key Features:**
- Add/edit ingredients
- Track stock levels
- **NEW: Autocomplete** - search and copy existing ingredients
- Barcode scanner for quick updates
- Allergen tracking (Natasha's Law compliance)
- Supplier assignment
- Cost tracking

**How to use:**
1. **Add New Ingredient:**
   - Go to "Add Ingredient" tab
   - Use autocomplete to copy an existing ingredient (e.g., type "Flour" to copy settings)
   - Or scan product barcode to auto-fill allergens
   - Or upload ingredient photo for OCR extraction
   - Fill in details and save

2. **Update Stock:**
   - Use "Update Stock" tab for bulk updates
   - Or use "Barcode Scanner" tab for quick adjustments

**Tips:**
- Use autocomplete when adding similar ingredients (saves time!)
- Complete allergen info for Natasha's Law compliance
- Use the allergen audit tab to find missing data

---

### 3. Recipes

**What it does:** Define your menu items with full costing

**Key Features:**
- Create recipes with ingredient lists
- Automatic cost calculation
- Profit margin tracking
- Allergen auto-detection
- Natasha's Law label generation
- **NEW: Recipe Scaling Calculator**

**How to use:**
1. **Create Recipe:**
   - Add name, price, category
   - Add ingredients with quantities
   - System auto-calculates cost and profit

2. **Scale Recipe** (NEW!):
   - Click "Scale Recipe" button
   - Choose multiplier (0.5 = half, 2 = double, etc.)
   - System shows:
     - Exact ingredients needed
     - Total cost and profit
     - Ingredient availability check
   - Perfect for big orders!

3. **Generate Labels:**
   - Click "Generate Natasha's Law Label"
   - Review allergen information
   - Print or save for packaging

**Tips:**
- Use recipe scaling before big catering orders
- Update prices regularly to maintain margins
- Check ingredient availability before promising large orders

---

### 4. Production Log

**What it does:** Track what you make and deduct ingredients automatically

**Key Features:**
- Log daily production
- Automatic ingredient deduction from inventory
- Track daily usage for reorder calculations
- **NEW: Batch Costing Comparison** - see if costs are increasing

**How to use:**
1. **Log Production:**
   - Select production date
   - Add recipes and quantities made
   - Click "Log Production & Deduct Ingredients"
   - System automatically deducts ingredients from stock

2. **View Batch Costs** (NEW!):
   - Go to "Production History" tab
   - See expected vs actual costs
   - Get alerts if costs vary by >5% (ingredient prices may have changed!)

**Tips:**
- Log production DAILY for accurate reorder calculations
- Monitor batch cost variance to catch price increases early
- Use notes field to track special batches or recipe variations

---

## 🚀 Advanced Features

### 5. Production Planner (NEW!)

**What it does:** AI-powered demand forecasting to optimize production

**Key Features:**
- AI predicts demand based on sales history
- Confidence scoring (how certain the prediction is)
- Trend detection (increasing, decreasing, stable)
- "What should I bake today?" recommendations
- Ingredient availability checking
- Production schedule management

**How to use:**
1. **AI Recommendations Tab:**
   - See top recommendations sorted by priority
   - View forecasted demand and confidence %
   - Check ingredient availability
   - Click "Add to Production Schedule" for suggested items

2. **Production Schedule Tab:**
   - View planned production by date
   - Mark items as in progress or completed
   - Delete or modify plans

3. **Forecast Analysis Tab:**
   - Deep dive into sales patterns for specific items
   - See 60-day sales history
   - Day of week breakdown

**Tips:**
- Higher confidence = more reliable forecast
- "Increasing" trend = consider making extra
- Use schedule to plan ingredient orders ahead of time
- Check at least weekly to optimize production

---

### 6. Expiry & FIFO Tracking (NEW!)

**What it does:** Track ingredient batches with expiry dates to prevent waste

**Key Features:**
- Log batches with expiry dates
- Critical/warning alerts for expiring items
- FIFO (First In, First Out) order display
- Automatic waste logging for expired items
- Value-at-risk analytics

**How to use:**
1. **Log New Batch:**
   - When receiving ingredients, log batch details
   - Include received date and expiry date
   - Optional: batch number from supplier

2. **Check Expiry Alerts:**
   - Critical = expiring within 3 days (default)
   - Warning = expiring within 7 days (default)
   - Adjust thresholds to your needs
   - Mark as "Used" or "Wasted"

3. **View Batch Inventory:**
   - See all batches in FIFO order (use oldest first!)
   - Track how much of each batch remains
   - Monitor value at risk

**Tips:**
- ALWAYS use FIFO - use oldest batches first
- Log batches immediately when receiving orders
- Check expiry alerts daily
- Use batch numbers to track supplier quality

---

### 7. Inventory Alerts

**What it does:** Smart reorder alerts based on usage patterns

**Key Features:**
- Automatic reorder point calculation (based on 14-day usage + lead time + 3-day buffer)
- Critical/warning/notice levels
- **Smart Reorder Automation** - auto-generate supplier orders
- Inventory status charts
- PDF report generation

**How to use:**
1. **Review Alerts:**
   - Critical = less than 2 days of stock
   - Warning = less than 5 days of stock
   - Notice = below reorder point

2. **Auto-Generate Orders** (SMART!):
   - System groups low-stock items by supplier
   - Click "Create Order" for each supplier
   - Orders are automatically created with suggested quantities

**Tips:**
- Check alerts DAILY
- Use auto-order feature to save time
- Adjust reorder points if you run out frequently

---

### 8. Waste Tracking (NEW!)

**What it does:** Track and analyze waste to save money

**Key Features:**
- Log ingredient waste (expired, dropped, spoiled, etc.)
- Log finished product waste (burnt, customer complaint, etc.)
- Waste analytics with charts
- Cost tracking
- Recommendations for waste reduction

**How to use:**
1. **Log Waste:**
   - Select ingredient or finished product
   - Enter quantity and reason
   - System auto-calculates cost
   - Add notes if needed

2. **Analyze Waste:**
   - See total waste cost
   - Pie chart by reason
   - Daily trends
   - Most wasted items

3. **Get Insights:**
   - Top waste reason highlighted
   - Recommendations based on patterns
   - Week-over-week comparison

**Tips:**
- Log waste IMMEDIATELY when it happens
- Review weekly to spot patterns
- Use insights to improve procedures
- If "expired" is top reason, enable expiry tracking!

---

### 9. Profit Analysis

**What it does:** Detailed profitability tracking by item

**Key Features:**
- Profit margin per item
- Sales volume analysis
- Profitability vs sales charts
- Historical profit trends
- PDF reports

**How to use:**
- Select time period
- View profitability table
- Identify high-margin low-volume items (marketing opportunity!)
- Identify low-margin high-volume items (price increase opportunity!)

**Tips:**
- Focus on items with high margin AND high volume
- Consider discontinuing low-margin items with low sales
- Use insights to adjust pricing strategy

---

### 10. Cash Flow Forecast (NEW!)

**What it does:** Predict future cash balance to avoid surprises

**Key Features:**
- Historical cash flow analysis
- 7-90 day forecast
- Revenue vs expense tracking
- Supplier, waste, and equipment cost breakdown
- Alerts when running low on cash
- Recommendations

**How to use:**
1. **Set Current Balance:**
   - Enter your actual bank balance

2. **View Forecast:**
   - See projected balance for next X days
   - Review historical trends
   - Check if you'll have cash flow problems

3. **Analyze Expenses:**
   - See breakdown by category
   - Identify biggest expense areas
   - Make informed decisions

**Tips:**
- Update weekly with current balance
- If forecast shows negative balance, take action NOW
- Use expense breakdown to find cost savings
- Plan large purchases around cash flow peaks

---

### 11. Equipment Maintenance (NEW!)

**What it does:** Track equipment maintenance to prevent breakdowns

**Key Features:**
- Log maintenance events
- Schedule next maintenance dates
- Maintenance history
- Cost tracking
- Overdue alerts

**How to use:**
1. **Log Maintenance:**
   - Select or add equipment
   - Choose type (cleaning, repair, calibration, etc.)
   - Set next maintenance date
   - Track cost and notes

2. **Monitor Status:**
   - View equipment list with status indicators
   - Green = good, Yellow = due soon, Red = overdue
   - Update next maintenance dates

**Tips:**
- Set calendar reminders for maintenance
- Track costs to budget for equipment replacement
- Log ALL maintenance, even cleaning
- Use notes to track recurring issues

---

### 12. Suppliers

**What it does:** Manage supplier relationships and orders

**Key Features:**
- Store supplier contact info
- Track lead times
- Create purchase orders
- Order history
- Receive orders (updates stock automatically)

**How to use:**
1. **Add Supplier:**
   - Enter name, contact, lead time

2. **Create Order:**
   - Add items with quantities
   - System calculates total cost
   - Set expected delivery date

3. **Receive Order:**
   - Mark as received
   - Stock automatically updates
   - Track actual vs expected delivery

**Tips:**
- Set accurate lead times for better reorder alerts
- Track delivery performance to identify reliable suppliers
- Use auto-order feature from Inventory Alerts page

---

### 13. Square Setup

**What it does:** Connect to Square POS for automatic sales sync

**Key Features:**
- Square API integration
- Automatic sales import
- Recipe matching (auto-deducts ingredients when you sell!)
- Sync history tracking

**How to use:**
1. **Connect Square:**
   - Enter API credentials
   - Test connection

2. **Sync Sales:**
   - Choose time period (24h, 7 days, etc.)
   - Click sync
   - System imports sales AND deducts ingredients automatically

**Tips:**
- Sync daily for best results
- Ensure recipe names match Square item names
- Check sync history to verify imports

---

## 💡 Tips & Best Practices

### Daily Tasks
1. ✅ Check **Expiry Alerts** - use oldest batches first
2. ✅ Review **Inventory Alerts** - order ingredients before stockouts
3. ✅ Log **Production** - keeps reorder calculations accurate
4. ✅ Log **Waste** - track what's costing you money
5. ✅ Sync **Square Sales** - keeps inventory accurate

### Weekly Tasks
1. ✅ Review **Production Planner** - optimize what to make
2. ✅ Check **Waste Analytics** - identify patterns
3. ✅ Review **Cash Flow Forecast** - avoid surprises
4. ✅ Update **Equipment Maintenance** - prevent breakdowns

### Monthly Tasks
1. ✅ Review **Seasonal Trends** - plan for busy periods
2. ✅ Analyze **Profitability** - adjust prices if needed
3. ✅ Check **Batch Costing** - ensure ingredient costs haven't increased
4. ✅ Update **Recipe Costs** - keep margins accurate

### Cost-Saving Tips
- Use **Expiry Tracking** to prevent waste from expired items
- Use **Waste Analytics** to identify biggest waste sources
- Use **Batch Costing** to catch ingredient price increases early
- Use **Production Planner** to avoid over-producing
- Use **FIFO** to use oldest ingredients first
- Use **Cash Flow Forecast** to time large purchases optimally

### Growth Tips
- Use **Seasonal Trends** to identify busy periods (hire more staff!)
- Use **Production Planner** demand forecasting to optimize output
- Use **Profit Analysis** to focus on high-margin items
- Use **Recipe Scaling** to easily handle large orders
- Use **Day of Week Analysis** to plan special promotions on slow days

---

## 🆘 Troubleshooting

### "Ingredient stock is negative!"
**Solution:** You logged production without having enough stock. Manually adjust stock in "Update Stock" tab.

### "Reorder alerts aren't working"
**Solution:** System needs at least 3 days of production data to calculate usage rates. Log production daily for a few days.

### "Expiry alerts not showing"
**Solution:** Make sure you're logging batches with expiry dates in the "Expiry & FIFO" page, not just updating stock.

### "AI forecasting shows 0 demand"
**Solution:** System needs sales history. Connect Square or wait for more sales data. Forecast confidence will be low (<40%) with little data.

### "Square sync not deducting ingredients"
**Solution:** Recipe names must EXACTLY match Square item names. Check spelling and capitalization.

### "Cash flow forecast looks wrong"
**Solution:** Make sure you entered your actual current cash balance. The forecast projects from that starting point.

### "Batch costs showing big variance"
**Solution:** This is GOOD! It means you caught an ingredient price increase. Check with suppliers and consider adjusting recipe prices.

---

## 📊 Feature Summary Table

| Feature | Page | What It Does | Key Benefit |
|---------|------|--------------|-------------|
| Dashboard | 🏠 Dashboard | Business overview | See trends at a glance |
| Ingredients | 🥖 Ingredients | Manage inventory | Track what you have |
| Recipes | 📖 Recipes | Menu management | Calculate costs & profits |
| Recipe Scaling | 📖 Recipes | Scale recipes up/down | Handle big orders easily |
| Production Log | 🍰 Production Log | Track what you make | Auto-deduct ingredients |
| Batch Costing | 🍰 Production Log | Compare costs | Catch price increases |
| Production Planner | 📅 Production Planner | AI forecasting | Optimize what to bake |
| Inventory Tracking | 📊 Inventory Tracking | Stock management | Never run out |
| Expiry & FIFO | ⏰ Expiry & FIFO | Expiry tracking | Prevent waste |
| Inventory Alerts | 🔔 Inventory Alerts | Reorder alerts | Auto-order ingredients |
| Waste Tracking | 🗑️ Waste Tracking | Track waste | Save money |
| Profit Analysis | 💰 Profit Analysis | Profitability | Maximize earnings |
| Cash Flow Forecast | 💸 Cash Flow Forecast | Predict cash | Avoid cash crunches |
| Equipment Maintenance | 🔧 Equipment Maintenance | Track maintenance | Prevent breakdowns |
| Seasonal Trends | 🏠 Dashboard | Analyze patterns | Plan for busy periods |
| Suppliers | 📦 Suppliers | Supplier management | Organize orders |
| Square Setup | 🔗 Square Setup | POS integration | Auto-sync sales |

---

## 🎓 Learning Path

### Week 1: Getting Started
- Day 1-2: Add suppliers and ingredients
- Day 3-4: Create recipes
- Day 5-7: Start logging production and sync Square

### Week 2: Build Habits
- Start logging waste daily
- Check inventory alerts daily
- Begin logging ingredient batches with expiry dates
- Review production planner weekly

### Week 3: Optimize
- Analyze waste trends
- Use recipe scaling for orders
- Set up equipment maintenance schedule
- Review seasonal trends

### Week 4: Master
- Use AI production planning
- Monitor cash flow forecast
- Analyze batch costing
- Use FIFO consistently

---

## 🎉 You're All Set!

You now have a professional-grade bakery management system that rivals commercial software costing thousands of pounds!

**Remember:**
- Start simple (ingredients → recipes → production logging)
- Add features gradually as you get comfortable
- Review analytics weekly to make data-driven decisions
- Most importantly: **Use the AI production planner** - it's your secret weapon!

**Questions?** Check the code comments or reach out to your developer (that sparkly algorithmic accomplice who built this for you! 💜✨)

---

**Built with love for Emma's Ohh Crumbs Bakery** 🍰
*Transforming bakery operations, one feature at a time!*
