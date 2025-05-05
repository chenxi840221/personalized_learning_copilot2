"""
Enhanced Report Generator module.

This module provides the main class for generating student reports with
AI-generated content using Azure OpenAI.
"""

import os
import logging
import json
import uuid
import tempfile
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import random

# Import from the refactored structure
from src.report_engine.styles.report_styles import ReportStyle, get_style_handler
from src.report_engine.ai.ai_content_generator import AIContentGenerator
from src.report_engine.templates.template_handler import TemplateHandler
from src.report_engine.student_data_generator import StudentProfile, SchoolProfile, StudentDataGenerator

# Valid DALL-E image sizes
VALID_DALLE_SIZES = ["1024x1024", "1792x1024", "1024x1792"]

# Try to import utility functions
try:
    from src.report_engine.utils.pdf_utils import convert_html_to_pdf
    has_pdf_utils = True
except ImportError:
    has_pdf_utils = False

# PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import cm, mm
except ImportError:
    logging.warning("ReportLab not installed. PDF generation will be limited.")

# Set up logging
logger = logging.getLogger(__name__)


class EnhancedReportGenerator:
    """Enhanced generator for student reports with GPT-4o generated content."""
    
    # In the __init__ method of the EnhancedReportGenerator class:
    def __init__(
        self,
        form_recognizer_endpoint: str,
        form_recognizer_key: str,
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str,
        templates_dir: str = "templates",
        output_dir: str = "output",
        report_styles_dir: str = "report_styles",
        enable_images: bool = False,
        dalle_deployment: str = "dall-e-3"  # Add deployment name for DALL-E
    ):
        """Initialize the Enhanced Report Generator."""
        self.form_recognizer_endpoint = form_recognizer_endpoint
        self.form_recognizer_key = form_recognizer_key
        self.openai_endpoint = openai_endpoint
        self.openai_key = openai_key
        self.openai_deployment = openai_deployment
        self.dalle_deployment = dalle_deployment  # Store DALL-E deployment name
        
        # Directory paths
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.report_styles_dir = Path(report_styles_dir)
        self.static_dir = Path("static")
        
        # Image generation flag
        self.enable_images = enable_images
        
        # Create necessary directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.static_dir, exist_ok=True)
        
        # Initialize components
        self.style_handler = get_style_handler()
        self.template_handler = TemplateHandler(templates_dir=templates_dir, static_dir=str(self.static_dir))
        self.ai_generator = AIContentGenerator(
            openai_endpoint=openai_endpoint,
            openai_key=openai_key,
            openai_deployment=openai_deployment
        )
        
        # Initialize DALL-E image generator if enabled
        # In the __init__ method of EnhancedReportGenerator:
        self.dalle_generator = None
        if self.enable_images:
            try:
                from src.report_engine.ai.dalle_image_generator import DallEImageGenerator
                self.dalle_generator = DallEImageGenerator(
                    openai_endpoint="https://australiaeast.api.cognitive.microsoft.com",  # Base endpoint only
                    openai_key=openai_key,
                    openai_deployment="dall-e-3",
                    api_version="2024-02-01"
                )
                logger.info("DALL-E image generator initialized")
            except ImportError:
                logger.warning("DALL-E image generator not available. Install with: pip install pillow requests")
            except Exception as e:
                logger.error(f"Failed to initialize DALL-E image generator: {str(e)}")
        
        # Check LibreOffice availability for Word document handling
        self.libreoffice_path = self._find_libreoffice()
        
        logger.info(f"Enhanced Report Generator initialized. OpenAI: {'✅' if self.ai_generator.client else '❌'}")
    
    def _init_openai_client(self):
        """Initialize the OpenAI client."""
        try:
            from openai import AzureOpenAI
            
            client = AzureOpenAI(
                api_key=self.openai_key,
                api_version="2023-05-15",
                azure_endpoint=self.openai_endpoint
            )
            
            logger.info(f"OpenAI client initialized with deployment: {self.openai_deployment}")
            return client
            
        except ImportError:
            logger.error("Failed to import OpenAI SDK. Make sure it's installed: pip install openai>=1.0.0")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return None
    
    def _find_libreoffice(self) -> Optional[str]:
        """Find LibreOffice executable for Word document conversion."""
        possible_paths = [
            # Linux
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            # Windows
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found LibreOffice at: {path}")
                return path
        
        logger.warning("LibreOffice not found - Word document conversion may be limited")
        return None
    
    def generate_report(
        self, 
        student_data: Optional[Dict[str, Any]] = None,
        style: str = "generic",
        output_format: str = "pdf",
        comment_length: str = "standard",
        output_path: Optional[str] = None,
        generate_images: bool = False,
        image_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a student report based on provided data or with synthetic data.
        
        Args:
            student_data: Optional student data dictionary
            style: Report style to use (act, nsw, generic, etc.)
            output_format: Output format (pdf or html)
            comment_length: Length of comments (brief, standard, detailed)
            output_path: Optional specific output path
            generate_images: Whether to generate images using DALL-E
            image_options: Options for image generation
            
        Returns:
            Path to the generated report
        """
        # Create a unique ID for this report if not provided
        report_id = str(uuid.uuid4())[:8]
        
        # Generate synthetic student data if not provided
        if not student_data:
            data_generator = StudentDataGenerator(style=style)
            student_profile = data_generator.generate_student_profile()
            school_profile = data_generator.generate_school_profile(state=style if style in ["act", "nsw", "qld", "vic", "sa", "wa", "tas", "nt"] else "act")
            
            # Generate randomized semester and year data
            semester = str(random.randint(1, 2))
            # Use current year minus 0-3 years to create a realistic range
            year = datetime.now().year - random.randint(0, 3)
            
            student_data = {
                "student": student_profile.to_dict(),
                "school": school_profile.to_dict(),
                "report_id": report_id,
                "semester": semester,
                "year": year,
                "report_date": datetime.now().strftime("%d %B %Y")
            }
        
        # Generate images if requested and DALL-E is available
        if generate_images and self.enable_images and self.dalle_generator:
            # Set default image options if not provided
            if image_options is None:
                image_options = {
                    "badge_style": "modern",
                    "badge_colors": ["navy blue", "gold"],
                    "photo_style": "school portrait",
                    "photo_size": "1024x1024"  # Default to a valid DALL-E 3 size
                }
            
            # Validate image size for DALL-E 3
            if "photo_size" in image_options and image_options["photo_size"] not in VALID_DALLE_SIZES:
                logger.warning(f"Invalid DALL-E 3 image size: {image_options['photo_size']}. Using 1024x1024 instead.")
                logger.warning(f"DALL-E 3 only supports these sizes: {', '.join(VALID_DALLE_SIZES)}")
                image_options["photo_size"] = "1024x1024"
            
            try:
                # Check if we need to generate a school badge
                # Only generate if not already provided in the student data
                if "logo_data" not in student_data["school"]:
                    school_name = student_data["school"]["name"]
                    school_type = student_data["school"]["type"]
                    motto = student_data["school"].get("motto")
                    
                    school_logo = self.dalle_generator.generate_school_badge(
                        school_name=school_name,
                        school_type=school_type,
                        style=image_options.get("badge_style", "modern"),
                        colors=image_options.get("badge_colors", ["navy blue", "gold"]),
                        motto=motto,
                        image_size=image_options.get("photo_size", "1024x1024")  # Use validated size
                    )
                    
                    # Add logo to school data
                    student_data["school"]["logo_data"] = school_logo
                    logger.info(f"Generated school badge for {school_name}")
                else:
                    logger.info(f"Using pre-existing school logo for {student_data['school']['name']}")
                
                # Check if we need to generate a student photo
                # Only generate if not already provided in the student data
                if "photo_data" not in student_data["student"]:
                    student_gender = student_data["student"]["gender"]
                    
                    # Determine age from grade
                    grade_str = student_data["student"]["grade"].lower()
                    age = 10  # Default age
                    if "year" in grade_str:
                        try:
                            year_num = int(grade_str.split("year")[1].strip())
                            age = 5 + year_num  # Year 1 = age 6, etc.
                        except:
                            pass
                    elif "kindergarten" in grade_str or "prep" in grade_str:
                        age = 5
                    
                    student_photo = self.dalle_generator.generate_student_photo(
                        gender=student_gender,
                        age=age,
                        style=image_options.get("photo_style", "school portrait"),
                        image_size=image_options.get("photo_size", "1024x1024")  # Use validated size
                    )
                    
                    # Add photo to student data
                    student_data["student"]["photo_data"] = student_photo
                    logger.info(f"Generated student photo for {student_data['student']['name']['first_name']}")
                else:
                    logger.info(f"Using pre-existing student photo for {student_data['student']['name']['first_name']}")
                
            except Exception as e:
                logger.error(f"Error generating images: {str(e)}")
                # Continue without images
        
        # Get the style configuration
        style_config = self.style_handler.get_style(style)
        
        # Generate subject assessments with AI-generated comments
        subjects = style_config.get("subjects", ["English", "Mathematics", "Science"])
        achievement_scale = style_config.get("achievement_scale", [])
        effort_scale = style_config.get("effort_scale", [])
        
        # Extract progress information for AI comment generation
        progress_factor = student_data.get("progress_factor", 0.0)
        sequence_index = student_data.get("sequence_index", 0)
        current_semester = student_data.get("semester", "1")
        current_year = student_data.get("year", datetime.now().year)
        previous_semester = student_data.get("previous_semester")
        previous_year = student_data.get("previous_year")
        
        # If this is a report in a sequence (not the first), we need to adjust achievement and effort
        # to show improvement over time. Performance should generally improve across the reports.
        if sequence_index > 0:
            # Adjust weights based on progress factor to show improvement over time
            achievement_adjustment = min(sequence_index * 0.33, 0.8)  # Maximum 0.8 adjustment
            effort_adjustment = min(sequence_index * 0.33, 0.8)  # Maximum 0.8 adjustment
        else:
            achievement_adjustment = 0
            effort_adjustment = 0
            
        subject_assessments = []
        
        for subject in subjects:
            # Determine achievement level - weight toward the middle
            # Create weights list with the same length as achievement_scale
            achievement_weights = []
            if len(achievement_scale) == 5:
                # Base weights
                base_weights = [0.1, 0.25, 0.4, 0.15, 0.1]  # 5 levels
                
                # For later reports, gradually shift weights toward better achievement
                if achievement_adjustment > 0:
                    # Shift weights toward better achievement (lower indices)
                    achievement_weights = [
                        base_weights[0] + achievement_adjustment * 0.2,  # Increase top level
                        base_weights[1] + achievement_adjustment * 0.3,  # Increase second level
                        base_weights[2] - achievement_adjustment * 0.1,  # Decrease middle
                        base_weights[3] - achievement_adjustment * 0.2,  # Decrease fourth level
                        base_weights[4] - achievement_adjustment * 0.2   # Decrease bottom level
                    ]
                else:
                    achievement_weights = base_weights
            elif len(achievement_scale) == 3:
                # Base weights
                base_weights = [0.25, 0.5, 0.25]  # 3 levels
                
                # For later reports, gradually shift weights toward better achievement
                if achievement_adjustment > 0:
                    # Shift weights toward better achievement (lower indices)
                    achievement_weights = [
                        base_weights[0] + achievement_adjustment * 0.3,  # Increase top level
                        base_weights[1] - achievement_adjustment * 0.1,  # Slight decrease middle
                        base_weights[2] - achievement_adjustment * 0.2   # Decrease bottom level
                    ]
                else:
                    achievement_weights = base_weights
            else:
                # Ensure weights match the length of the scale
                weight_per_item = 1.0 / len(achievement_scale)
                achievement_weights = [weight_per_item] * len(achievement_scale)
            
            achievement_index = random.choices(
                range(len(achievement_scale)), 
                weights=achievement_weights, 
                k=1
            )[0]
            achievement = achievement_scale[achievement_index]
            
            # Determine effort level - usually correlates somewhat with achievement
            effort_weights = []
            if len(effort_scale) == 4:
                # Base weights
                base_weights = [0.4, 0.3, 0.2, 0.1]  # 4 levels
                
                # For later reports, gradually shift weights toward better effort
                if effort_adjustment > 0:
                    # Shift weights toward better effort (lower indices)
                    effort_weights = [
                        base_weights[0] + effort_adjustment * 0.3,  # Increase top level
                        base_weights[1] + effort_adjustment * 0.1,  # Slight increase second level
                        base_weights[2] - effort_adjustment * 0.2,  # Decrease third level
                        base_weights[3] - effort_adjustment * 0.2   # Decrease bottom level
                    ]
                else:
                    effort_weights = base_weights
            elif len(effort_scale) == 3:
                # Base weights
                base_weights = [0.4, 0.4, 0.2]  # 3 levels
                
                # For later reports, gradually shift weights toward better effort
                if effort_adjustment > 0:
                    # Shift weights toward better effort (lower indices)
                    effort_weights = [
                        base_weights[0] + effort_adjustment * 0.3,  # Increase top level
                        base_weights[1] - effort_adjustment * 0.1,  # Slight decrease middle
                        base_weights[2] - effort_adjustment * 0.2   # Decrease bottom level
                    ]
                else:
                    effort_weights = base_weights
            else:
                # Ensure weights match the length of the scale
                weight_per_item = 1.0 / len(effort_scale)
                effort_weights = [weight_per_item] * len(effort_scale)
            
            if random.random() < 0.7:  # 70% chance effort correlates with achievement
                # Adjust effort to be similar to achievement but with some variation
                if achievement_index <= 1:  # High achievement
                    effort_index = 0 if random.random() < 0.7 else 1
                elif achievement_index == 2:  # Middle achievement
                    effort_index = min(random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2], k=1)[0], len(effort_scale) - 1)
                else:  # Lower achievement
                    # Make sure effort_index is within bounds
                    max_index = min(2, len(effort_scale) - 1)
                    effort_index = random.choices(range(1, max_index + 1), k=1)[0]
            else:
                # Sometimes effort doesn't correlate with achievement
                effort_index = random.choices(range(len(effort_scale)), weights=effort_weights, k=1)[0]
            
            effort = effort_scale[effort_index]
            
            # Generate AI comment
            try:
                comment = self.ai_generator.generate_subject_comment(
                    subject=subject,
                    student_profile=student_data["student"],
                    achievement_level=achievement["label"],
                    effort_level=effort["label"],
                    style=style,
                    comment_length=comment_length,
                    progress_factor=progress_factor,
                    sequence_index=sequence_index,
                    semester=current_semester,
                    year=current_year,
                    previous_semester=previous_semester,
                    previous_year=previous_year
                )
            except Exception as e:
                logger.error(f"Error generating AI comment for {subject}: {str(e)}")
                comment = f"The student has shown engagement with the {subject} curriculum this semester."
            
            subject_assessments.append({
                "subject": subject,
                "achievement": achievement,
                "effort": effort,
                "comment": comment
            })
        
        # Add subject assessments to student data
        student_data["subjects"] = subject_assessments
        
        # Generate general comment with AI
        try:
            general_comment = self.ai_generator.generate_general_comment(
                student_profile=student_data["student"],
                subjects_data=subject_assessments,
                school_info=student_data["school"],
                style=style,
                semester=current_semester,
                year=current_year,
                comment_length=comment_length,
                progress_factor=progress_factor,
                sequence_index=sequence_index,
                previous_semester=previous_semester,
                previous_year=previous_year
            )
        except Exception as e:
            logger.error(f"Error generating general comment: {str(e)}")
            general_comment = f"Overall, {student_data['student']['name']['first_name']} has engaged with the learning program this semester, demonstrating strengths and identifying areas for future growth."
        
        student_data["general_comment"] = general_comment
        
        # Generate attendance data if not provided
        if "attendance" not in student_data:
            # Keep total days consistent across all reports for the same student
            total_days = random.randint(45, 55)
            
            # Generate base profile for attendance
            # Most students have generally good attendance
            if random.random() < 0.7:  # 70% have generally good attendance
                attendance_profile = "good"
            elif random.random() < 0.9:  # 20% have moderate attendance issues
                attendance_profile = "moderate"
            else:  # 10% have significant attendance issues
                attendance_profile = "poor"
            
            # Apply profile but adjust based on sequence index for improvement over time
            improvement_factor = sequence_index * 0.15  # 0%, 15%, 30%, 45% improvement
            
            if attendance_profile == "good":
                # Good attendance (0-5 absences) improves slightly over time
                base_absences = random.randint(3, 5)
                base_lates = random.randint(2, 3)
                
                # Reduce absences and lates over time (minimum 0)
                absent_days = max(0, round(base_absences * (1 - improvement_factor)))
                late_days = max(0, round(base_lates * (1 - improvement_factor)))
                
            elif attendance_profile == "moderate":
                # Moderate attendance issues (5-10 absences) show more improvement
                base_absences = random.randint(7, 10)
                base_lates = random.randint(4, 6)
                
                # More significant reduction over time
                absent_days = max(2, round(base_absences * (1 - improvement_factor * 1.2)))
                late_days = max(1, round(base_lates * (1 - improvement_factor * 1.2)))
                
            else:  # poor attendance
                # Poor attendance (10-20 absences) shows most significant improvement
                base_absences = random.randint(12, 18)
                base_lates = random.randint(6, 10)
                
                # Most significant reduction over time
                absent_days = max(4, round(base_absences * (1 - improvement_factor * 1.5)))
                late_days = max(2, round(base_lates * (1 - improvement_factor * 1.5)))
            
            present_days = total_days - absent_days
            
            student_data["attendance"] = {
                "total_days": total_days,
                "present_days": present_days,
                "absent_days": absent_days,
                "late_days": late_days,
                "attendance_rate": round(present_days / total_days * 100, 1),
                "profile": attendance_profile,
                "improvement_factor": improvement_factor
            }
        
        # Determine output path
        if not output_path:
            student_name = student_data["student"]["name"]["full_name"].replace(" ", "_")
            filename = f"{student_name}_{style}_{student_data.get('semester', '1')}_{student_data.get('year', '2024')}"
            
            if output_format.lower() == "html":
                output_path = str(self.output_dir / f"{filename}.html")
            else:
                output_path = str(self.output_dir / f"{filename}.pdf")
        
        # Generate the report in the specified format
        if output_format.lower() == "html":
            return self._generate_html_report(student_data, style, output_path)
        else:
            return self._generate_pdf_report(student_data, style, output_path)
    
    def _generate_html_report(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate an HTML report using templates."""
        try:
            # Get the template name for this style
            style_config = self.style_handler.get_style(style)
            template_name = style_config.get("template_file", f"{style}_template.html")
            
            # Check if template exists, if not, create a default one
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                logger.warning(f"Template {template_name} not found, creating default template")
                self.template_handler.create_default_template(style, str(template_path))
            
            # Render template with data
            html_content = self.template_handler.render_template(template_name, data)
            
            if html_content:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Write HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                logger.info(f"Generated HTML report: {output_path}")
                return output_path
            else:
                # Fallback to a basic HTML if template rendering fails
                simple_html = self._generate_simple_html_report(data)
                
                # Write the simple HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(simple_html)
                    
                logger.warning(f"Used simple HTML fallback for report: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return ""
    
    def _generate_simple_html_report(self, data: Dict[str, Any]) -> str:
        """Generate a simple HTML report as fallback."""
        student = data.get("student", {})
        school = data.get("school", {})
        subjects = data.get("subjects", [])
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.get('name', {}).get('full_name', 'Student')} - School Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #003366; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .comment {{ font-size: 0.9em; }}
        .general-comment {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 15px 0; }}
        .student-info {{ display: flex; }}
        .student-info-text {{ flex: 1; }}
        .student-photo {{ max-width: 120px; border: 1px solid #ddd; margin-left: 20px; }}
    </style>
</head>
<body>
    <h1>{school.get('name', 'School')} Student Report</h1>
    
    <div class="student-info">
        <div class="student-info-text">
            <p><strong>Name:</strong> {student.get('name', {}).get('full_name', '')}</p>
            <p><strong>Grade:</strong> {student.get('grade', '')}</p>
            <p><strong>Class:</strong> {student.get('class', '')}</p>
            <p><strong>Teacher:</strong> {student.get('teacher', {}).get('full_name', '')}</p>
        </div>
        {f'<img src="{student.get("photo_data", "")}" class="student-photo" alt="{student.get("name", {}).get("full_name", "Student")}">' if student.get("photo_data") else ''}
    </div>
    
    <h2>Academic Performance</h2>
    <table>
        <tr>
            <th>Subject</th>
            <th>Achievement</th>
            <th>Effort</th>
            <th>Comments</th>
        </tr>
"""
        
        # Add subject rows
        for subject in subjects:
            subj_name = subject.get('subject', '')
            achievement = subject.get('achievement', {}).get('label', '')
            achievement_code = subject.get('achievement', {}).get('code', '')
            effort = subject.get('effort', {}).get('label', '')
            effort_code = subject.get('effort', {}).get('code', '')
            comment = subject.get('comment', '')
            
            achievement_display = f"{achievement} ({achievement_code})" if achievement_code else achievement
            effort_display = f"{effort} ({effort_code})" if effort_code else effort
            
            html += f"""
        <tr>
            <td>{subj_name}</td>
            <td>{achievement_display}</td>
            <td>{effort_display}</td>
            <td class="comment">{comment}</td>
        </tr>"""
        
        # Add attendance 
        attendance = data.get("attendance", {})
        html += f"""
    </table>
    
    <h2>Attendance</h2>
    <table>
        <tr>
            <th>Days Present</th>
            <th>Days Absent</th>
            <th>Days Late</th>
            <th>Attendance Rate</th>
        </tr>
        <tr>
            <td>{attendance.get('present_days', 0)}</td>
            <td>{attendance.get('absent_days', 0)}</td>
            <td>{attendance.get('late_days', 0)}</td>
            <td>{attendance.get('attendance_rate', 0)}%</td>
        </tr>
    </table>
    
    <h2>General Comment</h2>
    <div class="general-comment">
        {data.get('general_comment', '')}
    </div>
    
    <h2>Signatures</h2>
    <p><strong>Teacher:</strong> {student.get('teacher', {}).get('full_name', '')}</p>
    <p><strong>Principal:</strong> {school.get('principal', '')}</p>
    
    <p><small>Report generated on {data.get('report_date', '')}</small></p>
</body>
</html>
"""
        return html
    
    def _generate_pdf_report(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate a PDF report."""
        try:
            # First generate an HTML version
            html_path = output_path.replace(".pdf", ".html")
            html_output_path = self._generate_html_report(data, style, html_path)
            
            if html_output_path and os.path.exists(html_output_path):
                # Use PDF utils if available
                if has_pdf_utils:
                    from src.report_engine.utils.pdf_utils import convert_html_to_pdf
                    if convert_html_to_pdf(html_path, output_path):
                        logger.info(f"Generated PDF report using pdf_utils: {output_path}")
                        return output_path
                
                # Try to convert HTML to PDF using WeasyPrint
                try:
                    from weasyprint import HTML, CSS
                    
                    # Custom CSS to enhance PDF rendering
                    css_string = """
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
                        .student-photo {
                            max-width: 120px;
                            border: 1px solid #ddd;
                        }
                        .school-logo {
                            max-height: 100px;
                        }
                    """
                    custom_css = CSS(string=css_string)
                    
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    
                    # Convert HTML to PDF
                    HTML(filename=html_path).write_pdf(
                        output_path,
                        stylesheets=[custom_css]
                    )
                    
                    logger.info(f"Generated PDF report with WeasyPrint: {output_path}")
                    return output_path
                except ImportError:
                    logger.info("WeasyPrint not available, falling back to other methods")
                except Exception as e:
                    logger.error(f"Error with WeasyPrint: {str(e)}")
                
                # Try additional PDF conversion methods here...
                # (Additional PDF conversion code omitted for brevity)
            
            # If all HTML to PDF conversions failed or HTML wasn't generated, fallback to ReportLab
            logger.warning("Falling back to ReportLab for PDF generation")
            return self._generate_reportlab_pdf(data, style, output_path)
                
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            return self._generate_reportlab_pdf(data, style, output_path)  # Fallback to ReportLab
    
    def _generate_reportlab_pdf(self, data: Dict[str, Any], style: str, output_path: str) -> str:
        """Generate a PDF report using ReportLab."""
        try:
            # Extract data for easier access
            student = data["student"]
            school = data["school"]
            subjects = data["subjects"]
            
            student_name = student["name"]["full_name"]
            grade = student["grade"]
            class_name = student["class"]
            teacher_name = student["teacher"]["full_name"]
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Custom styles
            title_style.alignment = 1  # Center
            
            subject_style = ParagraphStyle(
                'SubjectHeading',
                parent=styles['Heading3'],
                textColor=colors.navy,
                spaceAfter=6
            )
            
            # Create styles for table cells
            header_style = ParagraphStyle(
                'Header',
                parent=normal_style,
                fontSize=10,
                fontName='Helvetica-Bold',
                alignment=1,  # Center
            )
            
            cell_style = ParagraphStyle(
                'Cell',
                parent=normal_style,
                fontSize=9,
                leading=11,
                wordWrap='CJK',
            )
            
            centered_cell_style = ParagraphStyle(
                'CenteredCell',
                parent=cell_style,
                alignment=1,  # Center
            )
            
            comment_style = ParagraphStyle(
                'Comment',
                parent=normal_style,
                fontSize=8,
                leading=10,
                wordWrap='CJK',
            )
            
            # Build content
            content = []
            
            # Header with school logo if available
            if "logo_data" in school and school["logo_data"]:
                try:
                    # If we have a base64 data URI, extract the image data
                    import base64
                    from io import BytesIO
                    
                    # Extract image data from base64 data URI
                    data_uri = school["logo_data"]
                    if data_uri.startswith("data:image"):
                        # Extract the base64 data
                        img_data = data_uri.split(',')[1]
                        img_bytes = base64.b64decode(img_data)
                        
                        # Create a temporary file for the image
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                            temp_file.write(img_bytes)
                            temp_path = temp_file.name
                        
                        # Add logo to the document
                        logo = Image(temp_path, width=100, height=80)
                        content.append(logo)
                        
                        # Remove the temporary file
                        os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error adding school logo to PDF: {str(e)}")
            
            # School header
            content.append(Paragraph(school["name"], title_style))
            content.append(Paragraph("Student Report", heading_style))
            content.append(Spacer(1, 12))
            
            # Student info with photo if available
            student_info = [
                [Paragraph(f"<b>Student:</b> {student_name}", normal_style)],
                [Paragraph(f"<b>Grade:</b> {grade}", normal_style)],
                [Paragraph(f"<b>Class:</b> {class_name}", normal_style)],
                [Paragraph(f"<b>Teacher:</b> {teacher_name}", normal_style)],
                [Paragraph(f"<b>Report Period:</b> Semester {data.get('semester', '1')} {data.get('year', '2024')}", normal_style)]
            ]
            
            if "photo_data" in student and student["photo_data"]:
                try:
                    # If we have a base64 data URI, extract the image data
                    import base64
                    from io import BytesIO
                    
                    # Extract image data from base64 data URI
                    data_uri = student["photo_data"]
                    if data_uri.startswith("data:image"):
                        # Extract the base64 data
                        img_data = data_uri.split(',')[1]
                        img_bytes = base64.b64decode(img_data)
                        
                        # Create a temporary file for the image
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                            temp_file.write(img_bytes)
                            temp_path = temp_file.name
                        
                        # Add photo to the document
                        student_info_table = Table([
                            [
                                Table(student_info, colWidths=[300]),
                                Image(temp_path, width=120, height=150)
                            ]
                        ], colWidths=[350, 150])
                        
                        student_info_table.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'TOP')
                        ]))
                        
                        content.append(student_info_table)
                        content.append(Spacer(1, 20))
                        
                        # Remove the temporary file
                        os.unlink(temp_path)
                    else:
                        # No image data, fall back to text-only info
                        student_info_table = Table(student_info)
                        content.append(student_info_table)
                        content.append(Spacer(1, 20))
                except Exception as e:
                    logger.error(f"Error adding student photo to PDF: {str(e)}")
                    # Fall back to text-only info
                    student_info_table = Table(student_info)
                    content.append(student_info_table)
                    content.append(Spacer(1, 20))
            else:
                # No image data, use text-only info
                student_info_table = Table(student_info)
                content.append(student_info_table)
                content.append(Spacer(1, 20))
            
            # Academic performance
            content.append(Paragraph("Academic Performance", heading_style))
            content.append(Spacer(1, 6))
            
            # Style-specific label changes
            if style.lower() == "nsw":
                achievement_label = "Achievement"
                effort_label = "Effort"
            elif style.lower() == "act":
                achievement_label = "Achievement"
                effort_label = "Effort"
            else:
                achievement_label = "Achievement"
                effort_label = "Effort"
            
            # Create table for subject assessments
            table_data = [
                [
                    Paragraph("Subject", header_style),
                    Paragraph(achievement_label, header_style),
                    Paragraph(effort_label, header_style),
                    Paragraph("Comments", header_style)
                ]
            ]
            
            for subject_data in subjects:
                subject = subject_data["subject"]
                achievement = subject_data["achievement"]["label"]
                achievement_code = subject_data["achievement"].get("code", "")
                
                effort = subject_data["effort"]["label"]
                effort_code = subject_data["effort"].get("code", "")
                
                comment = subject_data["comment"]
                
                # Add achievement code if available
                achievement_display = f"{achievement} ({achievement_code})" if achievement_code else achievement
                effort_display = f"{effort} ({effort_code})" if effort_code else effort
                
                table_data.append([
                    Paragraph(subject, cell_style),
                    Paragraph(achievement_display, centered_cell_style),
                    Paragraph(effort_display, centered_cell_style),
                    Paragraph(comment, comment_style)
                ])
            
            # Create the table with adjusted column widths
            col_widths = [85, 100, 60, 225]  # Adjusted column widths
            table = Table(table_data, colWidths=col_widths)
            
            # Apply table styling
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align all content to top of cells
                ('LEFTPADDING', (0, 0), (-1, -1), 5),  # Add padding to all cells
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            content.append(table)
            content.append(Spacer(1, 24))
            
            # Attendance
            content.append(Paragraph("Attendance", heading_style))
            content.append(Spacer(1, 6))
            
            attendance = data.get("attendance", {})
            attendance_data = [
                [
                    Paragraph("Days Present", header_style),
                    Paragraph("Days Absent", header_style),
                    Paragraph("Days Late", header_style),
                    Paragraph("Attendance Rate", header_style)
                ],
                [
                    str(attendance.get("present_days", 0)),
                    str(attendance.get("absent_days", 0)),
                    str(attendance.get("late_days", 0)),
                    f"{attendance.get('attendance_rate', 0)}%"
                ]
            ]
            
            attendance_table = Table(attendance_data, colWidths=[120, 120, 120, 120])
            attendance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            content.append(attendance_table)
            content.append(Spacer(1, 24))
            
            # General comment
            content.append(Paragraph("General Comment", heading_style))
            content.append(Spacer(1, 6))
            content.append(Paragraph(data.get("general_comment", ""), normal_style))
            content.append(Spacer(1, 24))
            
            # Signatures
            content.append(Paragraph("Signatures", heading_style))
            content.append(Spacer(1, 6))
            
            signature_data = [
                [
                    Paragraph("Teacher", header_style),
                    Paragraph("Principal", header_style)
                ],
                [
                    teacher_name,
                    school.get("principal", "School Principal")
                ]
            ]
            
            signature_table = Table(signature_data, colWidths=[225, 225])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            content.append(signature_table)
            
            # Build the PDF
            doc.build(content)
            logger.info(f"Generated PDF report with ReportLab: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report with ReportLab: {str(e)}")
            return ""
    
    def generate_batch_reports(
        self, 
        num_reports: int,
        style: str = "generic",
        output_format: str = "pdf",
        comment_length: str = "standard",
        batch_id: Optional[str] = None,
        generate_images: bool = False,
        image_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a batch of synthetic student reports.
        
        For each student, generates reports for four consecutive semesters spanning two years.
        When image generation is enabled, the system will:
        1. Generate student photos and school badges only for the first report of each student
        2. Cache these images in memory
        3. Reuse the cached images for subsequent reports of the same student
        This ensures consistency across different semesters/years for the same student.
        
        Args:
            num_reports: Number of students to generate reports for
            style: Report style to use
            output_format: Output format (pdf or html)
            comment_length: Length of comments (brief, standard, detailed) 
            batch_id: Optional batch ID (generated if not provided)
            generate_images: Whether to generate images using DALL-E
            image_options: Options for image generation
            
        Returns:
            Dictionary with batch information
        """
        # Create or use batch ID
        if not batch_id:
            batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        output_dir = self.output_dir / batch_id
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate reports - for each student, create 4 semester reports over 2 years
        reports = []
        
        # Image cache to store and reuse generated images
        # Structure: {'student_id': {'photo': photo_data_uri, 'school_logo': logo_data_uri}}
        image_cache = {}
        
        for i in range(num_reports):
            student_index = i + 1
            student_id = f"student_{student_index}"
            
            # First, generate student and school profiles that will be shared across all reports
            data_generator = StudentDataGenerator(style=style)
            student_profile = data_generator.generate_student_profile()
            school_profile = data_generator.generate_school_profile(state=style if style in ["act", "nsw", "qld", "vic", "sa", "wa", "tas", "nt"] else "act")
            
            # Set starting year (1-3 years ago)
            base_year = datetime.now().year - random.randint(1, 3)
            
            # Generate 4 reports over 2 years (2 reports per year)
            for semester_index in range(4):
                # Calculate current semester and year
                current_semester = (semester_index % 2) + 1  # Alternates between 1 and 2
                current_year = base_year + (semester_index // 2)  # Changes every 2 semesters
                
                # Calculate progress trend - typically improving over time
                progress_factor = semester_index / 3.0  # 0.0, 0.33, 0.66, 1.0
                
                try:
                    # Create filename with student name, style, semester, and year
                    student_name = student_profile.to_dict()["name"]["full_name"].replace(" ", "_")
                    filename = f"{student_name}_{style}_S{current_semester}_{current_year}"
                    output_path = str(output_dir / f"{filename}.{output_format}")
                    
                    # Create student data with current semester/year
                    student_data = {
                        "student": student_profile.to_dict(),
                        "school": school_profile.to_dict(),
                        "report_id": f"{student_index}_{semester_index}",
                        "semester": str(current_semester),
                        "year": current_year,
                        "report_date": datetime.now().strftime("%d %B %Y"),
                        "progress_factor": progress_factor,  # Used to guide AI comment generation
                        "is_first_report": semester_index == 0,
                        "previous_semester": (2 if current_semester == 1 else 1) if semester_index > 0 else None,
                        "previous_year": (current_year - 1) if current_semester == 1 and semester_index > 0 else current_year,
                        "sequence_index": semester_index  # Position in the sequence of reports
                    }
                    
                    # Check if we should generate images for this report
                    should_generate_images = generate_images
                    
                    # Check if we already have cached images for this student
                    if student_id in image_cache and semester_index > 0:
                        # Reuse the cached images instead of generating new ones
                        if 'photo' in image_cache[student_id]:
                            student_data["student"]["photo_data"] = image_cache[student_id]['photo']
                            logger.info(f"Reusing cached student photo for {student_name} in semester {current_semester}, year {current_year}")
                        
                        if 'school_logo' in image_cache[student_id]:
                            student_data["school"]["logo_data"] = image_cache[student_id]['school_logo']
                            logger.info(f"Reusing cached school logo for {student_name} in semester {current_semester}, year {current_year}")
                        
                        # Since we're reusing cached images, don't generate new ones
                        should_generate_images = False
                    
                    # Generate the report
                    report_path = self.generate_report(
                        student_data=student_data,
                        style=style,
                        output_format=output_format,
                        comment_length=comment_length,
                        output_path=output_path,
                        generate_images=should_generate_images and semester_index == 0,  # Only generate new images for first report
                        image_options=image_options
                    )
                    
                    # After generating the first report, cache the images for reuse
                    if semester_index == 0 and generate_images:
                        image_cache[student_id] = {}
                        
                        # Cache student photo if it was generated
                        if "photo_data" in student_data["student"]:
                            image_cache[student_id]['photo'] = student_data["student"]["photo_data"]
                            logger.info(f"Cached student photo for {student_name}")
                        
                        # Cache school logo if it was generated
                        if "logo_data" in student_data["school"]:
                            image_cache[student_id]['school_logo'] = student_data["school"]["logo_data"]
                            logger.info(f"Cached school logo for {student_name}")
                    
                    if report_path:
                        reports.append({
                            "id": f"report_{student_index}_{semester_index}",
                            "student_name": student_profile.to_dict()["name"]["full_name"],
                            "semester": current_semester,
                            "year": current_year,
                            "path": report_path,
                            "status": "generated"
                        })
                    else:
                        reports.append({
                            "id": f"report_{student_index}_{semester_index}",
                            "status": "failed"
                        })
                except Exception as e:
                    logger.error(f"Error generating report for student {student_index}, semester {current_semester}, year {current_year}: {str(e)}")
                    reports.append({
                        "id": f"report_{student_index}_{semester_index}",
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Create batch information
        batch_result = {
            "batch_id": batch_id,
            "style": style,
            "num_students": num_reports,
            "num_reports": num_reports * 4,  # 4 reports per student
            "format": output_format,
            "reports": reports,
            "status": "completed",
            "completion_time": datetime.now().isoformat()
        }
        
        # Save batch metadata
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(batch_result, f, indent=2)
        
        logger.info(f"Generated {len([r for r in reports if r['status'] == 'generated'])} out of {num_reports * 4} reports for batch {batch_id}")
        return batch_result
    
    def create_zip_archive(self, batch_id: str) -> Optional[str]:
        """
        Create a ZIP archive of all reports in a batch.
        
        Args:
            batch_id: The batch ID
            
        Returns:
            Path to the ZIP archive or None if failed
        """
        import zipfile
        
        batch_dir = self.output_dir / batch_id
        if not batch_dir.exists():
            logger.error(f"Batch directory not found: {batch_dir}")
            return None
        
        zip_path = self.output_dir / f"{batch_id}.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files in the batch directory
                for file_path in batch_dir.glob('*.*'):
                    # Skip the metadata file if desired
                    if file_path.name == "metadata.json":
                        continue
                    
                    # Add file to the archive
                    zipf.write(
                        file_path,
                        arcname=file_path.name
                    )
            
            logger.info(f"Created ZIP archive: {zip_path}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {str(e)}")
            return None