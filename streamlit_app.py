#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
from io import BytesIO
import re

def parse_manual_input(text_input):
    """Parse manually entered order information"""
    # Initialize default values
    customer_name = "Not specified"
    order_date = "Not specified"
    
    # Try to extract customer name
    customer_patterns = [
        r'Customer[:\s]+([^\n\r]+)',
        r'Name[:\s]+([^\n\r]+)',
        r'Client[:\s]+([^\n\r]+)',
    ]
    
    for pattern in customer_patterns:
        match = re.search(pattern, text_input, re.IGNORECASE)
        if match:
            customer_name = match.group(1).strip()
            break
    
    # Try to extract date
    date_patterns = [
        r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_input, re.IGNORECASE)
        if match:
            order_date = match.group(1).strip()
            break
    
    return customer_name, order_date

def parse_line_items_from_text(text_input):
    """Parse line items from text input"""
    lines = text_input.split('\n')
    items = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip obvious headers
        if any(header in line.lower() for header in ['customer', 'date', 'order', 'invoice']):
            continue
        
        # Look for lines that might contain product info
        # Try to split on common separators
        parts = re.split(r'\s{2,}|\t|,', line)
        
        if len(parts) >= 2:
            clean_parts = [part.strip() for part in parts if part.strip()]
            if len(clean_parts) >= 2:
                # Create item dictionary
                item = {
                    'Product': clean_parts[0] if len(clean_parts) > 0 else '',
                    'Description': clean_parts[1] if len(clean_parts) > 1 else '',
                    'Quantity': clean_parts[2] if len(clean_parts) > 2 else '1',
                    'Price': clean_parts[3] if len(clean_parts) > 3 else '',
                    'Additional_Info': ' | '.join(clean_parts[4:]) if len(clean_parts) > 4 else ''
                }
                items.append(item)
    
    return pd.DataFrame(items) if items else pd.DataFrame()

def calculate_summary_from_manual(df):
    """Calculate summary statistics from manually entered data"""
    total_products = len(df) if not df.empty else 0
    total_quantity = 0
    
    if not df.empty and 'Quantity' in df.columns:
        # Try to sum quantities
        for qty in df['Quantity']:
            try:
                # Extract numbers from quantity field
                numbers = re.findall(r'\d+', str(qty))
                if numbers:
                    total_quantity += int(numbers[0])
            except:
                continue
    
    return total_products, total_quantity if total_quantity > 0 else "Unable to calculate"

def create_sample_data():
    """Create sample data for demonstration"""
    sample_items = [
        {'Product': 'Apples', 'Description': 'Red Delicious', 'Quantity': '5', 'Price': '$10.00', 'Additional_Info': 'Fresh'},
        {'Product': 'Bananas', 'Description': 'Cavendish', 'Quantity': '3', 'Price': '$6.00', 'Additional_Info': 'Organic'},
        {'Product': 'Bread', 'Description': 'Whole Wheat', 'Quantity': '2', 'Price': '$8.00', 'Additional_Info': 'Sliced'},
    ]
    return pd.DataFrame(sample_items)

