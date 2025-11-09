from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    contact_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    notes = Column(Text)
    lead_time_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    ingredients = relationship('Ingredient', back_populates='supplier_rel')
    orders = relationship('SupplierOrder', back_populates='supplier', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Supplier(name='{self.name}')>"


class Ingredient(Base):
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    unit = Column(String(50), nullable=False)
    cost_per_unit = Column(Float, default=0.0)
    current_stock = Column(Float, default=0.0)
    supplier = Column(String(200))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    supplier_lead_time_days = Column(Integer, default=7)
    
    recipe_items = relationship('RecipeItem', back_populates='ingredient')
    supplier_rel = relationship('Supplier', back_populates='ingredients')
    
    def __repr__(self):
        return f"<Ingredient(name='{self.name}', unit='{self.unit}')>"


class Recipe(Base):
    __tablename__ = 'recipes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    square_item_id = Column(String(200))
    sale_price = Column(Float, default=0.0)
    category = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    recipe_items = relationship('RecipeItem', back_populates='recipe', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Recipe(name='{self.name}', sale_price={self.sale_price})>"


class RecipeItem(Base):
    __tablename__ = 'recipe_items'
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    
    recipe = relationship('Recipe', back_populates='recipe_items')
    ingredient = relationship('Ingredient', back_populates='recipe_items')
    
    def __repr__(self):
        return f"<RecipeItem(recipe_id={self.recipe_id}, ingredient_id={self.ingredient_id}, quantity={self.quantity})>"


class SalesCache(Base):
    __tablename__ = 'sales_cache'
    
    id = Column(Integer, primary_key=True)
    square_payment_id = Column(String(200), unique=True)
    item_name = Column(String(200))
    quantity = Column(Integer, default=1)
    total_amount = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SalesCache(item_name='{self.item_name}', quantity={self.quantity}, timestamp={self.timestamp})>"


class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Settings(key='{self.key}')>"


class DailyUsage(Base):
    __tablename__ = 'daily_usage'
    
    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    quantity_used = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<DailyUsage(ingredient_id={self.ingredient_id}, date={self.date}, quantity={self.quantity_used})>"


class SupplierOrder(Base):
    __tablename__ = 'supplier_orders'
    
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    status = Column(String(50), default='pending')
    total_cost = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship('Supplier', back_populates='orders')
    order_items = relationship('SupplierOrderItem', back_populates='order', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<SupplierOrder(id={self.id}, supplier_id={self.supplier_id}, status='{self.status}')>"


class SupplierOrderItem(Base):
    __tablename__ = 'supplier_order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('supplier_orders.id'), nullable=False)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    order = relationship('SupplierOrder', back_populates='order_items')
    
    def __repr__(self):
        return f"<SupplierOrderItem(order_id={self.order_id}, ingredient_id={self.ingredient_id}, quantity={self.quantity})>"


class ProfitHistory(Base):
    __tablename__ = 'profit_history'
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    sale_price = Column(Float, default=0.0)
    ingredient_cost = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    quantity_sold = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<ProfitHistory(recipe_id={self.recipe_id}, date={self.date}, profit_margin={self.profit_margin:.2f}%)>"
