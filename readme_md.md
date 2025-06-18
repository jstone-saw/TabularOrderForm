# 📋 Order PDF Processor

A Streamlit web application that extracts order information from PDF files and generates structured summaries with line item details.

## 🚀 Features

- **Smart PDF Processing**: Automatically extracts tables and text from PDF files
- **Order Summary**: Generates customer name, date, total products, and quantities
- **Line Item Details**: Displays all product information in a structured table
- **Multiple Export Options**: Download as CSV or Excel formats
- **User-Friendly Interface**: Clean, intuitive web interface

## 📊 Output Format

### Order Summary
- Customer Name
- Order Date
- Total Products Ordered
- Total Quantity Ordered

### Line Items Table
- All product details from the PDF
- Organized rows and columns
- Source table information for debugging

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Java Runtime Environment (required for tabula-py)

### Local Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/order-pdf-processor.git
cd order-pdf-processor
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

4. Open your browser to `http://localhost:8501`

### Streamlit Cloud Deployment

1. Fork this repository to your GitHub account
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub account
4. Deploy the app by selecting this repository
5. Choose `streamlit_app.py` as your main file

## 🔧 Usage

1. **Upload PDF**: Choose an order/invoice PDF file
2. **Configure Options**: Select pages and extraction mode in the sidebar
3. **Process**: Click "Process Order PDF" to extract information
4. **Review**: Check the order summary and line items
5. **Download**: Export results as CSV or Excel files

## 💡 Best Results

- **Text-based PDFs** work better than scanned images
- **Standard invoice/order formats** are recognized more easily
- **Clear table structures** improve extraction accuracy
- Try toggling **stream mode** if extraction doesn't work initially

## 🐛 Troubleshooting

### Common Issues

**"No tables found"**
- Ensure PDF contains actual tables, not images
- Try toggling the "Use stream mode" option
- Check if PDF is text-based rather than scanned

**"Java not found" error**
- Install Java Runtime Environment (JRE)
- Ensure Java is in your system PATH

**Incorrect extraction**
- Try different page ranges
- Use "Custom" pages option for specific pages
- Review raw extracted tables in the debug section

## 📦 Dependencies

- `streamlit` - Web application framework
- `tabula-py` - PDF table extraction
- `pandas` - Data manipulation
- `openpyxl` - Excel file handling
- `java-installer` - Java environment setup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the [tabula-py documentation](https://tabula-py.readthedocs.io/)
3. Open an issue on GitHub with:
   - Error message
   - PDF type/format
   - Steps to reproduce

## 🔄 Version History

- **v1.0.0** - Initial release
  - PDF table extraction
  - Order summary generation
  - Line item processing
  - CSV/Excel export options