def main():
    st.title("📋 Order Processor - Manual Entry Version")
    st.markdown("Process order information through manual text entry or CSV upload")
    
    st.info("💡 **Note:** This version allows manual entry of order data since PDF processing libraries are not available on this platform.")
    
    # Tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["📝 Manual Entry", "📁 CSV Upload", "🎯 Sample Data"])
    
    with tab1:
        st.header("📝 Manual Order Entry")
        
        # Manual input fields
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name", placeholder="Enter customer name")
            order_date = st.text_input("Order Date", placeholder="MM/DD/YYYY")
        
        with col2:
            st.markdown("**Or paste order text:**")
            st.caption("Include customer info and line items")
        
        # Text area for bulk input
        text_input = st.text_area(
            "Paste Order Information",
            height=200,
            placeholder="""Example format:
Customer: John Smith
Date: 12/15/2024

Product Name    Description    Quantity    Price
Apples         Red Delicious     5        $10.00
Bananas        Cavendish         3        $6.00
Bread          Whole Wheat       2        $8.00""",
            help="Paste order text here. The app will try to extract customer info and line items."
        )
        
        # Process manual input
        if st.button("🚀 Process Manual Entry", type="primary"):
            if text_input.strip() or (customer_name and order_date):
                # Extract info from text if provided
                if text_input.strip():
                    extracted_customer, extracted_date = parse_manual_input(text_input)
                    final_customer = customer_name if customer_name else extracted_customer
                    final_date = order_date if order_date else extracted_date
                    items_df = parse_line_items_from_text(text_input)
                else:
                    final_customer = customer_name
                    final_date = order_date
                    items_df = pd.DataFrame()
                
                # Calculate summary
                total_products, total_quantity = calculate_summary_from_manual(items_df)
                
                # Display results
                display_results(final_customer, final_date, total_products, total_quantity, items_df, "manual_entry")
            
            else:
                st.warning("⚠️ Please enter either customer information or paste order text.")
    
    with tab2:
        st.header("📁 CSV Upload")
        st.markdown("Upload a CSV file with your order line items")
        
        # CSV upload
        uploaded_csv = st.file_uploader(
            "Choose a CSV file",
            type="csv",
            help="Upload a CSV file with columns like Product, Description, Quantity, etc."
        )
        
        if uploaded_csv is not None:
            try:
                df = pd.read_csv(uploaded_csv)
                st.success(f"✅ CSV uploaded: {uploaded_csv.name}")
                
                # Input customer info
                col1, col2 = st.columns(2)
                with col1:
                    csv_customer = st.text_input("Customer Name (CSV)", placeholder="Enter customer name")
                with col2:
                    csv_date = st.text_input("Order Date (CSV)", placeholder="MM/DD/YYYY")
                
                if st.button("🚀 Process CSV Data", type="primary"):
                    total_products, total_quantity = calculate_summary_from_manual(df)
                    display_results(csv_customer, csv_date, total_products, total_quantity, df, "csv_upload")
            
            except Exception as e:
                st.error(f"❌ Error reading CSV: {str(e)}")
    
    with tab3:
        st.header("🎯 Sample Data Demo")
        st.markdown("See how the app works with sample order data")
        
        if st.button("📊 Load Sample Order", type="primary"):
            sample_df = create_sample_data()
            total_products, total_quantity = calculate_summary_from_manual(sample_df)
            display_results("John Smith", "12/15/2024", total_products, total_quantity, sample_df, "sample_data")

def display_results(customer_name, order_date, total_products, total_quantity, items_df, source):
    """Display the processed results"""
    st.divider()
    
    # Display Order Summary
    st.header("📊 Order Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("👤 Customer Name", customer_name or "Not specified")
        st.metric("📅 Order Date", order_date or "Not specified")
    
    with col2:
        st.metric("📦 Total Products Ordered", total_products)
        st.metric("🔢 Total Quantity Ordered", total_quantity)
    
    # Create summary dataframe
    summary_data = {
        'Customer Name': [customer_name or "Not specified"],
        'Date': [order_date or "Not specified"],
        'Total Products Ordered': [total_products],
        'Total Quantity Ordered': [total_quantity]
    }
    summary_df = pd.DataFrame(summary_data)
    
    st.divider()
    
    # Display Line Items
    st.header("📋 Order Line Items")
    
    if not items_df.empty:
        st.dataframe(items_df, use_container_width=True)
        
        # Download section
        st.divider()
        st.header("📥 Download Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download summary as CSV
            summary_csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📊 Download Summary (CSV)",
                data=summary_csv,
                file_name=f"order_summary_{source}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Download line items as CSV
            items_csv = items_df.to_csv(index=False)
            st.download_button(
                label="📋 Download Line Items (CSV)",
                data=items_csv,
                file_name=f"line_items_{source}.csv",
                mime="text/csv"
            )
        
        with col3:
            # Download combined Excel file
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Order_Summary', index=False)
                items_df.to_excel(writer, sheet_name='Line_Items', index=False)
            
            st.download_button(
                label="📊 Download Complete Report (Excel)",
                data=excel_buffer.getvalue(),
                file_name=f"order_report_{source}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    else:
        st.warning("⚠️ No line items found.")
        
        # Still offer summary download
        summary_csv = summary_df.to_csv(index=False)
        st.download_button(
            label="📊 Download Summary (CSV)",
            data=summary_csv,
            file_name=f"order_summary_{source}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    # Introduction when no processing is happening
    if 'show_intro' not in st.session_state:
        st.session_state.show_intro = True
    
    if st.session_state.show_intro:
        st.markdown("""
        ### 📋 Welcome to Order Processor!
        
        This app helps you process order information and generate summaries. Since PDF processing libraries 
        aren't available on this platform, you can:
        
        **📝 Manual Entry:**
        - Enter customer details manually
        - Paste order text for automatic parsing
        
        **📁 CSV Upload:**
        - Upload existing order data as CSV
        - Add customer information
        
        **🎯 Sample Data:**
        - Try the app with sample order data
        - See the expected output format
        
        ### 📊 Output Format:
        - **Order Summary:** Customer Name, Date, Total Products, Total Quantity
        - **Line Items:** Detailed product table
        - **Downloads:** CSV and Excel formats available
        """)
    
    main()