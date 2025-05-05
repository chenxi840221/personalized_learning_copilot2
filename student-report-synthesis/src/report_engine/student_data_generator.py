"""
Student Data Generator module.

This module provides classes for generating realistic student profiles
and school data for report generation with accurate Australian grade levels.
"""

import random
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


class StudentProfile:
    """Class representing a student's profile with realistic attributes."""
    
    # Data for generating realistic students
    FIRST_NAMES_MALE = [
        "Oliver", "Noah", "William", "Jack", "Liam", "Lucas", "Henry", "Ethan",
        "Thomas", "James", "Oscar", "Leo", "Charlie", "Mason", "Alexander", "Ryan",
        "Lachlan", "Harrison", "Cooper", "Daniel", "Aiden", "Isaac", "Hunter", "Benjamin",
        "Max", "Samuel", "Archie", "Patrick", "Felix", "Muhammad", "Xavier", "Jasper"
    ]
    
    FIRST_NAMES_FEMALE = [
        "Charlotte", "Olivia", "Amelia", "Ava", "Mia", "Isla", "Grace", "Willow",
        "Harper", "Ruby", "Ella", "Sophia", "Chloe", "Zoe", "Isabella", "Evie",
        "Sophie", "Sienna", "Ayla", "Matilda", "Ivy", "Layla", "Evelyn", "Alice",
        "Lucy", "Hannah", "Emily", "Abigail", "Maya", "Zara", "Emma", "Lily"
    ]
    
    LAST_NAMES = [
        "Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Johnson", "White",
        "Martin", "Anderson", "Thompson", "Nguyen", "Ryan", "Chen", "Scott", "Davis",
        "Green", "Roberts", "Campbell", "Kelly", "Baker", "Wang", "Singh", "Li",
        "Jackson", "Miller", "Harris", "Young", "Allen", "King", "Lee", "Wright",
        "Thomas", "Robinson", "Lewis", "Hill", "Clarke", "Zhang", "Patel", "Mitchell",
        "Carter", "Phillips", "Evans", "Collins", "Turner", "Parker", "Edwards", "Murphy"
    ]
    
    # Australian names with Indigenous origin
    INDIGENOUS_FIRST_NAMES = [
        "Kirra", "Jarrah", "Talia", "Koa", "Marlee", "Bindi", "Alkira", "Yarran",
        "Allira", "Jedda", "Kyah", "Tanami", "Tallara", "Jayde", "Tianna", "Lowanna",
        "Alinta", "Jarli", "Waru", "Iluka", "Tjandamurra", "Minjarra", "Kurda", "Waratah"
    ]
    
    # Australian names with common Asian backgrounds
    ASIAN_FIRST_NAMES = [
        "Anh", "Chen", "Daiyu", "Eun", "Haruki", "Jin", "Kai", "Lian", "Ming",
        "Nguyen", "Phuong", "Qi", "Ryo", "Seo", "Tran", "Wei", "Xia", "Yi", "Zhen",
        "Hiroshi", "Jiahao", "Kenji", "Li", "Mei", "Nari", "Priya", "Rahul", "Sakura", "Ying"
    ]
    
    ASIAN_LAST_NAMES = [
        "Chen", "Kim", "Lee", "Liu", "Nguyen", "Park", "Singh", "Suzuki", "Tanaka",
        "Wang", "Wong", "Wu", "Xu", "Yang", "Zhang", "Zhao", "Patel", "Khan", "Tran",
        "Chong", "Devi", "Fujimoto", "Gupta", "Hayashi", "Jiang", "Kumar", "Lim", "Nakamura"
    ]
    
    # Middle Eastern and North African names
    MENA_FIRST_NAMES = [
        "Adam", "Ali", "Amir", "Dana", "Farah", "Hasan", "Ibrahim", "Layla", "Mohammed",
        "Noor", "Omar", "Rana", "Sami", "Yasmin", "Zahra", "Zaid", "Kareem", "Leila"
    ]
    
    MENA_LAST_NAMES = [
        "Abbas", "Ahmad", "Ali", "Faraj", "Hassan", "Ibrahim", "Khalil", "Mahmoud",
        "Mansour", "Mohammed", "Mustafa", "Nasser", "Qasim", "Rahman", "Saleh", "Sayegh"
    ]
    
    # Pacific Islander names
    PACIFIC_FIRST_NAMES = [
        "Anahera", "Aroha", "Hemi", "Koa", "Lagi", "Marama", "Moana", "Ngaio",
        "Peni", "Sione", "Talia", "Tane", "Vaiola", "Wiremu", "Lavinia", "Makareta"
    ]
    
    PACIFIC_LAST_NAMES = [
        "Fatu", "Folau", "Hopoate", "Latu", "Mafi", "Manu", "Palu", "Seumanutafa",
        "Talavou", "Taufa", "Tupou", "Williams", "Fifita", "Havea", "Koloamatangi"
    ]
    
    # School-specific data
    TEACHER_TITLES = ["Mr.", "Mrs.", "Ms.", "Dr."]
    
    TEACHER_LAST_NAMES = [
        "Thompson", "Campbell", "Richardson", "Anderson", "Mitchell", "Williams", 
        "Smith", "Johnson", "Rodriguez", "Martinez", "Wilson", "Taylor", "Martin", 
        "Wilson", "Davis", "White", "Jones", "Lee", "Patel", "Brown", "Singh",
        "Chen", "McDonald", "Nguyen", "Harris", "Clark", "Baker", "Adams", "Miller"
    ]
    
    # More realistic principals for Australian schools
    PRINCIPAL_NAMES = [
        "Dr. Sarah Mitchell", "Mr. David Thompson", "Mrs. Jennifer Roberts",
        "Dr. Michael Chen", "Ms. Emily Wilson", "Mr. Andrew Baker",
        "Mrs. Samantha Richardson", "Dr. Robert Zhang", "Ms. Elizabeth Johnson",
        "Mr. Christopher Williams", "Dr. Amanda Singh", "Mrs. Stephanie Clark",
        "Mr. Richard Anderson", "Dr. Karen Martinez", "Ms. Megan Taylor",
        "Mr. John Davidson", "Dr. Patricia Lewis", "Mrs. Michelle Harris",
        "Dr. Robyn Strangward", "Mr. James Robertson"
    ]
    
    # Updated Australian school grades/years with proper pre-school entries
    GRADE_SYSTEMS = {
        "act": ["Preschool", "Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "nsw": ["Preschool", "Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "qld": ["Kindergarten", "Prep", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "vic": ["Three-Year-Old Kindergarten", "Four-Year-Old Kindergarten", "Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "sa": ["Preschool", "Reception", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7"],
        "wa": ["Kindergarten", "Pre-primary", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "tas": ["Kindergarten", "Prep", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "nt": ["Preschool", "Transition", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "generic": ["Preschool", "Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"]
    }
    
    # Common class names used in Australian primary schools
    CLASS_NAMES = {
        # Animals
        "kindergarten": ["Koalas", "Kangaroos", "Possums", "Wombats", "Echidnas", "Kookaburras", "Emus"],
        # First letter of the teacher's surname
        "standard": ["KR", "KT", "KS", "1P", "1M", "1R", "2B", "2W", "2S", "3N", "3L", "3C"],
        # Other naming systems
        "colors": ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"],
        "nature": ["Rainforest", "Ocean", "Desert", "River", "Mountain", "Coral"],
        # Specialized
        "early_learning": ["Butterflies", "Ladybugs", "Caterpillars", "Dragonflies"],
        "montessori": ["Peace", "Harmony", "Discovery", "Curiosity", "Wonder"],
        # Foreign language classes
        "language": ["Llamas", "Dragons", "Tigers", "Eagles", "Dolphins"]
    }
    
    # Learning styles and characteristics 
    LEARNING_STRENGTHS = [
        "visual learning", "auditory learning", "hands-on activities", "reading", "writing",
        "group work", "independent study", "creative projects", "problem-solving", "mathematical reasoning",
        "scientific inquiry", "verbal expression", "artistic expression", "logical thinking",
        "spatial awareness", "memory recall", "pattern recognition", "critical thinking"
    ]
    
    LEARNING_CHALLENGES = [
        "staying focused", "organizing work", "completing tasks on time", "expressing ideas in writing",
        "participating in group discussions", "mathematical concepts", "reading comprehension",
        "spelling", "sitting still for extended periods", "asking for help when needed",
        "managing time effectively", "abstract concepts", "test anxiety", "following multi-step instructions"
    ]
    
    INTERESTS = [
        "art", "music", "sports", "reading", "science", "technology", "nature", "animals",
        "building and construction", "creative writing", "dance", "drama", "cooking",
        "history", "geography", "mathematics", "coding", "gardening", "astronomy"
    ]
    
    SOCIAL_STRENGTHS = [
        "making friends easily", "showing empathy", "resolving conflicts", "including others",
        "working collaboratively", "leadership", "respecting others", "active listening",
        "sharing", "taking turns", "communicating clearly", "helping others", "contributing to discussions"
    ]
    
    def __init__(
        self, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        gender: Optional[str] = None,
        grade: Optional[str] = None,
        style: str = "generic",
        class_name: Optional[str] = None,
        diversity_factor: float = 0.4,
        birth_date: Optional[str] = None
    ):
        """
        Initialize a student profile with either provided or randomly generated attributes.
        
        Args:
            first_name: Optional student first name
            last_name: Optional student last name
            gender: Optional gender ('male', 'female', 'non-binary', or None for random)
            grade: Optional grade/year level
            style: Report style (affects grade naming)
            class_name: Optional class name
            diversity_factor: A float between 0-1 determining likelihood of diverse names
            birth_date: Optional birth date in format "YYYY-MM-DD"
        """
        # Set gender first as names depend on it
        self.gender = gender if gender else random.choice(["male", "female", "non-binary"])
        
        # Set name
        self.first_name = first_name if first_name else self._generate_first_name(diversity_factor)
        self.last_name = last_name if last_name else self._generate_last_name(diversity_factor)
        
        # Set style for grade naming
        self.style = style.lower()
        
        # Set grade based on style - use weighted selection for more realistic distribution
        if grade:
            self.grade = grade
        else:
            self.grade = self._select_grade_with_weights(self.style)
        
        # Set class
        self.class_name = class_name if class_name else self._generate_class_name()
        
        # Generate teacher information
        self.teacher = self._generate_teacher()
        
        # Parent/guardian information
        self.guardians = self._generate_guardians()
        
        # Generate attendance info
        self.attendance = self._generate_attendance()
        
        # Generate birth date
        self.birth_date = birth_date if birth_date else self._generate_birth_date()
        
        # Generate learning profile
        self.learning_profile = self._generate_learning_profile()
    
    def _generate_first_name(self, diversity_factor: float) -> str:
        """Generate a realistic first name based on gender and diversity factor."""
        # Determine which name pool to use based on diversity factor
        name_pool_selector = random.random()
        
        if name_pool_selector < diversity_factor * 0.2:  # Indigenous names (8% of diversity)
            return random.choice(self.INDIGENOUS_FIRST_NAMES)
        elif name_pool_selector < diversity_factor * 0.5:  # Asian names (20% of diversity)
            return random.choice(self.ASIAN_FIRST_NAMES)
        elif name_pool_selector < diversity_factor * 0.7:  # Middle Eastern names (8% of diversity)
            return random.choice(self.MENA_FIRST_NAMES)
        elif name_pool_selector < diversity_factor:  # Pacific Islander names (12% of diversity)
            return random.choice(self.PACIFIC_FIRST_NAMES)
        else:  # Standard Anglo names
            if self.gender == "male":
                return random.choice(self.FIRST_NAMES_MALE)
            elif self.gender == "female":
                return random.choice(self.FIRST_NAMES_FEMALE)
            else:  # non-binary - pick from either list
                return random.choice(self.FIRST_NAMES_MALE + self.FIRST_NAMES_FEMALE)
    
    def _generate_last_name(self, diversity_factor: float) -> str:
        """Generate a realistic last name based on diversity factor."""
        name_pool_selector = random.random()
        
        if name_pool_selector < diversity_factor * 0.4:  # Asian surnames
            return random.choice(self.ASIAN_LAST_NAMES)
        elif name_pool_selector < diversity_factor * 0.7:  # Middle Eastern surnames
            return random.choice(self.MENA_LAST_NAMES)
        elif name_pool_selector < diversity_factor:  # Pacific Islander surnames
            return random.choice(self.PACIFIC_LAST_NAMES)
        else:  # Standard Anglo surnames
            return random.choice(self.LAST_NAMES)
    
    def _select_grade_with_weights(self, style: str = "generic") -> str:
        """
        Select a grade/year level with appropriate weighting.
        
        This method gives higher probability to primary school years 
        and lower probability to preschool years.
        
        Args:
            style: Report style determining grade naming conventions
            
        Returns:
            Selected grade/year level
        """
        grade_options = self.GRADE_SYSTEMS.get(style.lower(), self.GRADE_SYSTEMS["generic"])
        num_options = len(grade_options)
        
        # Create weights that favor primary school years
        weights = []
        
        for i in range(num_options):
            if i == 0:  # First year (typically preschool)
                weights.append(0.05)
            elif i == 1:  # Second year (typically kindergarten/prep/foundation)
                weights.append(0.15)
            else:  # Primary school years
                # Slightly decreasing weights for older years
                weights.append(0.8 / (num_options - 2) * (1 - ((i - 2) * 0.05)))
        
        # Ensure weights sum to 1
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        # Select grade based on weights
        return random.choices(grade_options, weights=weights, k=1)[0]
    
    def _generate_birth_date(self) -> str:
        """Generate a realistic birth date based on the student's grade."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Determine age range based on grade
        grade_lower = self.grade.lower()
        age = self._determine_age_from_grade(grade_lower, self.style)
        
        # Account for variation in student ages within a grade
        # 40% of students haven't had birthday yet this year
        if random.random() < 0.4:  
            birth_year = current_year - age - 1
        else:
            birth_year = current_year - age
        
        # Generate month and day
        birth_month = random.randint(1, 12)
        
        # Ensure valid days per month
        days_in_month = 31
        if birth_month in [4, 6, 9, 11]:
            days_in_month = 30
        elif birth_month == 2:
            # Simplified leap year check
            if birth_year % 4 == 0 and (birth_year % 100 != 0 or birth_year % 400 == 0):
                days_in_month = 29
            else:
                days_in_month = 28
        
        birth_day = random.randint(1, days_in_month)
        
        # Format as YYYY-MM-DD
        return f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"
    
    def _determine_age_from_grade(self, grade_lower: str, style: str) -> int:
        """
        Determine realistic age based on grade level and state-specific naming.
        
        Args:
            grade_lower: Lowercase grade name
            style: State-specific style (act, nsw, qld, vic, sa, etc.)
            
        Returns:
            Age in years
        """
        # Handle specific state naming conventions
        if style == "nsw":
            if "preschool" in grade_lower:
                return 4
            elif "kindergarten" in grade_lower:
                return 5
            else:
                # Extract year number
                year_match = re.search(r'year\s*(\d+)', grade_lower)
                if year_match:
                    year_num = int(year_match.group(1))
                    return 5 + year_num  # Kindergarten age is 5, Year 1 is 6, etc.
                return 7  # Default primary school age
                
        elif style == "vic":
            if "three-year-old" in grade_lower:
                return 3
            elif "four-year-old" in grade_lower:
                return 4
            elif "foundation" in grade_lower:
                return 5
            else:
                # Extract year number
                year_match = re.search(r'year\s*(\d+)', grade_lower)
                if year_match:
                    year_num = int(year_match.group(1))
                    return 5 + year_num  # Foundation age is 5, Year 1 is 6, etc.
                return 7  # Default primary school age
                
        elif style == "qld":
            if "kindergarten" in grade_lower:
                return 4
            elif "prep" in grade_lower:
                return 5
            else:
                # Extract year number
                year_match = re.search(r'year\s*(\d+)', grade_lower)
                if year_match:
                    year_num = int(year_match.group(1))
                    return 5 + year_num  # Prep age is 5, Year 1 is 6, etc.
                return 7  # Default primary school age
        
        elif style == "act":
            if "preschool" in grade_lower:
                return 4
            elif "kindergarten" in grade_lower:
                return 5
            else:
                # Extract year number
                year_match = re.search(r'year\s*(\d+)', grade_lower)
                if year_match:
                    year_num = int(year_match.group(1))
                    return 5 + year_num  # Kindergarten age is 5, Year 1 is 6, etc.
                return 7  # Default primary school age
                
        # Handle other states or generic style
        else:
            if "preschool" in grade_lower or "kindergarten" in grade_lower or "pre-primary" in grade_lower or "reception" in grade_lower or "transition" in grade_lower:
                return 5  # First year of school
            elif "prep" in grade_lower or "foundation" in grade_lower:
                return 5  # First year of formal school
            else:
                # Try to extract year number
                year_match = re.search(r'year\s*(\d+)', grade_lower)
                if year_match:
                    year_num = int(year_match.group(1))
                    return 5 + year_num  # Foundation age is 5, Year 1 is 6, etc.
                return 7  # Default primary school age
    
    def _generate_class_name(self) -> str:
        """Generate an appropriate class name based on the student's grade."""
        grade_lower = self.grade.lower()
        
        if "kindergarten" in grade_lower or "prep" in grade_lower or "foundation" in grade_lower or "reception" in grade_lower or "pre-primary" in grade_lower or "transition" in grade_lower or "three-year-old" in grade_lower or "four-year-old" in grade_lower:
            naming_system = random.choice(["kindergarten", "standard", "early_learning"])
        else:
            naming_system = random.choice(["standard", "colors", "nature", "language"])
            
        # For standard naming, incorporate year level in class name
        if naming_system == "standard" and "year" in grade_lower:
            try:
                year_num = grade_lower.split("year")[1].strip()
                # Get initial of random teacher last name
                teacher_initial = random.choice(self.TEACHER_LAST_NAMES)[0]
                # Create class code like "2M" for Year 2, teacher with last name starting with M
                return f"{year_num}{teacher_initial}"
            except:
                pass
                
        return random.choice(self.CLASS_NAMES[naming_system])
    
    def _generate_teacher(self) -> Dict[str, str]:
        """Generate teacher information."""
        title = random.choice(self.TEACHER_TITLES)
        last_name = random.choice(self.TEACHER_LAST_NAMES)
        
        # Sometimes include first initial or first name
        if random.random() < 0.3:
            if random.random() < 0.5:
                # First initial only
                first_initial = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                full_name = f"{title} {first_initial}. {last_name}"
            else:
                # Full first name
                if title == "Mr.":
                    first_name = random.choice(self.FIRST_NAMES_MALE)
                elif title == "Mrs." or title == "Ms.":
                    first_name = random.choice(self.FIRST_NAMES_FEMALE)
                else:  # Dr.
                    first_name = random.choice(self.FIRST_NAMES_MALE + self.FIRST_NAMES_FEMALE)
                
                full_name = f"{title} {first_name} {last_name}"
        else:
            full_name = f"{title} {last_name}"
        
        return {
            "title": title,
            "last_name": last_name,
            "full_name": full_name
        }
    
    def _generate_guardians(self) -> List[Dict[str, str]]:
        """Generate information about parents/guardians."""
        # Determine number of guardians to generate
        guardian_type_chance = random.random()
        if guardian_type_chance < 0.7:  # 70% chance of two guardians
            num_guardians = 2
        elif guardian_type_chance < 0.9:  # 20% chance of single guardian
            num_guardians = 1
        else:  # 10% chance of alternative guardian structure
            num_guardians = random.choice([1, 3])  # Single or three (e.g., blended family, grandparent)
        
        guardians = []
        last_names_used = set([self.last_name])
        
        # Handle single guardian scenario with higher chance of female guardian
        if num_guardians == 1:
            gender = "female" if random.random() < 0.7 else "male"
            relationship = self._get_guardian_relationship(gender, 0, num_guardians)
            guardians.append(self._create_guardian(gender, relationship, self.last_name))
            return guardians
        
        # Handle two or more guardians
        for i in range(num_guardians):
            # For first two guardians in traditional family structure (70% chance)
            if i < 2 and random.random() < 0.7:
                if i == 0:
                    gender = random.choice(["male", "female"])
                else:
                    # Usually opposite gender for second guardian
                    gender = "female" if guardians[0]["gender"] == "male" else "male"
                
                relationship = self._get_guardian_relationship(gender, i, num_guardians)
                
                # Determine last name - 80% chance same last name as student
                if random.random() < 0.8:
                    last_name = self.last_name
                else:
                    # Generate different last name
                    last_name = self._generate_unique_last_name(last_names_used)
                    last_names_used.add(last_name)
                
                guardians.append(self._create_guardian(gender, relationship, last_name))
            
            # Non-traditional family structures
            else:
                # Generate diverse guardian scenarios
                gender = random.choice(["male", "female"])
                relationship = self._get_guardian_relationship(gender, i, num_guardians)
                
                # Higher chance of different last name for additional guardians
                if random.random() < 0.6:
                    last_name = self._generate_unique_last_name(last_names_used)
                    last_names_used.add(last_name)
                else:
                    last_name = self.last_name
                
                guardians.append(self._create_guardian(gender, relationship, last_name))
        
        return guardians
    
    def _get_guardian_relationship(self, gender: str, index: int, total_guardians: int) -> str:
        """Determine the appropriate guardian relationship."""
        # Standard parent relationships
        if index < 2 and total_guardians <= 2:
            if gender == "male":
                return "Father"
            else:
                return "Mother"
        
        # Additional or alternative guardians
        relationship_options = []
        
        if gender == "male":
            relationship_options = ["Stepfather", "Grandfather", "Uncle", "Legal Guardian"]
        else:
            relationship_options = ["Stepmother", "Grandmother", "Aunt", "Legal Guardian"]
        
        return random.choice(relationship_options)
    
    def _generate_unique_last_name(self, used_names: set) -> str:
        """Generate a last name that hasn't been used yet."""
        # Pool all last name options
        all_last_names = self.LAST_NAMES + self.ASIAN_LAST_NAMES + self.MENA_LAST_NAMES + self.PACIFIC_LAST_NAMES
        
        # Filter out already used names
        available_names = [name for name in all_last_names if name not in used_names]
        
        if available_names:
            return random.choice(available_names)
        else:
            # If all names are somehow used, just return a random one
            return random.choice(all_last_names)
    
    def _create_guardian(self, gender: str, relationship: str, last_name: str) -> Dict[str, str]:
        """Create a guardian with the specified attributes."""
        # Generate first name based on gender
        if gender == "male":
            # Use cultural appropriateness for first name based on last name
            if last_name in self.ASIAN_LAST_NAMES:
                first_name = random.choice(self.ASIAN_FIRST_NAMES)
            elif last_name in self.MENA_LAST_NAMES:
                first_name = random.choice(self.MENA_FIRST_NAMES)
            elif last_name in self.PACIFIC_LAST_NAMES:
                first_name = random.choice(self.PACIFIC_FIRST_NAMES)
            else:
                first_name = random.choice(self.FIRST_NAMES_MALE)
        else:
            # Use cultural appropriateness for first name based on last name
            if last_name in self.ASIAN_LAST_NAMES:
                first_name = random.choice(self.ASIAN_FIRST_NAMES)
            elif last_name in self.MENA_LAST_NAMES:
                first_name = random.choice(self.MENA_FIRST_NAMES)
            elif last_name in self.PACIFIC_LAST_NAMES:
                first_name = random.choice(self.PACIFIC_FIRST_NAMES)
            else:
                first_name = random.choice(self.FIRST_NAMES_FEMALE)
        
        return {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "gender": gender,
            "relationship": relationship
        }
    
    def _generate_attendance(self) -> Dict[str, int]:
        """Generate realistic attendance data."""
        # Base on typical school term of around 10 weeks (50 days)
        total_days = random.randint(45, 55)
        
        # Most students have good attendance
        if random.random() < 0.7:  # 70% have good attendance
            absent_days = random.randint(0, 5)
            late_days = random.randint(0, 3)
        elif random.random() < 0.9:  # 20% have moderate attendance issues
            absent_days = random.randint(5, 10)
            late_days = random.randint(2, 6)
        else:  # 10% have significant attendance issues
            absent_days = random.randint(10, 20)
            late_days = random.randint(4, 10)
        
        present_days = total_days - absent_days
        
        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "attendance_rate": round(present_days / total_days * 100, 1)
        }
    
    def _generate_learning_profile(self) -> Dict[str, Any]:
        """Generate a learning profile for the student."""
        # Select 2-3 learning strengths
        num_strengths = random.randint(2, 3)
        strengths = random.sample(self.LEARNING_STRENGTHS, num_strengths)
        
        # Select 1-2 learning challenges
        num_challenges = random.randint(1, 2)
        challenges = random.sample(self.LEARNING_CHALLENGES, num_challenges)
        
        # Select 2-3 interests
        num_interests = random.randint(2, 3)
        interests = random.sample(self.INTERESTS, num_interests)
        
        # Select 2-3 social strengths
        num_social = random.randint(2, 3)
        social_strengths = random.sample(self.SOCIAL_STRENGTHS, num_social)
        
        # Generate learning goals
        learning_goals = self._generate_learning_goals(strengths, challenges)
        
        return {
            "strengths": strengths,
            "challenges": challenges,
            "interests": interests,
            "social_strengths": social_strengths,
            "learning_goals": learning_goals
        }
    
    def _generate_learning_goals(self, strengths: List[str], challenges: List[str]) -> List[str]:
        """Generate personalized learning goals based on strengths and challenges."""
        goals = []
        
        # Goal based on challenge
        if challenges:
            challenge = random.choice(challenges)
            if "focused" in challenge:
                goals.append("Develop strategies to maintain focus during independent work")
            elif "organizing" in challenge:
                goals.append("Improve organization of work materials and assignments")
            elif "time" in challenge:
                goals.append("Develop better time management skills")
            elif "writing" in challenge:
                goals.append("Strengthen written expression skills")
            elif "participating" in challenge:
                goals.append("Increase participation in class discussions")
            elif "mathematical" in challenge:
                goals.append("Build confidence in mathematical problem-solving")
            elif "reading" in challenge:
                goals.append("Improve reading comprehension strategies")
            elif "spelling" in challenge:
                goals.append("Develop consistent spelling accuracy")
            elif "sitting" in challenge:
                goals.append("Practice maintaining appropriate learning posture")
            elif "asking" in challenge:
                goals.append("Develop confidence in seeking assistance when needed")
            else:
                goals.append(f"Work on strategies to address challenges with {challenge}")
        
        # Goal based on strength
        if strengths:
            strength = random.choice(strengths)
            if "visual" in strength:
                goals.append("Further develop visual learning strategies")
            elif "auditory" in strength:
                goals.append("Continue to build on strong listening skills")
            elif "hands-on" in strength:
                goals.append("Apply practical skills to more complex projects")
            elif "reading" in strength:
                goals.append("Expand reading comprehension through more challenging texts")
            elif "writing" in strength:
                goals.append("Develop more sophisticated writing techniques")
            elif "group" in strength:
                goals.append("Take on leadership roles in collaborative activities")
            elif "independent" in strength:
                goals.append("Extend independent research skills")
            elif "creative" in strength:
                goals.append("Apply creative thinking across the curriculum")
            elif "problem-solving" in strength:
                goals.append("Tackle more complex problem-solving challenges")
            elif "mathematical" in strength:
                goals.append("Explore advanced mathematical concepts")
            else:
                goals.append(f"Build on existing strength in {strength}")
        
        # Add a generic academic goal if we don't have enough
        if len(goals) < 2:
            generic_goals = [
                "Develop greater confidence when presenting to the class",
                "Practice applying learning across different subject areas",
                "Take more initiative in classroom activities",
                "Regularly reflect on personal learning progress",
                "Develop stronger self-editing skills",
                "Apply feedback consistently to improve work"
            ]
            goals.append(random.choice(generic_goals))
        
        return goals
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert student profile to dictionary."""
        return {
            "name": {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "full_name": f"{self.first_name} {self.last_name}"
            },
            "gender": self.gender,
            "grade": self.grade,
            "class": self.class_name,
            "teacher": self.teacher,
            "guardians": self.guardians,
            "attendance": self.attendance,
            "birth_date": self.birth_date,
            "learning_profile": self.learning_profile
        }


class SchoolProfile:
    """Class representing an Australian school profile."""
    
    # Australian school types
    SCHOOL_TYPES = [
        "Primary School",
        "Public School",
        "Primary College",
        "Grammar School",
        "Catholic Primary School",
        "Elementary School",
        "Christian College",
        "State School",
        "Public Primary School",
        "Early Learning Centre",
        "Community School",
        "Primary Academy",
        "Anglican School",
        "Independent School",
        "Montessori School",
        "Steiner School"
    ]
    
    # Australian suburbs by state
    SUBURBS = {
        "act": ["Lyons", "Belconnen", "Gungahlin", "Woden", "Tuggeranong", "Dickson", "Braddon", "Barton", "Kingston", "Ainslie", "Narrabundah", "Yarralumla", "Calwell", "Kaleen"],
        "nsw": ["Parramatta", "Newcastle", "Cronulla", "Bondi", "Manly", "Blacktown", "Penrith", "Liverpool", "Campbelltown", "Wollongong", "Gosford", "Hornsby", "Katoomba", "Byron Bay", "Tamworth", "Dubbo"],
        "qld": ["Brisbane", "Gold Coast", "Sunshine Coast", "Toowoomba", "Townsville", "Cairns", "Rockhampton", "Mackay", "Bundaberg", "Ipswich", "Hervey Bay", "Gladstone", "Maryborough", "Mount Isa"],
        "vic": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Wodonga", "Shepparton", "Mildura", "Warrnambool", "Bairnsdale", "Sale", "Traralgon", "Horsham", "Echuca", "Wangaratta"],
        "sa": ["Adelaide", "Mount Gambier", "Whyalla", "Port Lincoln", "Port Augusta", "Victor Harbor", "Murray Bridge", "Port Pirie", "Renmark", "Gawler", "Nuriootpa", "Kadina", "Loxton"],
        "wa": ["Perth", "Fremantle", "Mandurah", "Bunbury", "Geraldton", "Albany", "Kalgoorlie", "Broome", "Port Hedland", "Esperance", "Karratha", "Busselton", "Kununurra", "Collie"],
        "tas": ["Hobart", "Launceston", "Devonport", "Burnie", "Kingston", "Ulverstone", "Wynyard", "New Norfolk", "Sorell", "George Town", "Smithton", "Deloraine", "St Helens"],
        "nt": ["Darwin", "Alice Springs", "Katherine", "Nhulunbuy", "Tennant Creek", "Palmerston", "Jabiru", "Yulara", "Alyangula", "Wadeye", "Humpty Doo", "Gunbalanya"]
    }
    
    # School values
    SCHOOL_VALUES = [
        "Respect", "Responsibility", "Excellence", "Integrity", "Compassion", 
        "Diversity", "Inclusion", "Resilience", "Perseverance", "Innovation", 
        "Collaboration", "Community", "Courage", "Honesty", "Kindness", 
        "Growth", "Achievement", "Creativity", "Leadership", "Sustainability"
    ]
    
    # School mottos
    SCHOOL_MOTTOS = [
        "Learning for Life",
        "Strive for Excellence",
        "Growing Together",
        "Believe, Achieve, Succeed",
        "Together We Learn",
        "Knowledge is Power",
        "Building Futures",
        "Creating Tomorrow's Leaders",
        "Aiming High",
        "Empowering Minds",
        "Learning Today, Leading Tomorrow",
        "Excellence Through Effort",
        "Where Every Child Matters",
        "Nurturing Young Minds",
        "Respect, Responsibility, Results",
        "Inspiring Bright Futures",
        "Character, Knowledge, Wisdom",
        "Always Our Best"
    ]
    
    def __init__(
        self,
        name: Optional[str] = None,
        type_name: Optional[str] = None,
        state: Optional[str] = None,
        suburb: Optional[str] = None,
        principal: Optional[str] = None,
        established: Optional[int] = None,
        school_values: Optional[List[str]] = None,
        motto: Optional[str] = None
    ):
        """
        Initialize a school profile with either provided or randomly generated attributes.
        
        Args:
            name: Optional school name
            type_name: Optional school type
            state: Optional state code (act, nsw, qld, vic, sa, wa, tas, nt)
            suburb: Optional suburb name
            principal: Optional principal name
            established: Optional year the school was established
            school_values: Optional list of school values
            motto: Optional school motto
        """
        # Set state first as other values may depend on it
        self.state = state.lower() if state else random.choice(list(self.SUBURBS.keys()))
        
        # Set suburb
        self.suburb = suburb
        if not self.suburb:
            self.suburb = random.choice(self.SUBURBS.get(self.state, self.SUBURBS["act"]))
        
        # Set school type
        self.type_name = type_name if type_name else random.choice(self.SCHOOL_TYPES)
        
        # Set school name
        if name:
            self.name = name
        else:
            # Occasionally use other naming patterns
            if random.random() < 0.2:
                # Saint names for Catholic/religious schools
                if "Catholic" in self.type_name or "Christian" in self.type_name or "Anglican" in self.type_name:
                    saints = ["St Mary's", "St Joseph's", "St Patrick's", "St John's", "St Michael's", 
                              "St Catherine's", "St Paul's", "St Peter's", "St Anthony's", "St Thomas'"]
                    self.name = f"{random.choice(saints)} {self.type_name}"
                else:
                    self.name = f"{self.suburb} {self.type_name}"
            else:
                self.name = f"{self.suburb} {self.type_name}"
        
        # Set principal
        self.principal = principal if principal else random.choice(StudentProfile.PRINCIPAL_NAMES)
        
        # Set year established
        if established:
            self.established = established
        else:
            # Most schools established between 1950 and 2010
            current_year = datetime.now().year
            weights = [0.05, 0.10, 0.20, 0.30, 0.25, 0.10]  # Weights for different time periods
            periods = [
                (1880, 1920),  # Very old schools
                (1920, 1950),  # Older schools
                (1950, 1980),  # Post-war expansion
                (1980, 2000),  # Modern schools
                (2000, 2015),  # Recent schools
                (2015, current_year - 2)  # Very new schools
            ]
            
            # Select a time period based on weights
            period_index = random.choices(range(len(periods)), weights=weights, k=1)[0]
            period = periods[period_index]
            
            self.established = random.randint(period[0], period[1])
        
        # Set school values
        if school_values:
            self.school_values = school_values
        else:
            # Select 3-5 random values
            num_values = random.randint(3, 5)
            self.school_values = random.sample(self.SCHOOL_VALUES, num_values)
        
        # Set motto
        self.motto = motto if motto else random.choice(self.SCHOOL_MOTTOS)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert school profile to dictionary."""
        return {
            "name": self.name,
            "type": self.type_name,
            "state": self.state,
            "suburb": self.suburb,
            "principal": self.principal,
            "established": self.established,
            "values": self.school_values,
            "motto": self.motto
        }


class StudentDataGenerator:
    """Generate realistic student data and reports."""
    
    def __init__(self, style: str = "generic"):
        """
        Initialize the Student Data Generator.
        
        Args:
            style: The report style to use (act, nsw, etc.)
        """
        self.style = style.lower()
    
    def generate_student_profile(self, **kwargs) -> StudentProfile:
        """Generate a student profile with optional specific attributes."""
        return StudentProfile(style=self.style, **kwargs)
    
    def generate_school_profile(self, **kwargs) -> SchoolProfile:
        """Generate a school profile with optional specific attributes."""
        return SchoolProfile(**kwargs)
    
    def generate_classroom(self, class_size: int = 25, grade: Optional[str] = None, teacher: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate a complete classroom of students.
        
        Args:
            class_size: Number of students in the class
            grade: Grade/year level for all students
            teacher: Optional teacher information
            
        Returns:
            Dictionary with classroom information
        """
        # Generate or use provided teacher
        if not teacher:
            teacher = StudentProfile._generate_teacher(self)
            
        # Determine grade if not provided
        if not grade:
            grade_options = StudentProfile.GRADE_SYSTEMS.get(self.style, StudentProfile.GRADE_SYSTEMS["generic"])
            grade = random.choice(grade_options)
        
        # Generate class name based on grade
        class_name = self._generate_class_name_for_grade(grade, teacher["last_name"])
        
        # Generate students
        students = []
        for _ in range(class_size):
            student = self.generate_student_profile(
                grade=grade,
                class_name=class_name
            )
            students.append(student.to_dict())
        
        # Create classroom dictionary
        classroom = {
            "teacher": teacher,
            "grade": grade,
            "class_name": class_name,
            "size": class_size,
            "students": students
        }
        
        return classroom
    
    def _generate_class_name_for_grade(self, grade: str, teacher_last_name: str) -> str:
        """Generate an appropriate class name for a given grade."""
        grade_lower = grade.lower()
        
        if "kindergarten" in grade_lower or "prep" in grade_lower or "foundation" in grade_lower or "reception" in grade_lower or "pre-primary" in grade_lower or "transition" in grade_lower or "three-year-old" in grade_lower or "four-year-old" in grade_lower:
            naming_system = random.choice(["kindergarten", "standard", "early_learning"])
        else:
            naming_system = random.choice(["standard", "colors", "nature", "language"])
            
        # For standard naming, incorporate year level in class name
        if naming_system == "standard" and "year" in grade_lower:
            try:
                year_num = grade_lower.split("year")[1].strip()
                # Use first letter of teacher's last name
                teacher_initial = teacher_last_name[0]
                # Create class code like "2M" for Year 2, teacher with last name starting with M
                return f"{year_num}{teacher_initial}"
            except:
                pass
                
        return random.choice(StudentProfile.CLASS_NAMES[naming_system])