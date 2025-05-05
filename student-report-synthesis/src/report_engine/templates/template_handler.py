"""
Template handler module for managing report templates.

This module provides utilities for working with HTML templates
and rendering them with student data to create reports.
"""

import os
import re
import logging
import base64
from pathlib import Path
from typing import Dict, Any, Optional

# HTML template handling - import Jinja2 first before defining classes
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    logging.warning("Jinja2 not installed. Template rendering will not be available.")
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

# PDF conversion
try:
    import xhtml2pdf.pisa as pisa
except ImportError:
    logging.warning("xhtml2pdf not installed. HTML to PDF conversion will not be available.")
    pisa = None

# Set up logging
logger = logging.getLogger(__name__)


class TemplateHandler:
    """Handler for report templates and rendering."""
    
    def __init__(self, templates_dir: str = "templates", static_dir: str = "static"):
        """
        Initialize the template handler.
        
        Args:
            templates_dir: Directory containing HTML templates
            static_dir: Directory containing static files (images, etc.)
        """
        self.templates_dir = Path(templates_dir)
        self.static_dir = Path(static_dir)
        self.env = self._init_jinja_env()
    
    def _init_jinja_env(self) -> Optional[Environment]:
        """Initialize the Jinja2 environment for template rendering."""
        if Environment is None:
            logger.warning("Jinja2 not available. Install it with: pip install jinja2")
            return None
        
        try:
            env = Environment(
                loader=FileSystemLoader(self.templates_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Add functions to get embedded images
            env.globals['get_image_base64'] = self.get_image_base64
            
            logger.info(f"Jinja2 environment initialized with templates from: {self.templates_dir}")
            return env
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 environment: {str(e)}")
            return None
    
    def get_image_base64(self, image_path: str) -> str:
        """
        Get base64 encoded image for embedding in HTML.
        
        Args:
            image_path: Path to the image relative to static directory
            
        Returns:
            Base64 encoded image string with data URI prefix
        """
        try:
            full_path = self.static_dir / image_path
            if not full_path.exists():
                logger.warning(f"Image not found: {full_path}")
                return ""
                
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml'
            }
            
            ext = full_path.suffix.lower()
            mime_type = mime_types.get(ext, 'application/octet-stream')
            
            with open(full_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                
            return f"data:{mime_type};base64,{encoded}"
            
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {str(e)}")
            return ""
    
    def render_template(self, template_name: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Render an HTML template with the provided data.
        
        Args:
            template_name: Name of the template file
            data: Data to render in the template
            
        Returns:
            Rendered HTML content or None if failed
        """
        if self.env is None:
            logger.error("Cannot render template: Jinja2 environment not initialized")
            return None
        
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(data=data)
            return html_content
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            # If template not found, try to create and use a default template
            try:
                if template_name.endswith("_template.html"):
                    style = template_name.replace("_template.html", "")
                    self.create_default_template(style)
                    # Try again with the new template
                    template = self.env.get_template(template_name)
                    html_content = template.render(data=data)
                    return html_content
            except Exception as nested_e:
                logger.error(f"Failed to create and use default template: {str(nested_e)}")
            return None
    
    def html_to_pdf(self, html_content_or_path: str, output_path: str) -> bool:
        """
        Convert HTML content or file to PDF.
        
        Args:
            html_content_or_path: HTML content string or path to HTML file
            output_path: Path to save the PDF file
            
        Returns:
            True if conversion was successful, False otherwise
        """
        if pisa is None:
            logger.error("Cannot convert HTML to PDF: xhtml2pdf not installed")
            return False
        
        try:
            # Determine if input is a file path or HTML content
            if os.path.exists(html_content_or_path) and html_content_or_path.endswith('.html'):
                # It's a file path
                with open(html_content_or_path, 'r', encoding='utf-8') as html_file:
                    html_content = html_file.read()
            else:
                # It's HTML content
                html_content = html_content_or_path
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Convert HTML to PDF
            with open(output_path, "wb") as pdf_file:
                # Add CSS to improve PDF rendering
                enhanced_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        @page {{
                            size: A4;
                            margin: 1cm;
                        }}
                        body {{
                            font-family: Arial, Helvetica, sans-serif;
                            margin: 0;
                            padding: 0;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}
                        th, td {{
                            padding: 4px;
                            border: 1px solid #ddd;
                        }}
                        th {{
                            background-color: #f2f2f2;
                        }}
                    </style>
                </head>
                <body>
                """
                
                # Check if the HTML content already has <html> tags
                if "<html" in html_content.lower():
                    # Extract body content from the existing HTML
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
                    if body_match:
                        body_content = body_match.group(1)
                        enhanced_html += body_content
                    else:
                        # If we can't extract the body, use the whole content
                        enhanced_html = html_content
                else:
                    # Add the HTML content as-is
                    enhanced_html += html_content
                
                # Close the HTML if we added our own opening tags
                if "<html" not in html_content.lower():
                    enhanced_html += "</body></html>"
                
                # Create PDF
                result = pisa.CreatePDF(
                    src=enhanced_html,
                    dest=pdf_file,
                    encoding="utf-8"
                )
            
            if result.err:
                logger.error(f"Error converting HTML to PDF: {result.err}")
                return False
            
            logger.info(f"HTML successfully converted to PDF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to convert HTML to PDF: {str(e)}")
            return False
    
    def create_default_template(self, style: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Create a default template for the specified style.
        
        Args:
            style: Report style name
            output_path: Optional path to save the template (default: templates/style_template.html)
            
        Returns:
            Path to the created template or None if failed
        """
        template_name = f"{style.lower()}_template.html"
        
        if output_path is None:
            output_path = self.templates_dir / template_name
        
        # Basic HTML template structure
        html_template = self._get_default_template_content(style)
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_template)
            
            logger.info(f"Created default template: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to create default template: {str(e)}")
            return None
    
    def _get_default_template_content(self, style: str) -> str:
        """
        Get the default template content for a style.
        
        Args:
            style: Report style name
            
        Returns:
            Default template HTML content
        """
        # Generic template for any style
        generic_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .school-name {
            font-size: 1.8rem;
            font-weight: bold;
            color: #003366;
        }
        .report-title {
            font-size: 1.4rem;
            margin-bottom: 1rem;
        }
        .student-info {
            margin-bottom: 2rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .signatures {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-box {
            text-align: center;
            width: 40%;
        }
        .signature-line {
            border-top: 1px solid #000;
            margin-top: 2rem;
            padding-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{ data.school.name }}</div>
            <div class="report-title">Student Progress Report - Semester {{ data.semester }} {{ data.year }}</div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{ data.student.name.full_name }}</p>
                    <p><strong>Grade:</strong> {{ data.student.grade }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{ data.student.class }}</p>
                    <p><strong>Teacher:</strong> {{ data.student.teacher.full_name }}</p>
                </div>
            </div>
        </div>
        
        <h4>Academic Performance</h4>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th>Achievement</th>
                    <th>Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in data.subjects %}
                <tr>
                    <td>{{ subject.subject }}</td>
                    <td class="text-center">
                        {{ subject.achievement.label }}
                        {% if subject.achievement.code %}
                        ({{ subject.achievement.code }})
                        {% endif %}
                    </td>
                    <td class="text-center">
                        {{ subject.effort.label }}
                        {% if subject.effort.code %}
                        ({{ subject.effort.code }})
                        {% endif %}
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <h4>Attendance</h4>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Days Present</th>
                    <th>Days Absent</th>
                    <th>Days Late</th>
                    <th>Attendance Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center">{{ data.attendance.present_days }}</td>
                    <td class="text-center">{{ data.attendance.absent_days }}</td>
                    <td class="text-center">{{ data.attendance.late_days }}</td>
                    <td class="text-center">{{ data.attendance.attendance_rate }}%</td>
                </tr>
            </tbody>
        </table>
        
        <h4>General Comment</h4>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>Principal</div>
            </div>
        </div>
        
        <div class="text-center mt-4">
            <small>Report generated on {{ data.report_date }}</small>
        </div>
    </div>
</body>
</html>
"""
        
        # Return style-specific template or generic template
        if style.lower() == "act":
            return self._get_act_template_content()
        elif style.lower() == "nsw":
            return self._get_nsw_template_content()
        else:
            return generic_template
    
    def _get_act_template_content(self) -> str:
        """Get the ACT-specific template content."""
        # ACT template content
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - ACT School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
            border-bottom: 2px solid #003366;
            padding-bottom: 1rem;
        }
        .school-name {
            font-size: 2rem;
            font-weight: bold;
            color: #003366;
        }
        .report-title {
            font-size: 1.5rem;
            margin: 0.5rem 0;
        }
        .student-info {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .section-title {
            background-color: #003366;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        .achievement-code {
            font-weight: bold;
            background-color: #e6f2ff;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .effort-code {
            font-weight: bold;
            background-color: #e6f7e6;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1.5rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 5px solid #003366;
        }
        .signatures {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-box {
            text-align: center;
            width: 40%;
        }
        .signature-line {
            border-top: 1px solid #000;
            margin-top: 2rem;
            padding-top: 0.5rem;
        }
        .legend {
            font-size: 0.8rem;
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.8rem;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{ data.school.name }}</div>
            <div class="report-title">Student Progress Report</div>
            <div>Semester {{ data.semester }} {{ data.year }}</div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{ data.student.name.full_name }}</p>
                    <p><strong>Grade:</strong> {{ data.student.grade }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{ data.student.class }}</p>
                    <p><strong>Teacher:</strong> {{ data.student.teacher.full_name }}</p>
                </div>
            </div>
        </div>
        
        <div class="section-title">Academic Performance</div>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th class="text-center">Achievement</th>
                    <th class="text-center">Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in data.subjects %}
                <tr>
                    <td><strong>{{ subject.subject }}</strong></td>
                    <td class="text-center">
                        <span class="achievement-code">{{ subject.achievement.code }}</span>
                        <div class="small mt-1">{{ subject.achievement.label }}</div>
                    </td>
                    <td class="text-center">
                        <span class="effort-code">{{ subject.effort.code }}</span>
                        <div class="small mt-1">{{ subject.effort.label }}</div>
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="section-title">Attendance</div>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th class="text-center">Days Present</th>
                    <th class="text-center">Days Absent</th>
                    <th class="text-center">Days Late</th>
                    <th class="text-center">Attendance Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center">{{ data.attendance.present_days }}</td>
                    <td class="text-center">{{ data.attendance.absent_days }}</td>
                    <td class="text-center">{{ data.attendance.late_days }}</td>
                    <td class="text-center">{{ data.attendance.attendance_rate }}%</td>
                </tr>
            </tbody>
        </table>
        
        <div class="section-title">General Comment</div>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Class Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>School Principal</div>
            </div>
        </div>
        
        <div class="legend">
            <div><strong>Achievement Scale:</strong></div>
            <div class="row">
                <div class="col-md-3"><span class="achievement-code">O</span> - Outstanding</div>
                <div class="col-md-3"><span class="achievement-code">H</span> - High</div>
                <div class="col-md-2"><span class="achievement-code">A</span> - At Standard</div>
                <div class="col-md-2"><span class="achievement-code">P</span> - Partial</div>
                <div class="col-md-2"><span class="achievement-code">L</span> - Limited</div>
            </div>
            <div class="mt-2"><strong>Effort Scale:</strong></div>
            <div class="row">
                <div class="col-md-3"><span class="effort-code">C</span> - Consistently</div>
                <div class="col-md-3"><span class="effort-code">U</span> - Usually</div>
                <div class="col-md-3"><span class="effort-code">S</span> - Sometimes</div>
                <div class="col-md-3"><span class="effort-code">R</span> - Rarely</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated on {{ data.report_date }}</p>
            <p>{{ data.school.name }} | {{ data.school.suburb }}, {{ data.school.state|upper }}</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_nsw_template_content(self) -> str:
        """Get the NSW-specific template content."""
        # NSW template content
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.student.name.full_name }} - NSW School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
            border-bottom: 2px solid #00539b;
            padding-bottom: 1rem;
        }
        .school-name {
            font-size: 2rem;
            font-weight: bold;
            color: #00539b;
        }
        .report-title {
            font-size: 1.5rem;
            margin: 0.5rem 0;
        }
        .student-info {
            margin: 2rem 0;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .section-title {
            background-color: #00539b;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .subject-table th {
            background-color: #e6f2ff;
        }
        .comment {
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        .achievement-code {
            font-weight: bold;
            background-color: #e6f2ff;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .effort-code {
            font-weight: bold;
            background-color: #e6f7e6;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .general-comment {
            margin: 2rem 0;
            padding: 1.5rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 5px solid #00539b;
        }
        .signatures {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-box {
            text-align: center;
            width: 40%;
        }
        .signature-line {
            border-top: 1px solid #000;
            margin-top: 2rem;
            padding-top: 0.5rem;
        }
        .legend {
            font-size: 0.8rem;
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.8rem;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{ data.school.name }}</div>
            <div class="report-title">Student Achievement Report</div>
            <div>Semester {{ data.semester }} {{ data.year }}</div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{ data.student.name.full_name }}</p>
                    <p><strong>Grade:</strong> {{ data.student.grade }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{ data.student.class }}</p>
                    <p><strong>Teacher:</strong> {{ data.student.teacher.full_name }}</p>
                </div>
            </div>
        </div>
        
        <div class="section-title">Key Learning Areas</div>
        <table class="table table-bordered subject-table">
            <thead>
                <tr>
                    <th>Subject</th>
                    <th class="text-center">Achievement</th>
                    <th class="text-center">Effort</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in data.subjects %}
                <tr>
                    <td><strong>{{ subject.subject }}</strong></td>
                    <td class="text-center">
                        <span class="achievement-code">{{ subject.achievement.code }}</span>
                        <div class="small mt-1">{{ subject.achievement.label }}</div>
                    </td>
                    <td class="text-center">
                        <span class="effort-code">{{ subject.effort.code }}</span>
                        <div class="small mt-1">{{ subject.effort.label }}</div>
                    </td>
                    <td class="comment">{{ subject.comment }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="section-title">Attendance</div>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th class="text-center">Days Present</th>
                    <th class="text-center">Days Absent</th>
                    <th class="text-center">Days Late</th>
                    <th class="text-center">Attendance Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center">{{ data.attendance.present_days }}</td>
                    <td class="text-center">{{ data.attendance.absent_days }}</td>
                    <td class="text-center">{{ data.attendance.late_days }}</td>
                    <td class="text-center">{{ data.attendance.attendance_rate }}%</td>
                </tr>
            </tbody>
        </table>
        
        <div class="section-title">General Comment</div>
        <div class="general-comment">
            {{ data.general_comment }}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{ data.student.teacher.full_name }}</div>
                <div>Class Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ data.school.principal }}</div>
                <div>Principal</div>
            </div>
        </div>
        
        <div class="legend">
            <div><strong>Achievement Scale:</strong></div>
            <div class="row">
                <div class="col-md-4"><span class="achievement-code">A</span> - Outstanding</div>
                <div class="col-md-4"><span class="achievement-code">B</span> - High</div>
                <div class="col-md-4"><span class="achievement-code">C</span> - Sound</div>
            </div>
            <div class="row mt-1">
                <div class="col-md-4"><span class="achievement-code">D</span> - Basic</div>
                <div class="col-md-4"><span class="achievement-code">E</span> - Limited</div>
                <div class="col-md-4"></div>
            </div>
            <div class="mt-2"><strong>Effort Scale:</strong></div>
            <div class="row">
                <div class="col-md-4"><span class="effort-code">H</span> - High</div>
                <div class="col-md-4"><span class="effort-code">S</span> - Satisfactory</div>
                <div class="col-md-4"><span class="effort-code">L</span> - Low</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated on {{ data.report_date }}</p>
            <p>{{ data.school.name }} | {{ data.school.suburb }}, {{ data.school.state|upper }}</p>
        </div>
    </div>
</body>
</html>
"""