"""
Template generator module for project setup.

This module provides the TemplateGenerator class for generating HTML
template content for different report styles.
"""


class TemplateGenerator:
    """Generator for HTML templates used in reports."""
    
    def get_act_template_content(self) -> str:
        """Get content for ACT template."""
        return '''<!DOCTYPE html>
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
        .logo {
            max-height: 80px;
            margin-bottom: 15px;
        }
        .school-logo {
            max-height: 100px;
            margin-bottom: 10px;
        }
        .student-photo {
            max-width: 120px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 3px;
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
            <div class="row">
                <div class="col-md-3 text-start">
                    <img src="{{ get_image_base64('images/logos/act_education_logo.png') }}" alt="ACT Education" class="logo">
                </div>
                <div class="col-md-6 text-center">
                    {% if data.school.logo_data %}
                    <img src="{{ data.school.logo_data }}" alt="{{ data.school.name }}" class="school-logo">
                    {% endif %}
                    <div class="school-name">{{ data.school.name }}</div>
                    <div class="report-title">Student Progress Report</div>
                    <div>Semester {{ data.semester }} {{ data.year }}</div>
                </div>
                <div class="col-md-3 text-end">
                    {% if data.student.photo_data %}
                    <img src="{{ data.student.photo_data }}" alt="{{ data.student.name.full_name }}" class="student-photo">
                    {% endif %}
                </div>
            </div>
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
'''
    
    def get_nsw_template_content(self) -> str:
        """Get content for NSW template."""
        return '''<!DOCTYPE html>
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
        .logo {
            max-height: 80px;
            margin-bottom: 15px;
        }
        .school-logo {
            max-height: 100px;
            margin-bottom: 10px;
        }
        .student-photo {
            max-width: 120px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 3px;
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
            <div class="row">
                <div class="col-md-3 text-start">
                    <img src="{{ get_image_base64('images/logos/nsw_government_logo.png') }}" alt="NSW Government" class="logo">
                </div>
                <div class="col-md-6 text-center">
                    {% if data.school.logo_data %}
                    <img src="{{ data.school.logo_data }}" alt="{{ data.school.name }}" class="school-logo">
                    {% endif %}
                    <div class="school-name">{{ data.school.name }}</div>
                    <div class="report-title">Student Achievement Report</div>
                    <div>Semester {{ data.semester }} {{ data.year }}</div>
                </div>
                <div class="col-md-3 text-end">
                    {% if data.student.photo_data %}
                    <img src="{{ data.student.photo_data }}" alt="{{ data.student.name.full_name }}" class="student-photo">
                    {% endif %}
                </div>
            </div>
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
'''
    
    def get_placeholder_template(self, style_name: str) -> str:
        """
        Get a placeholder HTML template for a specific style.
        
        Args:
            style_name: Name of the style (e.g., ACT, NSW)
            
        Returns:
            Placeholder HTML template content
        """
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ data.student.name.full_name }}}} - {style_name} School Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .school-name {{ font-size: 1.8rem; font-weight: bold; color: #003366; }}
        .report-title {{ font-size: 1.4rem; margin-bottom: 1rem; }}
        .student-info {{ margin-bottom: 2rem; }}
        .subject-table th {{ background-color: #e6f2ff; }}
        .comment {{ font-size: 0.9rem; }}
        .general-comment {{ margin: 2rem 0; padding: 1rem; background-color: #f8f9fa; border-radius: 5px; }}
        .signatures {{ margin-top: 3rem; display: flex; justify-content: space-around; }}
        .signature-box {{ text-align: center; width: 40%; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 2rem; padding-top: 0.5rem; }}
    </style>
</head>
<body>
    <div class="container mt-4 mb-4">
        <div class="header">
            <div class="school-name">{{{{ data.school.name }}}}</div>
            <div class="report-title">Student Progress Report - Semester {{{{ data.semester }}}} {{{{ data.year }}}}</div>
        </div>
        
        <div class="student-info">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Student:</strong> {{{{ data.student.name.full_name }}}}</p>
                    <p><strong>Grade:</strong> {{{{ data.student.grade }}}}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Class:</strong> {{{{ data.student.class }}}}</p>
                    <p><strong>Teacher:</strong> {{{{ data.student.teacher.full_name }}}}</p>
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
                {{{{% for subject in data.subjects %}}}}
                <tr>
                    <td>{{{{ subject.subject }}}}</td>
                    <td class="text-center">
                        {{{{ subject.achievement.label }}}}
                    </td>
                    <td class="text-center">
                        {{{{ subject.effort.label }}}}
                    </td>
                    <td class="comment">{{{{ subject.comment }}}}</td>
                </tr>
                {{{{% endfor %}}}}
            </tbody>
        </table>
        
        <h4>General Comment</h4>
        <div class="general-comment">
            {{{{ data.general_comment }}}}
        </div>
        
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">{{{{ data.student.teacher.full_name }}}}</div>
                <div>Teacher</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{{{ data.school.principal }}}}</div>
                <div>Principal</div>
            </div>
        </div>
    </div>
</body>
</html>
'''