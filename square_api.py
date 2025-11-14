import os
from square import Square
from square.core.api_error import ApiError
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
                token=self.access_token
            )
            self.is_configured = True

    def test_connection(self):
        if not self.is_configured:
            return False, "Square API credentials not configured"

        try:
            result = self.client.locations.list()
            return True, "Connected successfully"
        except ApiError as e:
            return False, f"API Error: {str(e)}"
        except Exception as e:
            return False, str(e)

    def get_catalog_items(self):
        if not self.is_configured:
            return []

        try:
            items = []
            cursor = None

            while True:
                result = self.client.catalog.list(types='ITEM', cursor=cursor)

                objects = result.objects if hasattr(result, 'objects') else []
                for obj in objects:
                    item_data = obj.item_data if hasattr(obj, 'item_data') else {}
                    variations = item_data.variations if hasattr(item_data, 'variations') else []

                    for variation in variations:
                        variation_data = variation.item_variation_data if hasattr(variation, 'item_variation_data') else None
                        if variation_data:
                            price_money = variation_data.price_money if hasattr(variation_data, 'price_money') else None
                            price = (price_money.amount / 100.0) if price_money and hasattr(price_money, 'amount') else 0

                            items.append({
                                'id': obj.id if hasattr(obj, 'id') else '',
                                'name': item_data.name if hasattr(item_data, 'name') else 'Unknown',
                                'variation_id': variation.id if hasattr(variation, 'id') else '',
                                'price': price,
                                'category': item_data.category_id if hasattr(item_data, 'category_id') else 'Uncategorized'
                            })

                cursor = result.cursor if hasattr(result, 'cursor') else None
                if not cursor:
                    break

            return items

        except ApiError as e:
            st.error(f"Square API error fetching catalog: {str(e)}")
            return []
        except Exception as e:
            st.error(f"Exception fetching catalog: {str(e)}")
            return []

    def get_payments(self, days_back=30):
        if not self.is_configured or not self.location_id:
            return []

        try:
            begin_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            end_time = datetime.utcnow().isoformat() + 'Z'

            result = self.client.payments.list(
                begin_time=begin_time,
                end_time=end_time,
                location_id=self.location_id,
                limit=100
            )

            payments = []
            payment_list = result.payments if hasattr(result, 'payments') else []
            for payment in payment_list:
                total_money = payment.total_money if hasattr(payment, 'total_money') else None
                amount = (total_money.amount / 100.0) if total_money and hasattr(total_money, 'amount') else 0

                payments.append({
                    'id': payment.id if hasattr(payment, 'id') else '',
                    'amount': amount,
                    'status': payment.status if hasattr(payment, 'status') else 'UNKNOWN',
                    'created_at': payment.created_at if hasattr(payment, 'created_at') else '',
                    'receipt_number': payment.receipt_number if hasattr(payment, 'receipt_number') else '',
                })
            return payments

        except ApiError as e:
            st.error(f"Square API error fetching payments: {str(e)}")
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

                result = self.client.orders.search(body=body)

                order_list = result.orders if hasattr(result, 'orders') else []
                for order in order_list:
                    line_items = order.line_items if hasattr(order, 'line_items') else []

                    for item in line_items:
                        total_money = item.total_money if hasattr(item, 'total_money') else None
                        amount = (total_money.amount / 100.0) if total_money and hasattr(total_money, 'amount') else 0

                        orders.append({
                            'order_id': order.id if hasattr(order, 'id') else '',
                            'item_name': item.name if hasattr(item, 'name') else 'Unknown Item',
                            'quantity': int(item.quantity) if hasattr(item, 'quantity') else 1,
                            'total_amount': amount,
                            'created_at': order.created_at if hasattr(order, 'created_at') else '',
                            'state': order.state if hasattr(order, 'state') else 'UNKNOWN'
                        })

                cursor = result.cursor if hasattr(result, 'cursor') else None
                if not cursor:
                    break

            return orders

        except ApiError as e:
            st.error(f"Square API error fetching orders: {str(e)}")
            return []
        except Exception as e:
            st.error(f"Exception fetching orders: {str(e)}")
            return []
