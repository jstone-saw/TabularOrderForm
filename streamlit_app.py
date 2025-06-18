#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import tempfile
import os
from io import BytesIO
import re
from datetime import datetime

# Check for Java and tabula-py
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    st.error("❌ tabula-py is not available. Please check the installation.")

# Check Java availability
def check_java():
    """Check if Java is available"""
    try:
        import subprocess
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def extract_customer_info(dfs):
    """Extract customer information from the dataframes"""
    customer_name = "Not found"
    order_date = "Not found"
    
    # Look through all dataframes for customer info
    for df in dfs:
        df_str = df.to_string()
        
        # Try to find customer name (common patterns)
        customer_patterns = [
            r'Customer[:\s]+([^\n\r]+)',
            r'Bill[ing]*\s+To[:\s]+([^\n\r]+)',
            r'Ship[ping]*\s+To[:\s]+([^\n\r]+)',
            r'Name[:\s]+([^\n\r]+)',
            r'Client[:\s]+([^\n\r]+)',
        ]
        
        for pattern in customer_patterns:
            match = re.search(pattern, df_str, re.IGNORECASE)
            if match and customer_name == "Not found":
                customer_name = match.group(1).strip()
                break
        
        # Try to find date (common patterns)
        date_patterns = [
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Order\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, df_str, re.IGNORECASE)
            if match and order_date == "Not found":
                order_date = match.group(1).strip()
                break
    
    return customer_name, order_date

def process_line_items(dfs):
    """Process and combine line items from all dataframes"""
    all_items = []
    
    for i, df in enumerate(dfs):
        # Skip very small dataframes (likely headers or footers)
        if len(df) < 2:
            continue
            
        # Try to identify columns that might contain product info
        df_copy = df.copy()
        
        # Clean up the dataframe
        df_copy = df_copy.dropna(how='all')  # Remove completely empty rows
        
        # Try to identify key columns
        potential_product_cols = []
        potential_qty_cols = []
        potential_price_cols = []
        
        for col in df_copy.columns:
            col_str = str(col).lower()
            col_data = df_copy[col].astype(str).str.lower()
            
            # Product/Description columns
            if any(keyword in col_str for keyword in ['product', 'item', 'description', 'name']):
                potential_product_cols.append(col)
            
            # Quantity columns
            if any(keyword in col_str for keyword in ['qty', 'quantity', 'units', 'count']):
                potential_qty_cols.append(col)
            elif col_data.str.match(r'^\d+$').sum() > len(df_copy) * 0.5:  # Mostly numbers
                potential_qty_cols.append(col)
            
            # Price columns
            if any(keyword in col_str for keyword in ['price', 'cost', 'amount', 'total', '$']):
                potential_price_cols.append(col)
            elif col_data.str.contains(r'[\$£€]|\d+\.\d{2}').sum() > 0:
                potential_price_cols.append(col)
        
        # Add rows to items list
        for idx, row in df_copy.iterrows():
            item_data = {
                'Table_Source': f'Table_{i+1}',
                'Row_Index': idx
            }
            
            # Add all columns
            for col in df_copy.columns:
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
        if any(keyword in col_str for keyword in ['qty', 'quantity', 'units', 'count']):
            try:
                # Clean and convert to numeric
                numeric_values = pd.to_numeric(items_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
                total_quantity += numeric_values.sum()
                break
            except:
                continue
    
    return total_products, int(total_quantity) if total_quantity > 0 else "Unable to calculate"

def main():
    st.title("📋 Order PDF Processor")
    st.markdown("Extract order summaries and line items from PDF files")
    
    # Check dependencies
    if not TABULA_AVAILABLE:
        st.error("❌ **Missing Dependencies**")
        st.markdown("""
        This app requires `tabula-py` and Java to be installed. 
        
        **For Streamlit Cloud deployment:**
        1. Ensure `tabula-py==2.9.0` is in your `requirements.txt`
        2. Add `default-jre` and `default-jdk` to your `packages.txt`
        3. Redeploy the app
        
        **For local development:**
        ```bash
        pip install tabula-py==2.9.0
        # Install Java JRE/JDK on your system
        ```
        """)
        return
    
    if not check_java():
        st.warning("⚠️ **Java Runtime Not Detected**")
        st.markdown("""
        Java is required for PDF processing but wasn't detected. 
        The app may not work properly without Java.
        """)
    
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
            pages_param = st.sidebar.selectbox(
                "Pages to process",
                ["All pages", "First page only", "Custom"],
                help="Most order info is on the first page"
            )
            
            if pages_param == "Custom":
                page_input = st.sidebar.text_input("Page numbers (e.g., 1,2 or 1-3)", value="1")
                pages_param = page_input if page_input else "1"
            elif pages_param == "First page only":
                pages_param = 1
            else:
                pages_param = "all"
            
            use_stream = st.sidebar.checkbox("Use stream mode", value=True)
            
            # Process PDF button
            if st.button("🚀 Process Order PDF", type="primary"):
                with st.spinner("Processing order PDF..."):
                    try:
                        # Extract tables
                        dfs = tabula.read_pdf(
                            tmp_file_path,
                            pages=pages_param,
                            stream=use_stream,
                            multiple_tables=True
                        )
                        
                        if dfs and len(dfs) > 0:
                            # Extract customer information
                            customer_name, order_date = extract_customer_info(dfs)
                            
                            # Process line items
                            items_df = process_line_items(dfs)
                            
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
                                st.warning("⚠️ No line items found. The PDF structure might not be recognized.")
                                
                                # Show raw extracted tables for debugging
                                with st.expander("🔍 View Raw Extracted Tables"):
                                    for i, df in enumerate(dfs):
                                        st.subheader(f"Raw Table {i+1}")
                                        st.dataframe(df)
                        
                        else:
                            st.error("❌ No tables found in the PDF.")
                            st.info("💡 Try adjusting the extraction options or check if the PDF contains extractable tables.")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing PDF: {str(e)}")
                        st.info("💡 Tips:")
                        st.markdown("""
                        - Ensure the PDF contains actual tables (not images)
                        - Try toggling the 'Use stream mode' option
                        - Check if the PDF is text-based and not scanned
                        - Some PDFs may require manual review of the structure
                        """)
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    else:
        st.info("👆 Please upload an order PDF file to get started")
        
        st.markdown("""
        ### 📋 What this app does:
        1. **Extracts order information** from PDF files
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
        - PDFs with clear table structures work best
        - Text-based PDFs (not scanned images)
        - Standard invoice/order formats
        """)

if __name__ == "__main__":
    main()