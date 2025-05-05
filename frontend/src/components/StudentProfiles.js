// frontend/src/components/StudentProfiles.js
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useEntraAuth } from '../hooks/useEntraAuth';
import { getStudentProfiles, getStudentProfile, getStudentProfileHistory, deleteStudentProfile } from '../services/api';
import StudentProfileCreator from './StudentProfileCreator';

const StudentProfiles = () => {
  const { user } = useAuth();
  const { getAccessToken, isAuthenticated } = useEntraAuth();
  
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [profileHistory, setProfileHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [viewMode, setViewMode] = useState('list'); // 'list', 'detail', 'history', 'create'
  const [filters, setFilters] = useState({
    nameFilter: '',
    schoolYear: '',
    term: ''
  });
  
  // School years and terms data
  const schoolYearOptions = ['2023', '2024', '2025'];
  const termOptions = ['S1', 'S2', 'T1', 'T2', 'T3', 'T4'];
  
  // Fetch profiles on component mount
  useEffect(() => {
    if (user) {
      fetchProfiles();
    }
  }, [user]);
  
  // Fetch student profiles
  const fetchProfiles = async (filterParams = {}) => {
    setLoading(true);
    setError('');
    
    try {
      const params = {
        ...filterParams
      };
      
      if (filters.nameFilter) {
        params.name_filter = filters.nameFilter;
      }
      
      if (filters.schoolYear) {
        params.school_year = filters.schoolYear;
      }
      
      if (filters.term) {
        params.term = filters.term;
      }
      
      const data = await getStudentProfiles(params);
      setProfiles(data || []);
    } catch (err) {
      setError('Failed to fetch student profiles. Please try again.');
      console.error('Error fetching profiles:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle profile view
  const handleViewProfile = async (profileId) => {
    setLoading(true);
    setError('');
    
    try {
      const params = {};
      
      if (filters.schoolYear) {
        params.school_year = filters.schoolYear;
      }
      
      if (filters.term) {
        params.term = filters.term;
      }
      
      const data = await getStudentProfile(profileId, params);
      setSelectedProfile(data);
      setViewMode('detail');
    } catch (err) {
      setError('Failed to fetch profile details. Please try again.');
      console.error('Error fetching profile:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle view profile history
  const handleViewHistory = async (profileId) => {
    setLoading(true);
    setError('');
    
    try {
      const data = await getStudentProfileHistory(profileId);
      setProfileHistory(data);
      setViewMode('history');
    } catch (err) {
      setError('Failed to fetch profile history. Please try again.');
      console.error('Error fetching profile history:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle delete profile
  const handleDeleteProfile = async (profileId) => {
    if (!window.confirm('Are you sure you want to delete this student profile?')) return;
    
    setLoading(true);
    
    try {
      await deleteStudentProfile(profileId);
      
      // Remove profile from list
      setProfiles(profiles.filter(profile => profile.id !== profileId));
      
      // Reset selected profile if deleted
      if (selectedProfile && selectedProfile.id === profileId) {
        setSelectedProfile(null);
        setViewMode('list');
      }
      
      setSuccessMessage('Student profile deleted successfully.');
    } catch (err) {
      setError('Failed to delete profile. Please try again.');
      console.error('Error deleting profile:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle filter changes
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Apply filters
  const applyFilters = (e) => {
    e.preventDefault();
    fetchProfiles();
  };
  
  // Reset filters
  const resetFilters = () => {
    setFilters({
      nameFilter: '',
      schoolYear: '',
      term: ''
    });
    fetchProfiles({});
  };
  
  // Back to list view
  const backToList = () => {
    setSelectedProfile(null);
    setProfileHistory(null);
    setViewMode('list');
  };
  
  // Handle profile creation
  const handleCreateProfile = () => {
    setViewMode('create');
  };
  
  // Handle profile created event
  const handleProfileCreated = (profileData) => {
    setSuccessMessage('Student profile created successfully!');
    // Refresh the profiles list
    fetchProfiles();
    // Return to list view after short delay
    setTimeout(() => {
      setViewMode('list');
    }, 1000);
  };
  
  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };
  
  // Render profile creation view
  const renderProfileCreation = () => {
    return (
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium">Create New Student Profile</h3>
          <button
            onClick={backToList}
            className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to List
          </button>
        </div>
        <StudentProfileCreator onProfileCreated={handleProfileCreated} />
      </div>
    );
  };
  
  // Render profile list view
  const renderProfileList = () => {
    return (
      <div>
        {/* Action Buttons */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={handleCreateProfile}
            className="inline-flex items-center px-4 py-2 bg-green-600 text-white border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Create Student Profile
          </button>
        </div>
        
        {/* Filters */}
        <div className="mb-6 bg-white rounded-lg shadow-md p-4">
          <h3 className="text-lg font-medium mb-3">Filter Profiles</h3>
          <form onSubmit={applyFilters} className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Student Name
                </label>
                <input
                  type="text"
                  name="nameFilter"
                  value={filters.nameFilter}
                  onChange={handleFilterChange}
                  placeholder="Search by name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  School Year
                </label>
                <select
                  name="schoolYear"
                  value={filters.schoolYear}
                  onChange={handleFilterChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Years</option>
                  {schoolYearOptions.map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Term/Semester
                </label>
                <select
                  name="term"
                  value={filters.term}
                  onChange={handleFilterChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Terms</option>
                  {termOptions.map(term => (
                    <option key={term} value={term}>{term}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={resetFilters}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Reset
              </button>
              
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
              >
                Apply Filters
              </button>
            </div>
          </form>
        </div>
        
        {/* Profile Cards */}
        {loading ? (
          <div className="flex justify-center items-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : profiles.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-6 text-center">
            <p className="text-gray-500">No student profiles found. Upload student reports to generate profiles.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {profiles.map(profile => (
              <div 
                key={profile.id}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow hover:shadow-md transition-shadow duration-300"
              >
                <div className="bg-blue-50 border-b border-gray-200 px-4 py-3">
                  <div className="flex justify-between items-center">
                    <div className="font-medium text-blue-900 truncate">
                      {profile.full_name || 'Unknown Student'}
                    </div>
                    <div className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-1 rounded-full">
                      Grade {profile.grade_level || 'N/A'}
                    </div>
                  </div>
                </div>
                
                <div className="p-4">
                  <div className="mb-3 space-y-1">
                    {profile.current_school_year && profile.current_term && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">Current Term:</span>{' '}
                        <span className="text-gray-900">{profile.current_school_year} - {profile.current_term}</span>
                      </div>
                    )}
                    
                    {profile.school_name && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">School:</span>{' '}
                        <span className="text-gray-900">{profile.school_name}</span>
                      </div>
                    )}
                    
                    {profile.learning_style && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">Learning Style:</span>{' '}
                        <span className="text-gray-900 capitalize">{profile.learning_style}</span>
                      </div>
                    )}
                    
                    {/* Display ownership badge */}
                    <div className="mt-1">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                        <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                        Created by you
                      </span>
                    </div>
                  </div>
                  
                  {/* Strengths */}
                  {profile.strengths && profile.strengths.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-medium text-gray-500 mb-1">Strengths:</div>
                      <div className="flex flex-wrap gap-1">
                        {profile.strengths.slice(0, 3).map((item, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                            {item}
                          </span>
                        ))}
                        {profile.strengths.length > 3 && (
                          <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded">
                            +{profile.strengths.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Interests */}
                  {profile.interests && profile.interests.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-medium text-gray-500 mb-1">Interests:</div>
                      <div className="flex flex-wrap gap-1">
                        {profile.interests.slice(0, 3).map((item, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                            {item}
                          </span>
                        ))}
                        {profile.interests.length > 3 && (
                          <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded">
                            +{profile.interests.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Actions */}
                  <div className="mt-4 flex justify-between">
                    <div className="space-x-2">
                      <button
                        onClick={() => handleViewProfile(profile.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-sm font-medium rounded text-blue-700 bg-white hover:bg-blue-50"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Details
                      </button>
                      
                      <button
                        onClick={() => handleViewHistory(profile.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-green-300 text-sm font-medium rounded text-green-700 bg-white hover:bg-green-50"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        History
                      </button>
                    </div>
                    
                    <button
                      onClick={() => handleDeleteProfile(profile.id)}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded text-red-700 bg-white hover:bg-red-50"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };
  
  // Render profile detail view
  const renderProfileDetail = () => {
    if (!selectedProfile) return null;
    
    return (
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-blue-50 px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold text-gray-900">{selectedProfile.full_name}</h3>
            <button
              onClick={backToList}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to List
            </button>
          </div>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Basic Information */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-lg font-medium mb-3">Basic Information</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Grade Level:</span>
                  <span className="font-medium">{selectedProfile.grade_level || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Gender:</span>
                  <span className="font-medium capitalize">{selectedProfile.gender || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Learning Style:</span>
                  <span className="font-medium capitalize">{selectedProfile.learning_style || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">School:</span>
                  <span className="font-medium">{selectedProfile.school_name || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Teacher:</span>
                  <span className="font-medium">{selectedProfile.teacher_name || 'Not specified'}</span>
                </div>
              </div>
            </div>
            
            {/* Current Term Information */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-lg font-medium mb-3">Current Term Information</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">School Year:</span>
                  <span className="font-medium">{selectedProfile.current_school_year || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Term:</span>
                  <span className="font-medium">{selectedProfile.current_term || 'Not specified'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Updated:</span>
                  <span className="font-medium">{formatDate(selectedProfile.updated_at)}</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Strengths */}
          <div className="mt-6">
            <h4 className="text-lg font-medium mb-3">Strengths</h4>
            {selectedProfile.strengths && selectedProfile.strengths.length > 0 ? (
              <div className="bg-green-50 p-4 rounded-lg">
                <ul className="list-disc pl-5 space-y-1">
                  {selectedProfile.strengths.map((strength, idx) => (
                    <li key={idx} className="text-green-800">{strength}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-gray-500">No strengths specified</p>
            )}
          </div>
          
          {/* Interests */}
          <div className="mt-6">
            <h4 className="text-lg font-medium mb-3">Interests</h4>
            {selectedProfile.interests && selectedProfile.interests.length > 0 ? (
              <div className="bg-blue-50 p-4 rounded-lg">
                <ul className="list-disc pl-5 space-y-1">
                  {selectedProfile.interests.map((interest, idx) => (
                    <li key={idx} className="text-blue-800">{interest}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-gray-500">No interests specified</p>
            )}
          </div>
          
          {/* Areas for Improvement */}
          <div className="mt-6">
            <h4 className="text-lg font-medium mb-3">Areas for Improvement</h4>
            {selectedProfile.areas_for_improvement && selectedProfile.areas_for_improvement.length > 0 ? (
              <div className="bg-yellow-50 p-4 rounded-lg">
                <ul className="list-disc pl-5 space-y-1">
                  {selectedProfile.areas_for_improvement.map((area, idx) => (
                    <li key={idx} className="text-yellow-800">{area}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-gray-500">No areas for improvement specified</p>
            )}
          </div>
          
          {/* Term-specific data if available */}
          {selectedProfile.historical_data_filtered && Object.keys(selectedProfile.historical_data_filtered).length > 0 && (
            <div className="mt-6">
              <h4 className="text-lg font-medium mb-3">Term-Specific Information</h4>
              {Object.entries(selectedProfile.historical_data_filtered).map(([termId, termData]) => (
                <div key={termId} className="bg-purple-50 p-4 rounded-lg mb-4">
                  <h5 className="font-medium text-purple-800 mb-2">{termData.school_year} - {termData.term}</h5>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="text-sm text-gray-600">Grade Level: <span className="font-medium">{termData.grade_level || 'N/A'}</span></p>
                      <p className="text-sm text-gray-600">School: <span className="font-medium">{termData.school_name || 'N/A'}</span></p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Teacher: <span className="font-medium">{termData.teacher_name || 'N/A'}</span></p>
                      <p className="text-sm text-gray-600">Updated: <span className="font-medium">{formatDate(termData.updated_at)}</span></p>
                    </div>
                  </div>
                  
                  {/* Term Strengths */}
                  {termData.strengths && termData.strengths.length > 0 && (
                    <div className="mb-2">
                      <p className="text-sm font-medium text-gray-600 mb-1">Strengths:</p>
                      <div className="flex flex-wrap gap-1">
                        {termData.strengths.map((item, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Term Interests */}
                  {termData.interests && termData.interests.length > 0 && (
                    <div className="mb-2">
                      <p className="text-sm font-medium text-gray-600 mb-1">Interests:</p>
                      <div className="flex flex-wrap gap-1">
                        {termData.interests.map((item, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Term Areas for Improvement */}
                  {termData.areas_for_improvement && termData.areas_for_improvement.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Areas for Improvement:</p>
                      <div className="flex flex-wrap gap-1">
                        {termData.areas_for_improvement.map((item, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };
  
  // Render profile history view
  const renderProfileHistory = () => {
    if (!profileHistory) return null;
    
    return (
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-blue-50 px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold text-gray-900">
              {profileHistory.full_name} - Learning History
            </h3>
            <button
              onClick={backToList}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to List
            </button>
          </div>
        </div>
        
        <div className="p-6">
          {profileHistory.history && profileHistory.history.length > 0 ? (
            <div className="space-y-6">
              {/* Timeline */}
              <div className="relative">
                {profileHistory.history.map((item, idx) => (
                  <div key={idx} className="relative pl-8 pb-8">
                    {/* Timeline connector */}
                    {idx < profileHistory.history.length - 1 && (
                      <div className="absolute top-0 left-3 h-full w-0.5 bg-blue-200"></div>
                    )}
                    
                    {/* Timeline dot */}
                    <div className="absolute top-0 left-0 w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                      <span className="text-white text-xs font-bold">{idx + 1}</span>
                    </div>
                    
                    {/* Timeline content */}
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h4 className="text-lg font-medium text-blue-800 mb-2">
                        {item.school_year} - {item.term}
                      </h4>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                        <div>
                          <p className="text-sm text-gray-600">Grade Level: <span className="font-medium">{item.grade_level || 'N/A'}</span></p>
                          <p className="text-sm text-gray-600">School: <span className="font-medium">{item.school_name || 'N/A'}</span></p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Teacher: <span className="font-medium">{item.teacher_name || 'N/A'}</span></p>
                          <p className="text-sm text-gray-600">Updated: <span className="font-medium">{formatDate(item.updated_at)}</span></p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                        {/* Term Strengths */}
                        <div>
                          <h5 className="text-sm font-medium text-gray-800 mb-2">Strengths</h5>
                          {item.strengths && item.strengths.length > 0 ? (
                            <ul className="space-y-1">
                              {item.strengths.map((strength, i) => (
                                <li key={i} className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
                                  {strength}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-gray-500">None specified</p>
                          )}
                        </div>
                        
                        {/* Term Interests */}
                        <div>
                          <h5 className="text-sm font-medium text-gray-800 mb-2">Interests</h5>
                          {item.interests && item.interests.length > 0 ? (
                            <ul className="space-y-1">
                              {item.interests.map((interest, i) => (
                                <li key={i} className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                  {interest}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-gray-500">None specified</p>
                          )}
                        </div>
                        
                        {/* Term Areas for Improvement */}
                        <div>
                          <h5 className="text-sm font-medium text-gray-800 mb-2">Areas for Improvement</h5>
                          {item.areas_for_improvement && item.areas_for_improvement.length > 0 ? (
                            <ul className="space-y-1">
                              {item.areas_for_improvement.map((area, i) => (
                                <li key={i} className="text-sm bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                                  {area}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-gray-500">None specified</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">No historical data available for this student profile.</p>
            </div>
          )}
        </div>
      </div>
    );
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Student Profiles</h1>
        <button 
          onClick={() => {
            fetchProfiles();
            // Reset to list view
            setViewMode('list');
            setSelectedProfile(null);
            setProfileHistory(null);
          }}
          className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-700 border border-blue-300 rounded hover:bg-blue-200"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Profiles
        </button>
      </div>
      
      {/* Display success or error messages */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
          <span className="block sm:inline">{error}</span>
        </div>
      )}
      
      {successMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4">
          <span className="block sm:inline">{successMessage}</span>
        </div>
      )}
      
      {/* Display appropriate view based on viewMode */}
      {viewMode === 'list' && renderProfileList()}
      {viewMode === 'detail' && renderProfileDetail()}
      {viewMode === 'history' && renderProfileHistory()}
      {viewMode === 'create' && renderProfileCreation()}
    </div>
  );
};

export default StudentProfiles;