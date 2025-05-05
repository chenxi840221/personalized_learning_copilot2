"""
Report Engine Package for Student Report Generation System.

This package contains the core components for generating student reports
with AI-powered content using Azure OpenAI.

Modules:
- enhanced_report_generator: Main report generation class
- student_data_generator: Student data generation with realistic profiles
- styles: Report style configurations and handling
- ai: AI integration for content generation
- templates: HTML template handling
- utils: Utility functions for report generation
"""

from src.report_engine.enhanced_report_generator import EnhancedReportGenerator
from src.report_engine.student_data_generator import StudentProfile, SchoolProfile, StudentDataGenerator
__version__ = "1.0.0"
