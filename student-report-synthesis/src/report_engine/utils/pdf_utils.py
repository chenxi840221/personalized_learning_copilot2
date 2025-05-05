"""
PDF Utilities Module for converting HTML to PDF.

This module provides functions for converting HTML to PDF using various methods.
"""

import os
import logging
from typing import List, Callable, Optional

# Set up logging
logger = logging.getLogger(__name__)

def convert_html_to_pdf_with_weasyprint(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using WeasyPrint for better CSS support.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Import WeasyPrint
        from weasyprint import HTML, CSS
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Set up custom CSS to improve PDF rendering
        custom_css = CSS(string="""
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                text-align: center;
                display: inline-block;
                height: 25px;
                line-height: 25px;
                vertical-align: middle;
                border: 1px solid #ddd;
                min-width: 25px;
                padding: 0 5px;
                margin: 0 2px;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .achievement-code, .effort-code {
                font-weight: bold;
                padding: 2px 5px;
                border-radius: 3px;
                display: inline-block;
            }
            .achievement-code {
                background-color: #e6f2ff;
            }
            .effort-code {
                background-color: #e6f7e6;
            }
            .subject-name {
                font-weight: bold;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .signature-box {
                width: 45%;
                text-align: center;
                display: inline-block;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
        """)
        
        # Convert HTML to PDF
        HTML(filename=html_path).write_pdf(
            pdf_path,
            stylesheets=[custom_css]
        )
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using WeasyPrint")
        return True
        
    except ImportError:
        logger.warning("WeasyPrint not installed. Try: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"Error with WeasyPrint: {str(e)}")
        return False

def convert_html_to_pdf_with_xhtml2pdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using xhtml2pdf with enhanced styling.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import xhtml2pdf.pisa as pisa
        from bs4 import BeautifulSoup
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Read HTML content
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Parse HTML to add special CSS
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find or create style tag
        style_tag = soup.find('style')
        if not style_tag:
            style_tag = soup.new_tag('style')
            head_tag = soup.find('head')
            if head_tag:
                head_tag.append(style_tag)
            else:
                # Create head if it doesn't exist
                head_tag = soup.new_tag('head')
                soup.html.insert(0, head_tag)
                head_tag.append(style_tag)
        
        # Add PDF-specific CSS
        style_tag.string = (style_tag.string if style_tag.string else "") + """
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                page-break-inside: avoid;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            .rating {
                border: 1px solid #ddd;
                padding: 3px 5px;
                margin: 0 1px;
                display: inline-block;
            }
            .rating.selected {
                background-color: #003366;
                color: white;
            }
            .signature-box {
                width: 45%;
                float: left;
                text-align: center;
                margin: 0 2.5%;
            }
            .signature-line {
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
            }
            .general-comment {
                padding: 10px;
                margin: 15px 0;
                border-left: 5px solid #003366;
                background-color: #f8f9fa;
            }
            .section-header {
                background-color: #f0f0f0;
                padding: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            .subject-name {
                font-weight: bold;
            }
        """
        
        # Pre-process the HTML for xhtml2pdf compatibility
        # Fix inline styling that xhtml2pdf doesn't handle well
        for element in soup.select('.selected'):
            element['style'] = 'background-color: #003366; color: white;'
        
        for element in soup.select('.signature-box'):
            element['style'] = 'width: 45%; display: inline-block; text-align: center; margin: 0 2%;'
        
        for element in soup.select('.signature-line'):
            element['style'] = 'border-top: 1px solid #000; margin-top: 30px; padding-top: 5px;'
        
        # Update HTML content with modifications
        enhanced_html = str(soup)
        
        # Create PDF
        with open(pdf_path, "wb") as pdf_file:
            result = pisa.CreatePDF(
                src=enhanced_html,
                dest=pdf_file,
                encoding="utf-8"
            )
        
        if result.err:
            logger.error(f"Error converting HTML to PDF with xhtml2pdf: {result.err}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using xhtml2pdf")
        return True
    
    except ImportError:
        logger.warning("xhtml2pdf or BeautifulSoup not installed. Try: pip install xhtml2pdf beautifulsoup4")
        return False
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with xhtml2pdf: {str(e)}")
        return False

def convert_html_to_pdf_with_wkhtmltopdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using wkhtmltopdf command line tool.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import subprocess
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Check if wkhtmltopdf is installed
        wkhtmltopdf_paths = [
            'wkhtmltopdf',  # If in PATH
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
        ]
        
        wkhtmltopdf_cmd = None
        for path in wkhtmltopdf_paths:
            try:
                subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                wkhtmltopdf_cmd = path
                break
            except (FileNotFoundError, subprocess.SubprocessError):
                continue
        
        if wkhtmltopdf_cmd is None:
            logger.warning("wkhtmltopdf not found. Install from https://wkhtmltopdf.org/downloads.html")
            return False
        
        # Convert HTML to PDF using wkhtmltopdf
        cmd = [
            wkhtmltopdf_cmd,
            '--enable-local-file-access',
            '--encoding', 'utf-8',
            '--page-size', 'A4',
            '--margin-top', '10mm',
            '--margin-bottom', '10mm',
            '--margin-left', '10mm',
            '--margin-right', '10mm',
            html_path,
            pdf_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logger.error(f"Error with wkhtmltopdf: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using wkhtmltopdf")
        return True
    
    except Exception as e:
        logger.error(f"Failed to convert {html_path} to PDF with wkhtmltopdf: {str(e)}")
        return False

def convert_html_to_pdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using the best available method.
    Tries multiple methods in succession until one succeeds.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    # Set PDF path if not provided
    if pdf_path is None:
        pdf_path = html_path.replace('.html', '.pdf')
    
    # List of conversion methods to try in order
    conversion_methods: List[Callable] = [
        convert_html_to_pdf_with_weasyprint,  # Best CSS support
        convert_html_to_pdf_with_wkhtmltopdf,  # Good rendering
        convert_html_to_pdf_with_xhtml2pdf    # Fallback option
    ]
    
    # Try each method in succession
    for method in conversion_methods:
        try:
            if method(html_path, pdf_path):
                return True
        except Exception as e:
            logger.warning(f"Method {method.__name__} failed: {str(e)}")
            continue
    
    logger.error(f"All PDF conversion methods failed for {html_path}")
    return False