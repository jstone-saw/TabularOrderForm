#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import tempfile
import os
from io import BytesIO
import re
from datetime import datetime
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyPDF2"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
    return text

def extract_customer_info(text):
    """Extract customer information from PDF text"""
    customer_name = "Not found"
    order_date = "Not found"
    
    # Try to find customer name (common patterns)
    customer_patterns = [
        r'Customer[:\s]+([^\n\r]+)',
        r'Bill[ing]*\s+To[:\s]*([^\n\r]+)',
        r'Ship[ping]*\s+To[:\s]*([^\n\r]+)',
        r'Name[:\s]+([^\n\r]+)',
        r'Client[:\s]+([^\n\r]+)',
        r'Delivery[:\s]+([^\n\r]+)',
        r'To[:\s]+([A-Z][^\n\r]+)',
    ]
    
    for pattern in customer_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match and customer_name == "Not found":
            potential_name = match.group(1).strip()
            # Clean up common artifacts
            potential_name = re.sub(r'[:\s]+$', '', potential_name)
            potential_name = re.sub(r'^\W+', '', potential_name)
            if len(potential_name) > 2 and not potential_name.isdigit():
                customer_name = potential_name
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

def parse_table_from_text(text):
    """Try to extract table-like data from text"""
    lines = text.split('\n')
    table_data = []
    
    # Look for lines that might be table rows (contain multiple words/numbers)
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip obvious headers/footers
        if any(skip_word in line.lower() for skip_word in ['page', 'total', 'subtotal', 'tax', 'gst']):
            continue
            
        # Look for lines with multiple separated values
        parts = re.split(r'\s{2,}|\t', line)  # Split on multiple spaces or tabs
        if len(parts) >= 2:
            # Clean up parts
            clean_parts = [part.strip() for part in parts if part.strip()]
            if len(clean_parts) >= 2:
                table_data.append(clean_parts)
    
    if table_data:
        # Try to create a DataFrame
        max_cols = max(len(row) for row in table_data)
        
        # Pad rows to same length
        for row in table_data:
            while len(row) < max_cols:
                row.append("")
        
        # Create column names
        columns = [f"Column_{i+1}" for i in range(max_cols)]
        
        df = pd.DataFrame(table_data, columns=columns)
        return df
    
    return pd.DataFrame()

def calculate_summary_stats(df, text):
    """Calculate summary statistics"""
    total_products = len(df) if not df.empty else 0
    total_quantity = 0
    
    # Try to find quantities in the dataframe
    if not df.empty:
        for col in df.columns:
            # Look for numeric values that might be quantities
            numeric_data = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
            if numeric_data.notna().any():
                # If we find reasonable quantities (not prices), sum them
                valid_quantities = numeric_data[(numeric_data > 0) & (numeric_data < 1000)]
                if len(valid_quantities) > 0:
                    total_quantity += valid_quantities.sum()
                    break
    
    # Also try to extract quantities from raw text
    if total_quantity == 0:
        qty_patterns = [
            r'qty[:\s]*(\d+)',
            r'quantity[:\s]*(\d+)',
            r'units[:\s]*(\d+)',
        ]
        
        for pattern in qty_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                total_quantity = sum(int(match) for match in matches if match.isdigit())
                break
    
    return total_products, int(total_quantity) if total_quantity > 0 else "Unable to calculate"

def main():
    st.title("📋 Order PDF Processor (PyPDF2 Version)")
    st.markdown("Extract order summaries from PDF files using text extraction")
    
    st.info("💡 **Note:** This version uses text extraction and may not capture complex table layouts as well as dedicated table extraction tools.")
    
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
            
            # Process PDF button
            if st.button("🚀 Process Order PDF", type="primary"):
                with st.spinner("Processing order PDF..."):
                    try:
                        # Extract text from PDF
                        full_text = extract_text_from_pdf(tmp_file_path)
                        
                        if not full_text.strip():
                            st.error("❌ No text could be extracted from the PDF. The PDF might be image-based or encrypted.")
                            return
                        
                        # Show raw text in expander for debugging
                        with st.expander("🔍 View Extracted Text"):
                            st.text_area("Extracted PDF Text", full_text, height=300)
                        
                        # Extract customer information
                        customer_name, order_date = extract_customer_info(full_text)
                        
                        # Try to parse table data from text
                        items_df = parse_table_from_text(full_text)
                        
                        # Calculate summary stats
                        total_products, total_quantity = calculate_summary_stats(items_df, full_text)
                        
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
                        st.header("📋 Extracted Data")
                        
                        if not items_df.empty:
                            st.subheader("📊 Parsed Table Data")
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
                                # Download parsed data as CSV
                                items_csv = items_df.to_csv(index=False)
                                st.download_button(
                                    label="📋 Download Parsed Data (CSV)",
                                    data=items_csv,
                                    file_name=f"parsed_data_{uploaded_file.name.replace('.pdf', '')}.csv",
                                    mime="text/csv"
                                )
                            
                            with col3:
                                # Download text as file
                                st.download_button(
                                    label="📄 Download Raw Text",
                                    data=full_text,
                                    file_name=f"extracted_text_{uploaded_file.name.replace('.pdf', '')}.txt",
                                    mime="text/plain"
                                )
                        else:
                            st.warning("⚠️ No structured table data could be parsed from the text.")
                            st.info("💡 You can still download the summary and raw text using the buttons below.")
                            
                            # Download options even without table data
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                summary_csv = summary_df.to_csv(index=False)
                                st.download_button(
                                    label="📊 Download Summary (CSV)",
                                    data=summary_csv,
                                    file_name=f"order_summary_{uploaded_file.name.replace('.pdf', '')}.csv",
                                    mime="text/csv"
                                )
                            
                            with col2:
                                st.download_button(
                                    label="📄 Download Raw Text",
                                    data=full_text,
                                    file_name=f"extracted_text_{uploaded_file.name.replace('.pdf', '')}.txt",
                                    mime="text/plain"
                                )
                    
                    except Exception as e:
                        st.error(f"❌ Error processing PDF: {str(e)}")
                        st.info("💡 This might be due to:")
                        st.markdown("""
                        - Encrypted or password-protected PDF
                        - Image-based PDF (scanned document)
                        - Corrupted PDF file
                        - Complex PDF structure
                        """)
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    else:
        st.info("👆 Please upload an order PDF file to get started")
        
        st.markdown("""
        ### 📋 What this version does:
        1. **Extracts text** from PDF files using PyPDF2
        2. **Parses customer information** using pattern matching
        3. **Attempts to identify table-like data** from the text
        4. **Provides downloads** in CSV and text formats
        
        ### ⚠️ Limitations:
        - May not capture complex table layouts perfectly
        - Works best with text-based PDFs
        - Image-based PDFs won't work
        
        ### 💡 Best Results:
        - **Text-based PDFs** (not scanned images)
        - **Simple, clear layouts**
        - **Standard invoice/order formats**
        """)

if __name__ == "__main__":
    main()