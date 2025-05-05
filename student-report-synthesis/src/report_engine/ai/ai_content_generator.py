"""
AI Content Generator module for generating report content using Azure OpenAI.

This module provides a class for generating personalized student report
comments and other content using the Azure OpenAI API.
"""

import logging
import time
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger(__name__)


class AIContentGenerator:
    """Class for generating dynamic content using Azure OpenAI GPT-4o."""
    
    def __init__(self, openai_endpoint: str, openai_key: str, openai_deployment: str = "gpt-4o"):
        """
        Initialize the AI Content Generator.
        
        Args:
            openai_endpoint: Azure OpenAI endpoint URL
            openai_key: Azure OpenAI API key
            openai_deployment: Azure OpenAI deployment name (default: gpt-4o)
        """
        self.openai_endpoint = openai_endpoint
        self.openai_key = openai_key
        self.openai_deployment = openai_deployment
        self.client = self._init_openai_client()
        
    def _init_openai_client(self):
        """Initialize the Azure OpenAI client."""
        if not self.openai_endpoint or not self.openai_key:
            logger.warning("OpenAI credentials not provided")
            return None
        
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
    
    def generate_subject_comment(
        self,
        subject: str,
        student_profile: Dict[str, Any],
        achievement_level: str,
        effort_level: str,
        style: str = "standard",
        max_retries: int = 3,
        comment_length: str = "standard"
    ) -> str:
        """
        Generate a personalized subject comment using GPT-4o.
        
        Args:
            subject: The subject name
            student_profile: Dictionary containing student information
            achievement_level: The student's achievement level in this subject
            effort_level: The student's effort level in this subject
            style: Report style (act, nsw, etc.)
            max_retries: Maximum number of retries if the API call fails
            comment_length: Length of the comment ('brief', 'standard', 'detailed')
            
        Returns:
            A personalized subject comment
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return f"Unable to generate comment for {subject}."
        
        # Determine gender and pronouns
        gender = student_profile.get("gender", "unknown")
        if gender.lower() == "male":
            pronouns = {"he/him": True}
        elif gender.lower() == "female":
            pronouns = {"she/her": True}
        else:
            pronouns = {"they/them": True}
            
        # Determine word count based on comment length
        word_counts = {
            "brief": "approximately 30-40 words",
            "standard": "approximately 60-80 words",
            "detailed": "approximately 100-150 words"
        }
        word_count = word_counts.get(comment_length, "approximately 60-80 words")
        
        # Construct the prompt
        prompt = f"""As an experienced teacher in an Australian school, write a personalized comment for a student's report card for the subject of {subject}.

STUDENT INFORMATION:
- Name: {student_profile.get('name', {}).get('first_name', 'the student')}
- Gender: {gender} (use appropriate pronouns)
- Year/Grade: {student_profile.get('grade', 'primary school')}
- Achievement Level: {achievement_level}
- Effort Level: {effort_level}

The comment should be {word_count} and should:
1. Be specific to the subject ({subject})
2. Reflect the student's achievement level ({achievement_level})
3. Acknowledge the student's effort level ({effort_level})
4. Include at least one specific strength
5. Include at least one area for improvement or next step in learning
6. Use age-appropriate language for a school report
7. Maintain a positive, constructive, and professional tone
8. Use Australian educational terminology

Write ONLY the comment text with no additional explanations or notes.
"""

        # Try generating the comment with retries
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.openai_deployment,
                    messages=[
                        {"role": "system", "content": "You are an expert teacher assistant that creates personalized, specific, and constructive student report comments following Australian educational standards."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                # Extract and clean up the comment
                comment = response.choices[0].message.content.strip()
                return comment
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retrying
        
        # Fallback comment if all retries fail
        return f"{student_profile.get('name', {}).get('first_name', 'The student')} has demonstrated engagement with the {subject} curriculum this semester. Areas to focus on next include continuing to develop skills and understanding in key concepts."
    
    def generate_general_comment(
        self,
        student_profile: Dict[str, Any],
        subjects_data: List[Dict[str, Any]],
        school_info: Dict[str, Any],
        style: str = "standard",
        semester: str = "1",
        comment_length: str = "standard",
        max_retries: int = 3
    ) -> str:
        """
        Generate a personalized general comment using GPT-4o.
        
        Args:
            student_profile: Dictionary containing student information
            subjects_data: List of dictionaries with subject assessment data
            school_info: Dictionary with school information
            style: Report style (act, nsw, etc.)
            semester: Current semester ("1" or "2")
            comment_length: Length of the comment ('brief', 'standard', 'detailed')
            max_retries: Maximum number of retries if the API call fails
            
        Returns:
            A personalized general comment
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return f"Unable to generate general comment."
        
        # Extract relevant information
        student_name = student_profile.get('name', {}).get('first_name', 'the student')
        gender = student_profile.get("gender", "unknown")
        grade = student_profile.get("grade", "primary school")
        teacher_name = student_profile.get("teacher", {}).get("full_name", "the teacher")
        
        # Create a summary of subject achievements for context
        subject_summary = ""
        strengths = []
        areas_for_improvement = []
        
        for subject_data in subjects_data:
            subject = subject_data.get("subject", "")
            achievement = subject_data.get("achievement", {}).get("label", "")
            
            subject_summary += f"- {subject}: Achievement: {achievement}, "
            subject_summary += f"Effort: {subject_data.get('effort', {}).get('label', '')}\n"
            
            # Identify strengths and areas for improvement based on achievement
            if achievement.lower() in ["outstanding", "high", "above standard"]:
                strengths.append(subject)
            elif achievement.lower() in ["partial", "basic", "limited", "below standard"]:
                areas_for_improvement.append(subject)
        
        # Determine word count based on comment length
        word_counts = {
            "brief": "approximately 80-100 words",
            "standard": "approximately 150-200 words",
            "detailed": "approximately 250-300 words"
        }
        word_count = word_counts.get(comment_length, "approximately 150-200 words")
        
        # Construct the prompt
        prompt = f"""As an experienced teacher in an Australian school, write a personalized general comment for a student's semester {semester} report card.

STUDENT INFORMATION:
- Name: {student_name}
- Gender: {gender}
- Year/Grade: {grade}
- Class Teacher: {teacher_name}

SUBJECT PERFORMANCE SUMMARY:
{subject_summary}

Notable strengths in: {', '.join(strengths) if strengths else 'Various areas'}
Areas for continued development: {', '.join(areas_for_improvement) if areas_for_improvement else 'Ongoing skill development'}

The general comment should be {word_count} and should:
1. Provide an overview of the student's approach to learning and engagement this semester
2. Highlight the student's key strengths across subject areas and as a learner
3. Comment on the student's social development and classroom participation
4. Mention areas for future focus or goals for continued development
5. Conclude with a positive and encouraging note
6. Use age-appropriate language for a school report
7. Maintain a positive, constructive, and professional tone
8. Use Australian educational terminology

Write ONLY the comment text with no additional explanations or notes.
"""

        # Try generating the comment with retries
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.openai_deployment,
                    messages=[
                        {"role": "system", "content": "You are an expert teacher assistant that creates personalized, specific, and constructive student report comments following Australian educational standards."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                
                # Extract and clean up the comment
                comment = response.choices[0].message.content.strip()
                return comment
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retrying
        
        # Fallback comment if all retries fail
        return f"{student_name} has participated in the learning program this semester, engaging with curriculum across subject areas. {student_name} demonstrates developing social skills within the classroom environment. Goals for next semester include continued focus on consistent application of effort and development of skills across all learning areas."