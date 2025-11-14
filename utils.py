from datetime import datetime, timedelta
from sqlalchemy import func
from models import Ingredient, Recipe, RecipeItem, SalesCache, DailyUsage
import pandas as pd

def format_currency(amount):
    """Format amount as GBP currency"""
    return f"£{amount:,.2f}"

def calculate_recipe_cost(session, recipe_id):
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        return 0.0
    
    total_cost = 0.0
    for recipe_item in recipe.recipe_items:
        ingredient = recipe_item.ingredient
        total_cost += ingredient.cost_per_unit * recipe_item.quantity
    
    return total_cost

def calculate_profit_margin(session, recipe_id):
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        return 0.0, 0.0, 0.0
    
    cost = calculate_recipe_cost(session, recipe_id)
    profit = recipe.sale_price - cost
    margin_percent = (profit / recipe.sale_price * 100) if recipe.sale_price > 0 else 0
    
    return cost, profit, margin_percent

def get_daily_usage_rate(session, ingredient_id, days=7):
    start_date = datetime.utcnow() - timedelta(days=days)
    
    usage_records = session.query(DailyUsage).filter(
        DailyUsage.ingredient_id == ingredient_id,
        DailyUsage.date >= start_date
    ).all()
    
    if not usage_records:
        return 0.0
    
    total_used = sum(record.quantity_used for record in usage_records)
    avg_daily_usage = total_used / days
    
    return avg_daily_usage

def calculate_reorder_threshold(session, ingredient):
    avg_daily_usage = get_daily_usage_rate(session, ingredient.id, days=14)
    lead_time = ingredient.supplier_lead_time_days
    safety_stock_days = 3
    
    reorder_point = avg_daily_usage * (lead_time + safety_stock_days)
    
    return reorder_point, avg_daily_usage

def get_low_stock_ingredients(session):
    ingredients = session.query(Ingredient).all()
    low_stock = []
    
    for ingredient in ingredients:
        reorder_point, daily_usage = calculate_reorder_threshold(session, ingredient)
        
        if ingredient.current_stock <= reorder_point:
            days_remaining = ingredient.current_stock / daily_usage if daily_usage > 0 else 999
            
            low_stock.append({
                'ingredient': ingredient,
                'current_stock': ingredient.current_stock,
                'reorder_point': reorder_point,
                'daily_usage': daily_usage,
                'days_remaining': days_remaining,
                'urgency': 'critical' if days_remaining < 2 else 'warning' if days_remaining < 5 else 'notice'
            })
    
    low_stock.sort(key=lambda x: x['days_remaining'])
    return low_stock

def update_daily_usage(session, date=None):
    if date is None:
        date = datetime.utcnow().date()
    
    sales = session.query(SalesCache).filter(
        func.date(SalesCache.timestamp) == date
    ).all()
    
    for sale in sales:
        recipe = session.query(Recipe).filter_by(name=sale.item_name).first()
        
        if recipe:
            for recipe_item in recipe.recipe_items:
                quantity_used = recipe_item.quantity * sale.quantity
                
                existing_usage = session.query(DailyUsage).filter(
                    DailyUsage.ingredient_id == recipe_item.ingredient_id,
                    func.date(DailyUsage.date) == date
                ).first()
                
                if existing_usage:
                    existing_usage.quantity_used += quantity_used
                else:
                    new_usage = DailyUsage(
                        ingredient_id=recipe_item.ingredient_id,
                        date=datetime.combine(date, datetime.min.time()),
                        quantity_used=quantity_used
                    )
                    session.add(new_usage)
    
    session.commit()

def generate_business_recommendations(session):
    recommendations = []
    
    recipes = session.query(Recipe).all()
    profit_data = []
    
    for recipe in recipes:
        cost, profit, margin = calculate_profit_margin(session, recipe.id)
        
        sales_count = session.query(func.sum(SalesCache.quantity)).filter(
            SalesCache.item_name == recipe.name
        ).scalar() or 0
        
        profit_data.append({
            'name': recipe.name,
            'cost': cost,
            'profit': profit,
            'margin': margin,
            'sales_count': sales_count,
            'total_profit': profit * sales_count
        })
    
    if profit_data:
        df = pd.DataFrame(profit_data)
        
        high_margin_items = df[df['margin'] > 60].sort_values('margin', ascending=False)
        if not high_margin_items.empty:
            top_item = high_margin_items.iloc[0]
            recommendations.append({
                'type': 'promote',
                'priority': 'high',
                'message': f"🌟 '{top_item['name']}' has a {top_item['margin']:.1f}% profit margin. Consider promoting it more heavily."
            })
        
        low_margin_items = df[df['margin'] < 20].sort_values('sales_count', ascending=False)
        if not low_margin_items.empty:
            top_low = low_margin_items.iloc[0]
            recommendations.append({
                'type': 'optimize',
                'priority': 'medium',
                'message': f"⚠️ '{top_low['name']}' has only {top_low['margin']:.1f}% margin. Consider raising prices or reducing ingredient costs."
            })
        
        if len(df) > 0:
            best_profit = df.sort_values('total_profit', ascending=False).iloc[0]
            best_sales = df.sort_values('sales_count', ascending=False).iloc[0]
            
            if best_profit['name'] != best_sales['name']:
                recommendations.append({
                    'type': 'insight',
                    'priority': 'medium',
                    'message': f"💡 '{best_sales['name']}' sells best, but '{best_profit['name']}' generates more total profit. Balance your menu accordingly."
                })
    
    low_stock = get_low_stock_ingredients(session)
    critical_items = [item for item in low_stock if item['urgency'] == 'critical']
    
    if critical_items:
        ingredient_names = ', '.join([item['ingredient'].name for item in critical_items[:3]])
        recommendations.append({
            'type': 'urgent',
            'priority': 'critical',
            'message': f"🚨 URGENT: Low stock on {ingredient_names}. Order immediately!"
        })
    
    return recommendations

def get_sales_summary(session, days=30):
    start_date = datetime.utcnow() - timedelta(days=days)
    
    sales = session.query(SalesCache).filter(
        SalesCache.timestamp >= start_date
    ).all()
    
    total_revenue = sum(sale.total_amount for sale in sales)
    total_items = sum(sale.quantity for sale in sales)
    
    total_cost = 0.0
    for sale in sales:
        recipe = session.query(Recipe).filter_by(name=sale.item_name).first()
        if recipe:
            cost = calculate_recipe_cost(session, recipe.id)
            total_cost += cost * sale.quantity
    
    total_profit = total_revenue - total_cost
    avg_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'avg_profit_margin': avg_profit_margin,
        'total_items_sold': total_items,
        'num_transactions': len(sales)
    }
