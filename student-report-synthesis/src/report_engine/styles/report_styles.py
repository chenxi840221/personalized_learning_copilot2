import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum, auto

# Set up logging
logger = logging.getLogger(__name__)

class ReportStyle(Enum):
    """Enumeration of supported report styles."""
    GENERIC = auto()
    ACT = auto()      # Australian Capital Territory
    NSW = auto()      # New South Wales
    QLD = auto()      # Queensland
    VIC = auto()      # Victoria
    
    @classmethod
    def from_string(cls, style_name: str) -> 'ReportStyle':
        """Convert string to ReportStyle enum."""
        mapping = {
            "generic": cls.GENERIC,
            "act": cls.ACT,
            "nsw": cls.NSW,
            "qld": cls.QLD, 
            "vic": cls.VIC
        }
        return mapping.get(style_name.lower(), cls.GENERIC)


class ReportStyleHandler:
    """Handles different report styles and their configurations."""
    
    def __init__(self, styles_dir: str = "report_styles"):
        """Initialize the ReportStyleHandler with a directory of style configs."""
        self.styles_dir = Path(styles_dir)
        self.styles = {}
        self._load_styles()
        
    def _load_styles(self):
        """Load all style configurations from the styles directory."""
        if not self.styles_dir.exists():
            os.makedirs(self.styles_dir, exist_ok=True)
            self._create_default_styles()
        
        for style_file in self.styles_dir.glob("*.json"):
            try:
                with open(style_file, "r") as f:
                    style_config = json.load(f)
                    style_name = style_file.stem
                    self.styles[style_name] = style_config
                    logger.info(f"Loaded report style: {style_name}")
            except Exception as e:
                logger.error(f"Failed to load style {style_file}: {str(e)}")
    
    def _create_default_styles(self):
        """Create default style configurations if none exist."""
        # Create generic style
        generic_style = {
            "name": "Generic Student Report",
            "description": "A generic student report style with standard subjects",
            "subjects": ["English", "Mathematics", "Science", "Humanities", "Arts", "Physical Education"],
            "achievement_scale": [
                {"code": "A", "label": "Outstanding", "description": "Outstanding achievement of the standard"},
                {"code": "B", "label": "High", "description": "High achievement of the standard"},
                {"code": "C", "label": "Expected", "description": "Meeting the expected standard"},
                {"code": "D", "label": "Basic", "description": "Basic achievement of the standard"},
                {"code": "E", "label": "Limited", "description": "Limited achievement of the standard"}
            ],
            "effort_scale": [
                {"code": "H", "label": "High", "description": "Consistently demonstrates high effort"},
                {"code": "S", "label": "Satisfactory", "description": "Usually demonstrates satisfactory effort"},
                {"code": "L", "label": "Low", "description": "Demonstrates inconsistent effort"}
            ],
            "template_file": "generic_template.html"
        }
        
        # Create ACT style
        act_style = {
            "name": "ACT Student Report",
            "description": "Australian Capital Territory school report format",
            "subjects": [
                "English", 
                "Mathematics", 
                "Humanities and Social Sciences", 
                "Science", 
                "Health and Physical Education", 
                "The Arts"
            ],
            "achievement_scale": [
                {"code": "O", "label": "Outstanding", "description": "Demonstrating outstanding achievement of the standard"},
                {"code": "H", "label": "High", "description": "Demonstrating a high achievement of the standard"},
                {"code": "A", "label": "At Standard", "description": "Demonstrating achievement at the standard"},
                {"code": "P", "label": "Partial", "description": "Demonstrating partial achievement of the standard"},
                {"code": "L", "label": "Limited", "description": "Demonstrating limited achievement of the standard"}
            ],
            "effort_scale": [
                {"code": "C", "label": "Consistently", "description": "Consistently demonstrates the habit/capability"},
                {"code": "U", "label": "Usually", "description": "Usually demonstrates the habit/capability"},
                {"code": "S", "label": "Sometimes", "description": "Sometimes demonstrates the habit/capability"},
                {"code": "R", "label": "Rarely", "description": "Rarely demonstrates the habit/capability"}
            ],
            "capabilities": {
                "social": [
                    "Demonstrates relational awareness",
                    "Demonstrates community awareness",
                    "Demonstrates communication",
                    "Demonstrates collaboration",
                    "Demonstrates leadership",
                    "Demonstrates decision-making",
                    "Demonstrates conflict resolution"
                ],
                "self": [
                    "Demonstrates personal awareness",
                    "Demonstrates emotional awareness",
                    "Demonstrates reflective practice",
                    "Demonstrates goal setting",
                    "Demonstrates emotional regulation",
                    "Demonstrates perseverance and adaptability"
                ]
            },
            "template_file": "act_template.html",
            "logo_file": "act_logo.png"
        }
        
        # Create NSW style
        nsw_style = {
            "name": "NSW Student Report",
            "description": "New South Wales school report format",
            "subjects": [
                "English",
                "Mathematics",
                "Science and Technology",
                "Human Society and its Environment",
                "Creative Arts",
                "Personal Development, Health and Physical Education"
            ],
            "achievement_scale": [
                {"code": "A", "label": "Outstanding", "description": "Your child's achievement in this subject is outstanding. They confidently apply their knowledge and skills in a range of new and complex situations."},
                {"code": "B", "label": "High", "description": "Your child's achievement in this subject is high. They confidently apply their knowledge and skills in a range of familiar and new situations."},
                {"code": "C", "label": "Expected", "description": "Your child's achievement in this subject is at the expected standard. They apply their knowledge and skills in familiar situations."},
                {"code": "D", "label": "Basic", "description": "Your child's achievement in this subject is basic. They apply their knowledge and skills in familiar situations with support."},
                {"code": "E", "label": "Limited", "description": "Your child's achievement in this subject is limited. They apply their knowledge and skills in some familiar situations with significant support."}
            ],
            "effort_scale": [
                {"code": "H", "label": "High", "description": "Your child actively participates and engages in most learning activities. They always try to complete and present work to a high standard."},
                {"code": "S", "label": "Satisfactory", "description": "Your child actively participates and engages in most learning activities. They regularly try to complete and present work to the required standard."},
                {"code": "L", "label": "Low", "description": "Your child sometimes participates and engages in learning activities. They occasionally try to complete and present work to the required standard."}
            ],
            "social_development": [
                "Displays a positive attitude to learning",
                "Respects the rights and property of others",
                "Respects class and school rules",
                "Shows initiative and enthusiasm",
                "Helps and encourages others"
            ],
            "template_file": "nsw_template.html",
            "logo_file": "nsw_logo.png"
        }
        
        # Create QLD style
        qld_style = {
            "name": "Queensland Student Report",
            "description": "Queensland school report format aligned with Australian Curriculum",
            "subjects": [
                "English",
                "Mathematics",
                "Science",
                "Humanities and Social Sciences",
                "Health and Physical Education",
                "The Arts",
                "Technologies",
                "Languages"
            ],
            "achievement_scale": [
                {"code": "A", "label": "Outstanding", "description": "Your child has demonstrated an exceptional level of knowledge and understanding of the content and concepts."},
                {"code": "B", "label": "High", "description": "Your child has demonstrated a thorough knowledge and understanding of the content and concepts."},
                {"code": "C", "label": "Sound", "description": "Your child has demonstrated a sound knowledge and understanding of the content and concepts."},
                {"code": "D", "label": "Developing", "description": "Your child has demonstrated a basic knowledge and understanding of the content and concepts."},
                {"code": "E", "label": "Support Required", "description": "Your child has demonstrated a limited knowledge and understanding of the content and concepts."}
            ],
            "effort_scale": [
                {"code": "H", "label": "High", "description": "Consistently demonstrates high effort in class activities and learning tasks."},
                {"code": "S", "label": "Satisfactory", "description": "Usually demonstrates satisfactory effort in class activities and learning tasks."},
                {"code": "L", "label": "Low", "description": "Demonstrates inconsistent effort in class activities and learning tasks."}
            ],
            "social_development": [
                "Cooperates and collaborates with others",
                "Demonstrates respectful behavior",
                "Contributes positively to class activities",
                "Shows independence and resilience",
                "Manages personal learning"
            ],
            "work_habits": [
                "Is organized and prepared for learning",
                "Completes tasks to the best of their ability",
                "Works independently and manages time effectively",
                "Follows classroom rules and procedures",
                "Participates actively in learning"
            ],
            "template_file": "qld_template.html",
            "logo_file": "qld_government_logo.png"
        }
        
        # Save default styles
        with open(self.styles_dir / "generic.json", "w") as f:
            json.dump(generic_style, f, indent=2)
        
        with open(self.styles_dir / "act.json", "w") as f:
            json.dump(act_style, f, indent=2)
            
        with open(self.styles_dir / "nsw.json", "w") as f:
            json.dump(nsw_style, f, indent=2)
            
        with open(self.styles_dir / "qld.json", "w") as f:
            json.dump(qld_style, f, indent=2)
        
        # Load the newly created styles
        self._load_styles()
    
    def get_style(self, style_name: str) -> Dict[str, Any]:
        """Get a specific style configuration by name."""
        if style_name.lower() not in self.styles:
            style_name = "generic"
            logger.warning(f"Style '{style_name}' not found, using generic style instead")
        
        return self.styles[style_name.lower()]
    
    def get_available_styles(self) -> List[str]:
        """Get a list of all available style names."""
        return list(self.styles.keys())
    
    def get_achievement_scale(self, style_name: str) -> List[Dict[str, str]]:
        """Get the achievement scale for a specific style."""
        style = self.get_style(style_name)
        return style.get("achievement_scale", [])
    
    def get_effort_scale(self, style_name: str) -> List[Dict[str, str]]:
        """Get the effort scale for a specific style."""
        style = self.get_style(style_name)
        return style.get("effort_scale", [])
    
    def get_subjects(self, style_name: str) -> List[str]:
        """Get the list of subjects for a specific style."""
        style = self.get_style(style_name)
        return style.get("subjects", [])


# Singleton instance for global access
_style_handler = None

def get_style_handler() -> ReportStyleHandler:
    """Get the global ReportStyleHandler instance."""
    global _style_handler
    if _style_handler is None:
        _style_handler = ReportStyleHandler()
    return _style_handler