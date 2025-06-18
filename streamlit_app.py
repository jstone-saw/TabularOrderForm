#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import tempfile
import os
from io import BytesIO
import re
from datetime import datetime
import pdfplumber

def extract_customer_info(text):
    """Extract customer information from PDF text"""
    customer_name = "Not found"
    order_date = "Not found"
    
    # Try to find customer name (common patterns)
    customer_patterns = [
        r'Customer[:\s]+([^\n\r]+)',
        r'Bill[ing]*\s+To[:\s]+([^\n\r]+)',
        r'Ship[ping]*\s+To[:\s]+([^\n\r]+)',
        r'Name[:\s]+([^\n\r]+)',
        r'Client[:\s]+([^\n\r]+)',
        r'Delivery[:\s]+([^\n\r]+)',
    ]
    
    for pattern in customer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and customer_name == "Not found":
            customer_name = match.group(1).strip()
            # Clean up common artifacts
            customer_name = re.sub(r'[:\s]+$', '', customer_name)
            break
    
    # Try to find date (common patterns)
    date_patterns = [
        r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Order\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Invoice\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and order_date == "Not found":
            order_date = match.group(1).strip()
            break
    
    return customer_name, order_date

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF using pdfplumber"""
    tables = []
    all_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text for customer info
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
            
            # Extract tables
            page_tables = page.extract_tables()
            for table_num, table in enumerate(page_tables):
                if table and len(table) > 1:  # Skip empty or single-row tables
                    # Convert to DataFrame
                    headers = table[0] if table[0] else [f"Column_{i}" for i in range(len(table[0]) if table else 0)]
                    data = table[1:] if len(table) > 1 else []
                    
                    if data:
                        df = pd.DataFrame(data, columns=headers)
                        # Clean up the dataframe
                        df = df.dropna(how='all')  # Remove completely empty rows
                        df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns
                        
                        # Add metadata
                        df['_page'] = page_num + 1
                        df['_table'] = table_num + 1
                        
                        tables.append(df)
    
    return tables, all_text

def process_line_items(tables):
    """Process and combine line items from all tables"""
    if not tables:
        return pd.DataFrame()
    
    all_items = []
    
    for i, df in enumerate(tables):
        # Skip very small tables (likely headers or footers)
        if len(df) < 2:
            continue
        
        # Clean up the dataframe
        df_copy = df.copy()
        df_copy = df_copy.dropna(how='all')  # Remove completely empty rows
        
        # Add source information
        for idx, row in df_copy.iterrows():
            item_data = {
                'Table_Source': f'Page_{row.get("_page", "Unknown")}_Table_{row.get("_table", i+1)}',
                'Row_Index': idx
            }
            
            # Add all columns (except metadata)
            for col in df_copy.columns:
                if not col.startswith('_'):
                    item_data[str(col)] = row[col]
            
            all_items.append(item_data)
    
    if all_items:
        items_df = pd.DataFrame(all_items)
        # Remove rows that are mostly empty
        items_df = items_df.dropna(thresh=len(items_df.columns) * 0.3)
        return items_df
    else:
        return pd.DataFrame()

def calculate_summary_stats(items_df):
    """Calculate summary statistics from line items"""
    if items_df.empty:
        return 0, 0
    
    total_products = len(items_df)
    total_quantity = 0
    
    # Try to find quantity columns and sum them
    for col in items_df.columns:
        col_str = str(col).lower()
        if any(keyword in col_str for keyword in ['qty', 'quantity', 'units', 'count', 'qnty']):
            try:
                # Clean and convert to numeric
                numeric_values = pd.to_numeric(
                    items_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), 
                    errors='coerce'
                )
                total_quantity += numeric_values.sum()
                break
            except:
                continue
    
    return total_products, int(total_quantity) if total_quantity > 0 else "Unable to calculate"

def main():
    st.title("📋 Order PDF Processor")
    st.markdown("Extract order summaries and line items from PDF files using pdfplumber")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose an Order PDF file", 
        type="pdf",
        help="Upload a PDF file containing order information"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Extraction options
            st.sidebar.header("⚙️ Extraction Options")
            
            extract_all_pages = st.sidebar.checkbox(
                "Extract from all pages", 
                value=True,
                help="Uncheck to process only the first page"
            )
            
            show_debug = st.sidebar.checkbox(
                "Show debug information", 
                value=False,
                help="Display raw extracted text and tables for debugging"
            )
            
            # Process PDF button
            if st.button("🚀 Process Order PDF", type="primary"):
                with st.spinner("Processing order PDF..."):
                    try:
                        # Extract tables and text from PDF
                        tables, full_text = extract_tables_from_pdf(tmp_file_path)
                        
                        if show_debug:
                            with st.expander("🔍 Debug: Raw Extracted Text"):
                                st.text_area("Full PDF Text", full_text, height=200)
                        
                        # Extract customer information from text
                        customer_name, order_date = extract_customer_info(full_text)
                        
                        # Process line items
                        items_df = process_line_items(tables)
                        
                        # Calculate summary stats
                        total_products, total_quantity = calculate_summary_stats(items_df)
                        
                        # Display Order Summary
                        st.header("📊 Order Summary")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("👤 Customer Name", customer_name)
                            st.metric("📅 Order Date", order_date)
                        
                        with col2:
                            st.metric("📦 Total Products Ordered", total_products)
                            st.metric("🔢 Total Quantity Ordered", total_quantity)
                        
                        # Create summary dataframe for download
                        summary_data = {
                            'Customer Name': [customer_name],
                            'Date': [order_date],
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
                                    file_name=f"order_summary_{uploaded_file.name.replace('.pdf', '')}.csv",
                                    mime="text/csv"
                                )
                            
                            with col2:
                                # Download line items as CSV
                                items_csv = items_df.to_csv(index=False)
                                st.download_button(
                                    label="📋 Download Line Items (CSV)",
                                    data=items_csv,
                                    file_name=f"line_items_{uploaded_file.name.replace('.pdf', '')}.csv",
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
                                    file_name=f"order_report_{uploaded_file.name.replace('.pdf', '')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        
                        else:
                            st.warning("⚠️ No line items found. The PDF structure might not contain recognizable tables.")
                            
                            # Show raw extracted tables for debugging
                            if tables:
                                with st.expander("🔍 View Raw Extracted Tables"):
                                    for i, df in enumerate(tables):
                                        st.subheader(f"Raw Table {i+1}")
                                        st.dataframe(df)
                            else:
                                st.info("💡 No tables were detected in the PDF. This might be a text-only document or the tables might be formatted as images.")
                        
                        if show_debug and tables:
                            with st.expander("🔍 Debug: All Extracted Tables"):
                                for i, df in enumerate(tables):
                                    st.subheader(f"Table {i+1}")
                                    st.dataframe(df)
                    
                    except Exception as e:
                        st.error(f"❌ Error processing PDF: {str(e)}")
                        st.info("💡 Tips:")
                        st.markdown("""
                        - Ensure the PDF contains actual tables (not images of tables)
                        - Check if the PDF is text-based and not scanned
                        - Try enabling debug mode to see what was extracted
                        - Some PDFs may have complex layouts that are difficult to parse
                        """)
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    else:
        st.info("👆 Please upload an order PDF file to get started")
        
        st.markdown("""
        ### 📋 What this app does:
        1. **Extracts order information** from PDF files using pdfplumber
        2. **Creates a summary** with Customer Name, Date, Total Products, Total Quantity
        3. **Displays line items** in a detailed table
        4. **Provides downloads** in CSV and Excel formats
        
        ### 📊 Output Format:
        
        **Order Summary:**
        - Customer Name
        - Order Date  
        - Total Products Ordered
        - Total Quantity Ordered
        
        **Line Items Table:**
        - All product details from the PDF
        - Organized in rows and columns
        - Includes source table information
        
        ### 💡 Best Results:
        - **Text-based PDFs** work better than scanned images
        - **Standard invoice/order formats** are recognized more easily
        - **Clear table structures** improve extraction accuracy
        - Use debug mode to see what text and tables are being extracted
        
        ### 🔧 Technology:
        This app uses **pdfplumber** instead of tabula-py, which:
        - Works reliably on cloud platforms
        - Doesn't require Java installation
        - Handles both text and table extraction
        - Provides better debugging capabilities
        """)

if __name__ == "__main__":
    main()