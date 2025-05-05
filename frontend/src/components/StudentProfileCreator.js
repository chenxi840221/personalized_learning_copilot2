// frontend/src/components/StudentProfileCreator.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../services/api';

/**
 * StudentProfileCreator - Component for manually creating student profiles
 * Allows teachers to create new student profiles by providing manual information
 * or by utilizing suggestions from existing student reports.
 */
const StudentProfileCreator = ({ onProfileCreated }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [availableReports, setAvailableReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState('');
  const [fetchingReportData, setFetchingReportData] = useState(false);
  
  const [profileData, setProfileData] = useState({
    full_name: '',
    gender: '',
    grade_level: '',
    learning_style: '',
    strengths: [],
    interests: [],
    areas_for_improvement: [],
    school_name: '',
    teacher_name: '',
    current_school_year: new Date().getFullYear().toString(),
    current_term: 'S1'
  });
  
  // Fetch student reports on component mount
  useEffect(() => {
    const fetchStudentReports = async () => {
      try {
        const response = await apiClient.get('/student-reports');
        if (response.data && response.data.length > 0) {
          setAvailableReports(response.data);
        }
      } catch (err) {
        console.error('Error fetching student reports:', err);
      }
    };
    
    fetchStudentReports();
  }, []);
  
  // Handle form field changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Handle array fields (strengths, interests, areas_for_improvement)
  const handleArrayFieldChange = (field, value) => {
    // Split the text input by commas into an array
    const items = value.split(',').map(item => item.trim()).filter(item => item);
    
    setProfileData(prev => ({
      ...prev,
      [field]: items
    }));
  };
  
  // Handle report selection to populate suggested data
  const handleReportSelection = async (e) => {
    const reportId = e.target.value;
    setSelectedReportId(reportId);
    
    if (!reportId) return;
    
    setFetchingReportData(true);
    setError('');
    
    try {
      // Call the debug endpoint to extract profile from the selected report
      const response = await apiClient.post(`/debug/extract-profile/${reportId}`);
      
      if (response.data && response.data.profile_data) {
        const profileData = response.data.profile_data;
        
        // Update form with extracted data
        setProfileData({
          full_name: profileData.full_name || '',
          gender: profileData.gender || '',
          grade_level: profileData.grade_level || '',
          learning_style: profileData.learning_style || '',
          strengths: profileData.strengths || [],
          interests: profileData.interests || [],
          areas_for_improvement: profileData.areas_for_improvement || [],
          school_name: profileData.school_name || '',
          teacher_name: profileData.teacher_name || '',
          current_school_year: profileData.current_school_year || new Date().getFullYear().toString(),
          current_term: profileData.current_term || 'S1'
        });
        
        setSuccess('Profile information extracted successfully');
      } else {
        setError('Failed to extract profile data from report');
      }
    } catch (err) {
      console.error('Error extracting profile from report:', err);
      setError('Error extracting profile from report');
    } finally {
      setFetchingReportData(false);
    }
  };
  
  // Handle form submission to create profile
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      // Use the direct indexing endpoint to create the profile
      const response = await apiClient.post('/direct-index/profile', profileData);
      
      if (response.data && response.data.status === 'success') {
        setSuccess('Student profile created successfully!');
        
        // Clear the form or reset to defaults
        setProfileData({
          full_name: '',
          gender: '',
          grade_level: '',
          learning_style: '',
          strengths: [],
          interests: [],
          areas_for_improvement: [],
          school_name: '',
          teacher_name: '',
          current_school_year: new Date().getFullYear().toString(),
          current_term: 'S1'
        });
        
        // Notify parent component if needed
        if (onProfileCreated) {
          onProfileCreated(response.data);
        }
      } else {
        setError('Failed to create student profile');
      }
    } catch (err) {
      console.error('Error creating student profile:', err);
      setError('Error creating student profile: ' + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-semibold mb-4">Create Student Profile</h2>
      
      {/* Report Selector */}
      {availableReports.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Get Suggestions from Report
          </label>
          <div className="flex space-x-2">
            <select
              value={selectedReportId}
              onChange={handleReportSelection}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              disabled={fetchingReportData}
            >
              <option value="">Select a report...</option>
              {availableReports.map(report => (
                <option key={report.id} value={report.id}>
                  {report.student_name || 'Unknown Student'} - {report.school_name || 'Unknown School'} ({report.created_at ? new Date(report.created_at).toLocaleDateString() : 'Unknown Date'})
                </option>
              ))}
            </select>
            {fetchingReportData && (
              <div className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Select a student report to auto-fill profile information
          </p>
        </div>
      )}
      
      {/* Profile Form */}
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {/* Basic Information */}
          <div className="col-span-2">
            <h3 className="text-md font-medium text-gray-700 mb-3">Basic Information</h3>
          </div>
          
          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
              Full Name*
            </label>
            <input
              type="text"
              name="full_name"
              id="full_name"
              required
              value={profileData.full_name}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          
          <div>
            <label htmlFor="gender" className="block text-sm font-medium text-gray-700 mb-1">
              Gender
            </label>
            <select
              name="gender"
              id="gender"
              value={profileData.gender}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="">Select gender...</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </div>
          
          <div>
            <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
              Grade Level
            </label>
            <select
              name="grade_level"
              id="grade_level"
              value={profileData.grade_level}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="">Select grade level...</option>
              {[...Array(12)].map((_, i) => (
                <option key={i+1} value={i+1}>{i+1}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label htmlFor="learning_style" className="block text-sm font-medium text-gray-700 mb-1">
              Learning Style
            </label>
            <select
              name="learning_style"
              id="learning_style"
              value={profileData.learning_style}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="">Select learning style...</option>
              <option value="Visual">Visual</option>
              <option value="Auditory">Auditory</option>
              <option value="Kinesthetic">Kinesthetic</option>
              <option value="Reading/Writing">Reading/Writing</option>
              <option value="Multimodal">Multimodal</option>
            </select>
          </div>
          
          <div className="col-span-2">
            <label htmlFor="school_name" className="block text-sm font-medium text-gray-700 mb-1">
              School Name
            </label>
            <input
              type="text"
              name="school_name"
              id="school_name"
              value={profileData.school_name}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          
          <div>
            <label htmlFor="teacher_name" className="block text-sm font-medium text-gray-700 mb-1">
              Teacher Name
            </label>
            <input
              type="text"
              name="teacher_name"
              id="teacher_name"
              value={profileData.teacher_name}
              onChange={handleChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="current_school_year" className="block text-sm font-medium text-gray-700 mb-1">
                School Year
              </label>
              <input
                type="text"
                name="current_school_year"
                id="current_school_year"
                value={profileData.current_school_year}
                onChange={handleChange}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
            </div>
            
            <div>
              <label htmlFor="current_term" className="block text-sm font-medium text-gray-700 mb-1">
                Term
              </label>
              <select
                name="current_term"
                id="current_term"
                value={profileData.current_term}
                onChange={handleChange}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="S1">Semester 1</option>
                <option value="S2">Semester 2</option>
                <option value="T1">Term 1</option>
                <option value="T2">Term 2</option>
                <option value="T3">Term 3</option>
                <option value="T4">Term 4</option>
              </select>
            </div>
          </div>
          
          {/* Student Characteristics */}
          <div className="col-span-2 mt-4">
            <h3 className="text-md font-medium text-gray-700 mb-3">Student Characteristics</h3>
          </div>
          
          <div className="col-span-2">
            <label htmlFor="strengths" className="block text-sm font-medium text-gray-700 mb-1">
              Strengths (comma separated)
            </label>
            <textarea
              id="strengths"
              rows="3"
              value={profileData.strengths.join(', ')}
              onChange={(e) => handleArrayFieldChange('strengths', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Math, Critical thinking, Problem solving"
            ></textarea>
          </div>
          
          <div className="col-span-2">
            <label htmlFor="interests" className="block text-sm font-medium text-gray-700 mb-1">
              Interests (comma separated)
            </label>
            <textarea
              id="interests"
              rows="3"
              value={profileData.interests.join(', ')}
              onChange={(e) => handleArrayFieldChange('interests', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Science, Art, Music"
            ></textarea>
          </div>
          
          <div className="col-span-2">
            <label htmlFor="areas_for_improvement" className="block text-sm font-medium text-gray-700 mb-1">
              Areas for Improvement (comma separated)
            </label>
            <textarea
              id="areas_for_improvement"
              rows="3"
              value={profileData.areas_for_improvement.join(', ')}
              onChange={(e) => handleArrayFieldChange('areas_for_improvement', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Organization, Time management, Writing"
            ></textarea>
          </div>
        </div>
        
        {/* Submit button */}
        <div className="mt-6">
          <button
            type="submit"
            disabled={loading || !profileData.full_name}
            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Student Profile'}
          </button>
        </div>
        
        {/* Error and success messages */}
        {error && (
          <div className="mt-3 text-sm text-red-600">{error}</div>
        )}
        {success && (
          <div className="mt-3 text-sm text-green-600">{success}</div>
        )}
      </form>
    </div>
  );
};

export default StudentProfileCreator;