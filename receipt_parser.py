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

    # Extract vendor name using company-style pattern
    # Look for company names with Ltd, Limited, LLP, PLC
    company_pattern = r'([A-Z][A-Za-z&.\s]+?\s(?:Ltd|Limited|LLP|PLC))'

    # Avoid false matches from page numbers, emails, etc.
    avoid_patterns = [
        r'Page\s+\d+\s+of\s+\d+',
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
    ]

    # Find all company name candidates
    company_matches = []
    for idx, line in enumerate(lines):
        # Skip lines with patterns to avoid
        if any(re.search(avoid, line, re.IGNORECASE) for avoid in avoid_patterns):
            continue

        match = re.search(company_pattern, line)
        if match:
            company_name = match.group(1).strip()
            # Store with line index to prefer those near contact info
            company_matches.append((idx, company_name, line))

    # Choose the best company name (prefer one near email/phone)
    if company_matches:
        # Find email/phone line indices
        email_phone_indices = []
        for idx, line in enumerate(lines):
            if re.search(r'@|phone|tel|sales|accounts', line, re.IGNORECASE):
                email_phone_indices.append(idx)

        # Prefer vendor/supplier names over customer names
        # Filter out lines starting with "Deliver", "Invoice To", "To:", etc.
        supplier_matches = [
            match for match in company_matches
            if not re.match(r'^(Deliver|Invoice To|To:)', match[2], re.IGNORECASE)
        ]

        # Use supplier matches if we found any, otherwise use all matches
        candidates = supplier_matches if supplier_matches else company_matches

        # Pick company name closest to contact info
        if email_phone_indices:
            best_match = min(candidates,
                           key=lambda x: min(abs(x[0] - ei) for ei in email_phone_indices))
            result['vendor_name'] = best_match[1]
        else:
            # No contact info found, just use first match
            result['vendor_name'] = candidates[0][1]

    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for line in lines:
        email_match = re.search(email_pattern, line)
        if email_match:
            result['vendor_email'] = email_match.group()
            break

    # Extract phone - only from lines that contain phone/tel/telephone keywords
    for line in lines:
        # Check if line contains phone-related keywords
        if re.search(r'\b(phone|tel|telephone|sales|accounts)\b', line, re.IGNORECASE):
            # Extract all digits and common phone characters
            phone_chars = re.sub(r'[^\d\s\(\)\+\-]', '', line)
            # Look for UK phone number patterns
            phone_pattern = r'(\+?44\s?7\d{3}\s?\d{6})|(\+?44\s?\d{4}\s?\d{6})|(\(?0\d{4}\)?\s?\d{6})|(\(?0\d{3}\)?\s?\d{3}\s?\d{4})'
            phone_match = re.search(phone_pattern, phone_chars)
            if phone_match:
                # Normalize the phone number (remove spaces, brackets, etc.)
                phone_raw = phone_match.group()
                result['vendor_phone'] = re.sub(r'[\s\(\)]', '', phone_raw)
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

    # Extract line items using robust regex pattern
    # Format: CODE QTY_ORD QTY_DEL DESCRIPTION PRICE PACK NET_AMOUNT
    # Example: "A036 10 10 Adress Diced Apple Pie Mix 19.80 10kg 198.00"
    # Example: "A8102 2 2 Pidy Sablee Fluted Tartlet 9.5cm 38.94 108pcs 77.88"
    # Example: "G3450 1 1 Mather's White Mallow Russe 45.20 12.5kg 45.20"

    matched_lines = []  # Debug: track which lines matched

    # Use verbose regex with named groups for clarity
    # MUCH MORE FLEXIBLE pattern to handle various invoice formats
    line_item_pattern = r'''(?x)  # Enable verbose mode
        ^(?P<code>[A-Z]+\d+[A-Z\d]*)\s+     # Product code: flexible (A002, AB002, A81091, etc.)
        (?P<qty_ord>\d+(?:\.\d+)?)\s+       # Quantity ordered (allows decimals: 1, 2.5, etc.)
        (?P<qty_del>\d+(?:\.\d+)?)\s+       # Quantity delivered (allows decimals)
        (?P<desc>.+?)\s+                    # Description (non-greedy, captures until numbers)
        (?P<price>£?\d+[.,]\d{1,2})\s+      # Unit price (flexible: 5.01, 5,01, 19.8, 46.88)
        (?P<pack>\S+)\s+                    # Pack size (any format: 10kg, Packet, Each, 90pcs, etc.)
        (?P<net>£?\d+[.,]\d{1,2})           # Net amount (flexible decimals)
        (?:\s+[A-Z]\s+\d+)?                 # Optional: VAT code and commodity code
        \s*$                                # End of line
    '''

    # Apply to the full text with multiline mode
    full_text = '\n'.join(lines)

    # Debug: Store search info
    matched_lines.append({
        'pattern_idx': 'DEBUG',
        'line': f'Searching {len(lines)} lines for pattern',
        'groups': {'total_lines': len(lines), 'full_text_length': len(full_text)}
    })

    # Debug: Show sample lines that look like they might be items
    for idx, line in enumerate(lines[:50]):  # First 50 lines
        # Look for lines that start with a letter and digit (product codes)
        if re.match(r'^[A-Z]\d', line):
            matched_lines.append({
                'pattern_idx': 'CANDIDATE',
                'line': f'Line {idx}: {line}',
                'groups': {'might_be_item': True}
            })

    for match in re.finditer(line_item_pattern, full_text, re.MULTILINE | re.VERBOSE):
        matched_dict = match.groupdict()

        # Debug: store match
        matched_lines.append({
            'line': match.group(0),
            'pattern_idx': 0,
            'groups': matched_dict
        })

        try:
            # Extract values
            product_code = matched_dict['code']
            qty = float(matched_dict['qty_ord'])
            item_name = matched_dict['desc'].strip()
            # Remove £ symbol and handle comma decimals
            unit_price_str = matched_dict['price'].replace('£', '').replace(',', '.')
            net_amount_str = matched_dict['net'].replace('£', '').replace(',', '.')
            unit_price = float(unit_price_str)
            net_amount = float(net_amount_str)
            pack_size = matched_dict['pack']

            # Filter out invalid item names
            if (item_name and
                len(item_name) > 2 and
                item_name.lower() not in ['cm', 'mm', 'kg', 'g', 'ml', 'l', 'oz', 'lb', 'z', 'vat', 'tax'] and
                net_amount > 0):
                result['line_items'].append({
                    'item_name': item_name,
                    'quantity': qty,
                    'unit_cost': unit_price,
                    'total_cost': net_amount
                })
        except (ValueError, IndexError, TypeError) as e:
            # Debug: track failed parse attempts
            matched_lines.append({
                'line': match.group(0),
                'pattern_idx': -1,
                'groups': matched_dict,
                'error': str(e)
            })

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

    # Add debug info
    result['_debug_matches'] = matched_lines
    result['_debug_vendor_candidates'] = company_matches if 'company_matches' in locals() else []

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
    Extract text from image or PDF using pytesseract OCR with preprocessing.
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import io
        import numpy as np

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
                        # Preprocess image
                        img = preprocess_image_for_ocr(img)
                        # Use recipe-optimized Tesseract config
                        text += pytesseract.image_to_string(
                            img,
                            lang="eng",
                            config="--oem 3 --psm 4"  # LSTM OCR, assume single column
                        ) + "\n"
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

                    # Preprocess image for better OCR
                    image = preprocess_image_for_ocr(image)

                    # Try multiple PSM modes to find best result
                    # PSM 3 = fully automatic page segmentation (default)
                    # PSM 4 = single column of text
                    # PSM 6 = uniform block of text
                    # PSM 11 = sparse text, find as much as possible

                    # Try PSM 6 first (works well for recipe cards)
                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config="--oem 3 --psm 6"  # Uniform block of text
                    )

                    # If result is too short, try PSM 3 (automatic)
                    if len(text.strip()) < 50:
                        text = pytesseract.image_to_string(
                            image,
                            lang="eng",
                            config="--oem 3 --psm 3"  # Fully automatic
                        )

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


def preprocess_image_for_ocr(image: 'Image.Image') -> 'Image.Image':
    """
    Preprocess image to improve OCR accuracy.
    - Resize to optimal size
    - Increase contrast (moderate)
    - Sharpen
    - Convert to grayscale
    """
    from PIL import Image, ImageEnhance, ImageFilter

    # Resize image if too large (optimal OCR is around 300 DPI)
    max_dimension = 2000
    if max(image.size) > max_dimension:
        ratio = max_dimension / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to grayscale
    image = image.convert('L')

    # Increase contrast (reduced from 2.0 to 1.5 for less aggressive processing)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)

    # Sharpen (less aggressive)
    image = image.filter(ImageFilter.SHARPEN)

    return image
