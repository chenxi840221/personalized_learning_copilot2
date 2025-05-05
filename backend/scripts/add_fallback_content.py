#!/usr/bin/env python3
"""
Script to add fallback content to the database.
This ensures that even if the search service fails, we have some content to show.
"""

import asyncio
import sys
import os
import logging
from pprint import pprint

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define fallback content for each subject
FALLBACK_CONTENT = {
    "Mathematics": [
        {
            "id": "fb-math-001",
            "title": "Introduction to Algebra Concepts",
            "description": "This resource introduces foundational algebra concepts with visual explanations and interactive examples.",
            "content_type": "lesson",
            "difficulty_level": "intermediate",
            "url": "https://www.khanacademy.org/math/algebra",
            "grade_level": [6, 7, 8, 9, 10],
            "topics": ["Algebra", "Mathematics", "Equations"],
            "duration_minutes": 25,
            "keywords": ["algebra", "equations", "variables", "expressions"]
        },
        {
            "id": "fb-math-002",
            "title": "Visual Geometry Learning",
            "description": "An interactive geometry resource with visual demonstrations of shapes, angles, and transformations.",
            "content_type": "interactive",
            "difficulty_level": "beginner",
            "url": "https://www.geogebra.org/geometry",
            "grade_level": [4, 5, 6, 7, 8],
            "topics": ["Geometry", "Mathematics", "Shapes"],
            "duration_minutes": 30,
            "keywords": ["geometry", "shapes", "angles", "transformations"]
        }
    ],
    "Science": [
        {
            "id": "fb-science-001",
            "title": "Introduction to Scientific Method",
            "description": "Learn the scientific method through interactive experiments and real-world examples.",
            "content_type": "lesson",
            "difficulty_level": "beginner",
            "url": "https://www.khanacademy.org/science/high-school-biology/hs-biology-foundations/hs-biology-and-the-scientific-method/a/the-science-of-biology",
            "grade_level": [5, 6, 7, 8, 9],
            "topics": ["Scientific Method", "Science", "Research"],
            "duration_minutes": 20,
            "keywords": ["scientific method", "experiments", "hypothesis", "research"]
        },
        {
            "id": "fb-science-002",
            "title": "Earth's Systems and Cycles",
            "description": "Explore Earth's major systems and cycles including the water cycle, carbon cycle, and weather patterns.",
            "content_type": "video",
            "difficulty_level": "intermediate",
            "url": "https://www.nationalgeographic.org/encyclopedia/earths-systems/",
            "grade_level": [6, 7, 8, 9, 10],
            "topics": ["Earth Science", "Science", "Ecosystems"],
            "duration_minutes": 35,
            "keywords": ["earth science", "water cycle", "weather", "climate"]
        }
    ],
    "English": [
        {
            "id": "fb-english-001",
            "title": "Reading Comprehension Strategies",
            "description": "Learn effective reading comprehension strategies to better understand and analyze texts.",
            "content_type": "lesson",
            "difficulty_level": "intermediate",
            "url": "https://www.readingstrategies.org/comprehension",
            "grade_level": [6, 7, 8, 9, 10],
            "topics": ["Reading", "English", "Comprehension"],
            "duration_minutes": 25,
            "keywords": ["reading", "comprehension", "analysis", "literacy"]
        },
        {
            "id": "fb-english-002",
            "title": "Essay Writing Fundamentals",
            "description": "A comprehensive guide to writing effective essays with structure and clarity.",
            "content_type": "article",
            "difficulty_level": "intermediate",
            "url": "https://owl.purdue.edu/owl/general_writing/academic_writing/essay_writing/index.html",
            "grade_level": [7, 8, 9, 10, 11],
            "topics": ["Writing", "English", "Essays"],
            "duration_minutes": 40,
            "keywords": ["writing", "essays", "structure", "composition"]
        }
    ],
    "History": [
        {
            "id": "fb-history-001",
            "title": "Timeline of World History",
            "description": "Interactive timeline of major events in world history with multimedia resources.",
            "content_type": "interactive",
            "difficulty_level": "intermediate",
            "url": "https://www.bbc.co.uk/history/interactive/timelines/",
            "grade_level": [6, 7, 8, 9, 10],
            "topics": ["World History", "History", "Timeline"],
            "duration_minutes": 30,
            "keywords": ["world history", "timeline", "civilization", "events"]
        },
        {
            "id": "fb-history-002",
            "title": "Primary Source Analysis",
            "description": "Learn techniques for analyzing and interpreting primary historical sources.",
            "content_type": "lesson",
            "difficulty_level": "advanced",
            "url": "https://www.loc.gov/programs/teachers/primary-source-analysis-tool/",
            "grade_level": [8, 9, 10, 11, 12],
            "topics": ["Historical Analysis", "History", "Primary Sources"],
            "duration_minutes": 45,
            "keywords": ["primary sources", "historical analysis", "documents", "research"]
        }
    ],
    "Art": [
        {
            "id": "fb-art-001",
            "title": "Elements of Art & Design Principles",
            "description": "Learn about the basic elements and principles of art and design through visual examples.",
            "content_type": "interactive",
            "difficulty_level": "beginner",
            "url": "https://www.theartstory.org/artists/movements/elements-of-art/",
            "grade_level": [5, 6, 7, 8, 9],
            "topics": ["Art Elements", "Art", "Design"],
            "duration_minutes": 25,
            "keywords": ["elements of art", "design principles", "color theory", "composition"]
        },
        {
            "id": "fb-art-002",
            "title": "Art History Timeline Overview",
            "description": "Explore major art movements and styles throughout history with examples from famous artists.",
            "content_type": "article",
            "difficulty_level": "intermediate",
            "url": "https://www.metmuseum.org/toah/chronology/",
            "grade_level": [7, 8, 9, 10, 11],
            "topics": ["Art History", "Art", "Art Movements"],
            "duration_minutes": 35,
            "keywords": ["art history", "art movements", "famous artists", "painting styles"]
        }
    ],
    "Geography": [
        {
            "id": "fb-geography-001",
            "title": "World Geography Basics",
            "description": "Learn about continents, countries, and major geographical features around the world.",
            "content_type": "interactive",
            "difficulty_level": "beginner",
            "url": "https://www.nationalgeographic.org/education/classroom-resources/mapping/",
            "grade_level": [5, 6, 7, 8],
            "topics": ["World Geography", "Geography", "Maps"],
            "duration_minutes": 30,
            "keywords": ["geography", "continents", "countries", "maps"]
        },
        {
            "id": "fb-geography-002",
            "title": "Climate Zones and Biomes",
            "description": "Explore Earth's major climate zones, biomes, and ecosystems with interactive resources.",
            "content_type": "lesson",
            "difficulty_level": "intermediate",
            "url": "https://www.nationalgeographic.org/encyclopedia/biome/",
            "grade_level": [6, 7, 8, 9, 10],
            "topics": ["Climate", "Geography", "Biomes"],
            "duration_minutes": 35,
            "keywords": ["climate zones", "biomes", "ecosystems", "habitats"]
        }
    ]
}

