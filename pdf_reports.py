from fpdf import FPDF
from datetime import datetime
import io

class BakeryReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, '🍰 Ohh Crumbs Bakery', 0, 0, 'C')
        self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'R')


def generate_sales_report(sales_data, start_date, end_date):
    pdf = BakeryReportPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Sales Report', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', 0, 1, 'L')
    pdf.ln(5)
    
    if sales_data.empty:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, 'No sales data available for this period.', 0, 1, 'L')
    else:
        total_revenue = sales_data['Total Revenue'].sum()
        total_items = sales_data['Units Sold'].sum()
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Summary', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'Total Revenue: ${total_revenue:,.2f}', 0, 1, 'L')
        pdf.cell(0, 6, f'Total Items Sold: {int(total_items):,}', 0, 1, 'L')
        pdf.cell(0, 6, f'Average Order Value: ${(total_revenue/len(sales_data)):,.2f}', 0, 1, 'L')
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Sales by Item', 0, 1, 'L')
        pdf.set_font('Arial', 'B', 9)
        
        col_widths = [80, 30, 40, 40]
        pdf.cell(col_widths[0], 8, 'Item', 1, 0, 'L')
        pdf.cell(col_widths[1], 8, 'Qty Sold', 1, 0, 'C')
        pdf.cell(col_widths[2], 8, 'Unit Price', 1, 0, 'C')
        pdf.cell(col_widths[3], 8, 'Revenue', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        
        for _, row in sales_data.iterrows():
            pdf.cell(col_widths[0], 6, str(row['Item'])[:30], 1, 0, 'L')
            pdf.cell(col_widths[1], 6, str(int(row['Units Sold'])), 1, 0, 'C')
            pdf.cell(col_widths[2], 6, f"${row['Sale Price']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"${row['Total Revenue']:,.2f}", 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')


def generate_profit_report(profit_data):
    pdf = BakeryReportPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Profit Analysis Report', 0, 1, 'L')
    pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'L')
    pdf.ln(5)
    
    if profit_data.empty:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, 'No profit data available.', 0, 1, 'L')
    else:
        avg_margin = profit_data['Margin %'].mean()
        total_profit = profit_data['Total Profit'].sum()
        total_revenue = profit_data['Total Revenue'].sum()
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Summary', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'Average Profit Margin: {avg_margin:.1f}%', 0, 1, 'L')
        pdf.cell(0, 6, f'Total Profit: ${total_profit:,.2f}', 0, 1, 'L')
        pdf.cell(0, 6, f'Total Revenue: ${total_revenue:,.2f}', 0, 1, 'L')
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Profitability by Item', 0, 1, 'L')
        pdf.set_font('Arial', 'B', 8)
        
        col_widths = [50, 25, 25, 25, 25, 25]
        pdf.cell(col_widths[0], 8, 'Item', 1, 0, 'L')
        pdf.cell(col_widths[1], 8, 'Cost', 1, 0, 'C')
        pdf.cell(col_widths[2], 8, 'Price', 1, 0, 'C')
        pdf.cell(col_widths[3], 8, 'Profit', 1, 0, 'C')
        pdf.cell(col_widths[4], 8, 'Margin %', 1, 0, 'C')
        pdf.cell(col_widths[5], 8, 'Sold', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 8)
        
        sorted_data = profit_data.sort_values('Margin %', ascending=False)
        
        for _, row in sorted_data.iterrows():
            pdf.cell(col_widths[0], 6, str(row['Item'])[:20], 1, 0, 'L')
            pdf.cell(col_widths[1], 6, f"${row['Cost']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[2], 6, f"${row['Sale Price']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"${row['Profit per Item']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[4], 6, f"{row['Margin %']:.1f}%", 1, 0, 'C')
            pdf.cell(col_widths[5], 6, str(int(row['Units Sold'])), 1, 1, 'C')
        
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Recommendations', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        
        high_margin = sorted_data[sorted_data['Margin %'] > 60]
        if not high_margin.empty:
            pdf.multi_cell(0, 5, f'High-margin items (>60%): {", ".join(high_margin["Item"].head(3).tolist())}. Consider promoting these items.')
            pdf.ln(2)
        
        low_margin = sorted_data[sorted_data['Margin %'] < 30]
        if not low_margin.empty:
            pdf.multi_cell(0, 5, f'Low-margin items (<30%): {", ".join(low_margin["Item"].head(3).tolist())}. Consider raising prices or reducing costs.')
    
    return pdf.output(dest='S').encode('latin-1')


def generate_inventory_report(ingredients_data, low_stock_items):
    pdf = BakeryReportPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Inventory Report', 0, 1, 'L')
    pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'L')
    pdf.ln(5)
    
    if ingredients_data.empty:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, 'No ingredient data available.', 0, 1, 'L')
    else:
        total_value = (ingredients_data['current_stock'] * ingredients_data['cost_per_unit']).sum()
        total_items = len(ingredients_data)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Summary', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'Total Ingredients: {total_items}', 0, 1, 'L')
        pdf.cell(0, 6, f'Total Inventory Value: ${total_value:,.2f}', 0, 1, 'L')
        pdf.cell(0, 6, f'Low Stock Items: {len(low_stock_items)}', 0, 1, 'L')
        pdf.ln(5)
        
        if low_stock_items:
            pdf.set_font('Arial', 'B', 12)
            pdf.set_fill_color(255, 230, 230)
            pdf.cell(0, 8, 'Low Stock Alerts', 0, 1, 'L', fill=True)
            pdf.set_font('Arial', 'B', 9)
            
            col_widths = [60, 30, 30, 40, 30]
            pdf.cell(col_widths[0], 8, 'Ingredient', 1, 0, 'L')
            pdf.cell(col_widths[1], 8, 'Stock', 1, 0, 'C')
            pdf.cell(col_widths[2], 8, 'Threshold', 1, 0, 'C')
            pdf.cell(col_widths[3], 8, 'Supplier', 1, 0, 'C')
            pdf.cell(col_widths[4], 8, 'Priority', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 8)
            
            for item in low_stock_items:
                ing = item['ingredient']
                urgency = item['urgency']
                
                if urgency == 'critical':
                    pdf.set_fill_color(255, 200, 200)
                elif urgency == 'warning':
                    pdf.set_fill_color(255, 240, 200)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                pdf.cell(col_widths[0], 6, str(ing.name)[:25], 1, 0, 'L', fill=True)
                pdf.cell(col_widths[1], 6, f"{ing.current_stock:.1f} {ing.unit}", 1, 0, 'C', fill=True)
                pdf.cell(col_widths[2], 6, f"{item['reorder_threshold']:.1f}", 1, 0, 'C', fill=True)
                pdf.cell(col_widths[3], 6, str(ing.supplier or 'N/A')[:15], 1, 0, 'C', fill=True)
                pdf.cell(col_widths[4], 6, urgency.upper(), 1, 1, 'C', fill=True)
            
            pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Full Inventory', 0, 1, 'L')
        pdf.set_font('Arial', 'B', 9)
        
        col_widths = [60, 25, 30, 30, 45]
        pdf.cell(col_widths[0], 8, 'Ingredient', 1, 0, 'L')
        pdf.cell(col_widths[1], 8, 'Stock', 1, 0, 'C')
        pdf.cell(col_widths[2], 8, 'Unit Cost', 1, 0, 'C')
        pdf.cell(col_widths[3], 8, 'Value', 1, 0, 'C')
        pdf.cell(col_widths[4], 8, 'Supplier', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 8)
        
        for _, ing in ingredients_data.iterrows():
            value = ing['current_stock'] * ing['cost_per_unit']
            
            pdf.cell(col_widths[0], 6, str(ing['name'])[:25], 1, 0, 'L')
            pdf.cell(col_widths[1], 6, f"{ing['current_stock']:.1f} {ing['unit']}", 1, 0, 'C')
            pdf.cell(col_widths[2], 6, f"${ing['cost_per_unit']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"${value:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[4], 6, str(ing['supplier'] or 'N/A')[:18], 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')
