import os
from square import Square
from datetime import datetime, timedelta
import streamlit as st

class SquareAPI:
    def __init__(self):
        self.access_token = os.getenv('SQUARE_ACCESS_TOKEN')
        self.location_id = os.getenv('SQUARE_LOCATION_ID')

        if not self.access_token:
            self.client = None
            self.is_configured = False
        else:
            self.client = Square(
                access_token=self.access_token,
                environment='production'
            )
            self.is_configured = True
    
    def test_connection(self):
        if not self.is_configured:
            return False, "Square API credentials not configured"
        
        try:
            result = self.client.locations.list_locations()
            if result.is_success():
                return True, "Connected successfully"
            else:
                return False, str(result.errors)
        except Exception as e:
            return False, str(e)
    
    def get_catalog_items(self):
        if not self.is_configured:
            return []
        
        try:
            items = []
            cursor = None
            
            while True:
                result = self.client.catalog.list_catalog(types='ITEM', cursor=cursor)
                
                if result.is_success():
                    for obj in result.body.get('objects', []):
                        item_data = obj.get('item_data', {})
                        variations = item_data.get('variations', [])
                        
                        for variation in variations:
                            variation_data = variation.get('item_variation_data', {})
                            price_money = variation_data.get('price_money', {})
                            
                            items.append({
                                'id': obj['id'],
                                'name': item_data.get('name', 'Unknown'),
                                'variation_id': variation['id'],
                                'price': price_money.get('amount', 0) / 100.0,
                                'category': item_data.get('category_id', 'Uncategorized')
                            })
                    
                    cursor = result.body.get('cursor')
                    if not cursor:
                        break
                else:
                    st.error(f"Error fetching catalog: {result.errors}")
                    break
            
            return items
                
        except Exception as e:
            st.error(f"Exception fetching catalog: {str(e)}")
            return []
    
    def get_payments(self, days_back=30):
        if not self.is_configured or not self.location_id:
            return []
        
        try:
            begin_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            end_time = datetime.utcnow().isoformat() + 'Z'
            
            result = self.client.payments.list_payments(
                begin_time=begin_time,
                end_time=end_time,
                location_id=self.location_id,
                limit=100
            )
            
            if result.is_success():
                payments = []
                for payment in result.body.get('payments', []):
                    payments.append({
                        'id': payment['id'],
                        'amount': payment.get('total_money', {}).get('amount', 0) / 100.0,
                        'status': payment.get('status', 'UNKNOWN'),
                        'created_at': payment.get('created_at', ''),
                        'receipt_number': payment.get('receipt_number', ''),
                    })
                return payments
            else:
                st.error(f"Error fetching payments: {result.errors}")
                return []
                
        except Exception as e:
            st.error(f"Exception fetching payments: {str(e)}")
            return []
    
    def get_orders(self, days_back=30):
        if not self.is_configured or not self.location_id:
            return []
        
        try:
            begin_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            end_time = datetime.utcnow().isoformat() + 'Z'
            
            orders = []
            cursor = None
            
            while True:
                body = {
                    'location_ids': [self.location_id],
                    'query': {
                        'filter': {
                            'date_time_filter': {
                                'created_at': {
                                    'start_at': begin_time,
                                    'end_at': end_time
                                }
                            }
                        }
                    },
                    'limit': 100
                }
                
                if cursor:
                    body['cursor'] = cursor
                
                result = self.client.orders.search_orders(body=body)
                
                if result.is_success():
                    for order in result.body.get('orders', []):
                        line_items = order.get('line_items', [])
                        
                        for item in line_items:
                            orders.append({
                                'order_id': order['id'],
                                'item_name': item.get('name', 'Unknown Item'),
                                'quantity': int(item.get('quantity', '1')),
                                'total_amount': float(item.get('total_money', {}).get('amount', 0)) / 100.0,
                                'created_at': order.get('created_at', ''),
                                'state': order.get('state', 'UNKNOWN')
                            })
                    
                    cursor = result.body.get('cursor')
                    if not cursor:
                        break
                else:
                    st.error(f"Error fetching orders: {result.errors}")
                    break
            
            return orders
                
        except Exception as e:
            st.error(f"Exception fetching orders: {str(e)}")
            return []