def get_fallback_content(subject):
    """Get fallback content for a specific subject or a default if not found."""
    if subject in FALLBACK_CONTENT:
        content_list = FALLBACK_CONTENT[subject]
    else:
        # Use Mathematics as default fallback but log a message
        logging.warning(f"No fallback content defined for subject '{subject}'. Using Mathematics fallback content.")
        content_list = FALLBACK_CONTENT["Mathematics"]
    
    # Convert dictionaries to Content objects
    contents = []
    for content_dict in content_list:
        try:
            # Create a copy so we don't modify the original
            modified_dict = dict(content_dict)
            # Make sure we have all required Content fields
            if "topics" not in modified_dict:
                modified_dict["topics"] = [subject]
                
            content = Content(
                id=modified_dict["id"],
                title=modified_dict["title"],
                description=modified_dict["description"],
                content_type=ContentType(modified_dict["content_type"]),
                subject=subject,  # Use the requested subject
                difficulty_level=DifficultyLevel(modified_dict["difficulty_level"]),
                url=modified_dict["url"],
                grade_level=modified_dict["grade_level"],
                keywords=modified_dict["keywords"],
                topics=modified_dict.get("topics", [subject]),
                duration_minutes=modified_dict.get("duration_minutes", 30),
                source="Fallback Content"
            )
            contents.append(content)
            logging.info(f"Created fallback content for '{subject}': {content.title}")
        except Exception as e:
            logging.error(f"Error creating fallback content: {e}")
    
    return contents

# Example of usage
if __name__ == "__main__":
    # Print out some example fallback content
    for subject in FALLBACK_CONTENT:
        contents = get_fallback_content(subject)
        print(f"\n{subject} Fallback Content:")
        for content in contents:
            print(f"  - {content.title} ({content.content_type.value})")
            print(f"    URL: {content.url}")