import re
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st

def parse_receipt_text(text: str) -> Dict:
    """
    Parse extracted text from a receipt to identify vendor info and line items.
    Returns a dict with vendor_info and line_items.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    result = {
        'vendor_name': None,
        'vendor_email': None,
        'vendor_phone': None,
        'vendor_address': None,
        'order_date': None,
        'line_items': [],
        'total_amount': None
    }

    # Common vendor name patterns (usually at the top)
    if lines:
        result['vendor_name'] = lines[0]

    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for line in lines:
        email_match = re.search(email_pattern, line)
        if email_match:
            result['vendor_email'] = email_match.group()
            break

    # Extract phone
    phone_pattern = r'(\+?44\s?7\d{3}\s?\d{6})|(\+?44\s?\d{4}\s?\d{6})|(\(?0\d{4}\)?\s?\d{6})|(\(?0\d{3}\)?\s?\d{3}\s?\d{4})'
    for line in lines:
        phone_match = re.search(phone_pattern, line)
        if phone_match:
            result['vendor_phone'] = phone_match.group()
            break

    # Extract date
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or DD-MM-YYYY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY-MM-DD
    ]
    for line in lines:
        for pattern in date_patterns:
            date_match = re.search(pattern, line)
            if date_match:
                try:
                    date_str = date_match.group()
                    # Try different date formats
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']:
                        try:
                            result['order_date'] = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue
                    if result['order_date']:
                        break
                except:
                    pass

    # Extract line items (quantity, item name, unit price, total price)
    # Updated patterns to handle receipts with both unit price AND net amount
    item_patterns = [
        # Pattern with qty, item name, unit price, and net amount (e.g., "10 Ardress Diced Apple Pie Mix 19.80 10kg 198.00")
        r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)?\s*([A-Za-z][A-Za-z\s\-\'&.]+?)\s+(\d+\.\d{2})\s+(?:\d+(?:\.\d+)?)?(?:kg|g|l|ml|lb|oz|x|pcs|cm|mm)?\s+(\d+\.\d{2})',
        # Pattern with qty, item, single price (e.g., "2kg Flour 3.50")
        r'(\d+(?:\.\d+)?)\s*(?:kg|g|l|ml|lb|oz|x)?\s+([A-Za-z\s]+?)\s+£?(\d+\.\d{2})',
        # Pattern with item, qty, price (e.g., "Flour 2kg 3.50")
        r'([A-Za-z\s]+?)\s+(\d+(?:\.\d+)?)\s*(?:kg|g|l|ml|lb|oz|x)?\s+£?(\d+\.\d{2})',
        # Pattern with just item and price (e.g., "Flour 3.50")
        r'([A-Za-z\s]+?)\s+£?(\d+\.\d{2})',
    ]

    for line in lines:
        # Skip header lines
        if any(keyword in line.lower() for keyword in ['total', 'subtotal', 'vat', 'tax', 'invoice', 'receipt', 'date', 'code', 'qty', 'price', 'amount']):
            continue

        # Skip very short lines
        if len(line.strip()) < 5:
            continue

        for pattern in item_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()

                try:
                    if len(groups) == 5:
                        # Format: qty, qty_again?, item_name, unit_price, net_amount
                        qty = float(groups[0])
                        item_name = groups[2].strip()
                        unit_price = float(groups[3])
                        net_amount = float(groups[4])

                        if item_name and net_amount > 0:
                            result['line_items'].append({
                                'item_name': item_name,
                                'quantity': qty,
                                'unit_cost': unit_price,  # Use the unit price directly
                                'total_cost': net_amount   # Use the net amount as total
                            })
                            break

                    elif len(groups) == 3:
                        # Could be (qty, item, price) or (item, qty, price)
                        if groups[0].replace('.', '').isdigit() and len(groups[0]) < 5:
                            # First group is quantity
                            qty = float(groups[0])
                            item_name = groups[1].strip()
                            price = float(groups[2])
                        elif groups[1].replace('.', '').isdigit():
                            # Second group is quantity
                            item_name = groups[0].strip()
                            qty = float(groups[1])
                            price = float(groups[2])
                        else:
                            # No quantity found, assume 1
                            item_name = groups[0].strip()
                            qty = 1.0
                            price = float(groups[1])

                        if item_name and price > 0:
                            result['line_items'].append({
                                'item_name': item_name,
                                'quantity': qty,
                                'unit_cost': price / qty if qty > 0 else price,
                                'total_cost': price
                            })
                            break

                    elif len(groups) == 2:
                        # (item, price)
                        item_name = groups[0].strip()
                        price = float(groups[1])
                        if item_name and price > 0:
                            result['line_items'].append({
                                'item_name': item_name,
                                'quantity': 1.0,
                                'unit_cost': price,
                                'total_cost': price
                            })
                            break

                except (ValueError, IndexError):
                    continue

    # Extract total
    total_pattern = r'(?:total|grand\s+total|amount\s+due)[\s:]*£?(\d+\.\d{2})'
    for line in lines:
        total_match = re.search(total_pattern, line, re.IGNORECASE)
        if total_match:
            try:
                result['total_amount'] = float(total_match.group(1))
                break
            except ValueError:
                pass

    return result


def parse_receipt_with_ai(image_bytes: bytes) -> Optional[Dict]:
    """
    Use OpenAI Vision API to parse receipt (if API key is available).
    Falls back to manual parsing if not available.
    """
    import os

    # Check if OpenAI API key is available
    openai_key = os.getenv('OPENAI_API_KEY')

    if not openai_key:
        return None

    try:
        import base64
        import requests

        # Convert image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_key}"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract the following information from this receipt/invoice:
1. Vendor name
2. Vendor email (if present)
3. Vendor phone (if present)
4. Vendor address (if present)
5. Order/invoice date
6. Line items with: item name, quantity, unit cost, total cost
7. Total amount

Return as JSON with this structure:
{
  "vendor_name": "...",
  "vendor_email": "...",
  "vendor_phone": "...",
  "vendor_address": "...",
  "order_date": "YYYY-MM-DD",
  "line_items": [
    {"item_name": "...", "quantity": 1.0, "unit_cost": 10.0, "total_cost": 10.0}
  ],
  "total_amount": 100.0
}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            import json
            result_text = response.json()['choices'][0]['message']['content']

            # Extract JSON from markdown code blocks if present
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            parsed_data = json.loads(result_text)

            # Convert date string to datetime if present
            if parsed_data.get('order_date'):
                try:
                    parsed_data['order_date'] = datetime.fromisoformat(parsed_data['order_date'])
                except:
                    parsed_data['order_date'] = None

            return parsed_data

    except Exception as e:
        st.warning(f"AI parsing failed: {str(e)}")
        return None

    return None


def extract_text_from_image(image_bytes: bytes, filename: str = "") -> str:
    """
    Extract text from image or PDF using pytesseract OCR.
    """
    try:
        from PIL import Image
        import io

        # Check if it's a PDF
        if filename.lower().endswith('.pdf'):
            try:
                import pdf2image
                # Convert PDF to images
                images = pdf2image.convert_from_bytes(image_bytes)

                # Try to import pytesseract
                try:
                    import pytesseract
                    text = ""
                    for img in images:
                        text += pytesseract.image_to_string(img) + "\n"
                    return text
                except ImportError:
                    st.warning("pytesseract not available. Using basic text extraction.")
                    return ""
            except ImportError:
                st.error("pdf2image not installed. Cannot process PDF files. Please upload JPG/PNG instead.")
                return ""
        else:
            # It's an image file
            try:
                # Create a fresh BytesIO object
                image_file = io.BytesIO(image_bytes)
                image = Image.open(image_file)

                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # Try to use pytesseract
                try:
                    import pytesseract
                    text = pytesseract.image_to_string(image)
                    return text
                except ImportError:
                    st.warning("pytesseract not installed. OCR not available. Please add to Streamlit secrets: OPENAI_API_KEY for AI parsing.")
                    return ""

            except Exception as e:
                st.error(f"Error opening image: {str(e)}. Make sure the file is a valid image (JPG, PNG).")
                return ""

    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return ""
