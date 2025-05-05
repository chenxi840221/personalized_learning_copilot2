// frontend/src/components/LearningPlanCreator.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useEntraAuth } from '../hooks/useEntraAuth';
import { getStudentProfiles } from '../services/api';
import { createLearningPlan, createAILearningPlan } from '../services/content';

/**
 * LearningPlanCreator - Component for creating personalized learning plans
 * Allows teachers to create learning plans for students based on their profiles
 */
const LearningPlanCreator = ({ onPlanCreated, onCancel }) => {
  const { user } = useAuth();
  const { getAccessToken, isAuthenticated } = useEntraAuth();
  const [loading, setLoading] = useState(false);
  const [studentProfiles, setStudentProfiles] = useState([]);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [authError, setAuthError] = useState(false);
  
  // Form state
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [planType, setPlanType] = useState('all_subjects'); // 'all_subjects' or 'single_subject'
  const [selectedSubject, setSelectedSubject] = useState('');
  const [dailyMinutes, setDailyMinutes] = useState(60); // Default to 1 hour daily
  const [learningPeriod, setLearningPeriod] = useState('one_month'); // Default to one month

  // Available subjects
  const subjects = ['Mathematics', 'Science', 'English', 'History', 'Geography', 'Art'];
  
  // Learning period options
  const learningPeriods = [
    { value: 'one_week', label: 'One Week' },
    { value: 'two_weeks', label: 'Two Weeks' },
    { value: 'one_month', label: 'One Month' },
    { value: 'two_months', label: 'Two Months' },
    { value: 'school_term', label: 'School Term' }
  ];
  
  // Fetch student profiles on component mount
  useEffect(() => {
    const fetchProfiles = async () => {
      setLoadingProfiles(true);
      setAuthError(false);
      
      try {
        // Get token if needed for authentication
        if (isAuthenticated) {
          const token = await getAccessToken();
          if (!token) {
            console.warn('No access token available');
            setAuthError(true);
            setError('Authentication error. Please try logging in again.');
            setLoadingProfiles(false);
            return;
          }
        }
        
        // Fetch profiles
        const profiles = await getStudentProfiles();
        setStudentProfiles(profiles || []);
        console.log(`Fetched ${profiles?.length || 0} student profiles`);
      } catch (error) {
        console.error('Error fetching student profiles:', error);
        
        // Check for auth errors
        if (error.status === 401 || error.status === 307) {
          setAuthError(true);
          setError('Authentication error. Please try logging in again.');
        } else {
          setError('Failed to load student profiles. Please try again.');
        }
      } finally {
        setLoadingProfiles(false);
      }
    };
    
    fetchProfiles();
  }, [isAuthenticated, getAccessToken]);
  
  // Handle profile selection
  const handleProfileChange = (e) => {
    const profileId = e.target.value;
    setSelectedProfileId(profileId);
    
    if (profileId) {
      const profile = studentProfiles.find(p => p.id === profileId);
      setSelectedProfile(profile);
    } else {
      setSelectedProfile(null);
    }
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedProfileId) {
      setError('Please select a student profile');
      return;
    }
    
    if (planType === 'single_subject' && !selectedSubject) {
      setError('Please select a subject');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      let createdPlan;
      
      // Different API calls based on plan type
      if (planType === 'all_subjects') {
        // Create a balanced learning plan for all subjects
        createdPlan = await createAILearningPlan({
          student_profile_id: selectedProfileId,
          daily_minutes: dailyMinutes,
          learning_period: learningPeriod,
          type: 'balanced'
        });
      } else {
        // Create a plan for a single subject
        createdPlan = await createAILearningPlan({
          student_profile_id: selectedProfileId,
          subject: selectedSubject,
          daily_minutes: dailyMinutes,
          learning_period: learningPeriod,
          type: 'focused'
        });
      }
      
      setSuccess('Learning plan created successfully!');
      
      // Notify parent component
      if (onPlanCreated) {
        onPlanCreated(createdPlan);
      }
      
      // Reset form after a short delay
      setTimeout(() => {
        setSelectedProfileId('');
        setSelectedProfile(null);
        setPlanType('all_subjects');
        setSelectedSubject('');
        setLearningPeriod('one_month');
        setSuccess('');
      }, 2000);
      
    } catch (error) {
      console.error('Error creating learning plan:', error);
      
      // Extract a more specific error message if available
      let errorMessage = 'Failed to create learning plan. Please try again.';
      if (error.message) {
        // Check for specific error messages
        if (error.message.includes('learning style') || error.message.includes('LearningStyle')) {
          errorMessage = 'There was an issue with the learning style format. We\'ve reported this and are using a default style instead.';
        } else if (error.message.includes('subject')) {
          errorMessage = 'Please select a valid subject for the learning plan.';
        } else if (error.message.includes('profile')) {
          errorMessage = 'There was an issue with the student profile data. Please check the profile or try another one.';
        } else {
          // Use the error message but limit its length
          errorMessage = `Error: ${error.message.slice(0, 100)}${error.message.length > 100 ? '...' : ''}`;
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Create Personalized Learning Plan</h2>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-700"
          aria-label="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        {/* Student Profile Selection */}
        <div className="mb-4">
          <label htmlFor="profile" className="block text-sm font-medium text-gray-700 mb-1">
            Select Student Profile<span className="text-red-500">*</span>
          </label>
          
          {loadingProfiles ? (
            <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
          ) : studentProfiles.length > 0 ? (
            <select
              id="profile"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={selectedProfileId}
              onChange={handleProfileChange}
              required
            >
              <option value="">Select a student profile...</option>
              {studentProfiles.map(profile => (
                <option key={profile.id} value={profile.id}>
                  {profile.full_name} - Grade {profile.grade_level}
                </option>
              ))}
            </select>
          ) : (
            <div className="text-amber-700 bg-amber-50 p-3 rounded-md text-sm">
              No student profiles available. Please create a student profile first.
            </div>
          )}
        </div>
        
        {/* Selected Profile Info */}
        {selectedProfile && (
          <div className="mb-6 bg-blue-50 p-4 rounded-md">
            <h3 className="font-medium text-blue-800 mb-2">Selected Student</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Name: <span className="font-medium">{selectedProfile.full_name}</span></p>
                <p className="text-sm text-gray-600">Grade: <span className="font-medium">{selectedProfile.grade_level}</span></p>
                <p className="text-sm text-gray-600">Learning Style: <span className="font-medium">{selectedProfile.learning_style || 'Not specified'}</span></p>
              </div>
              
              <div>
                <p className="text-sm text-gray-600">School: <span className="font-medium">{selectedProfile.school_name || 'Not specified'}</span></p>
                <p className="text-sm text-gray-600">Teacher: <span className="font-medium">{selectedProfile.teacher_name || 'Not specified'}</span></p>
                <p className="text-sm text-gray-600">Current Term: <span className="font-medium">{selectedProfile.current_school_year} - {selectedProfile.current_term}</span></p>
              </div>
            </div>
            
            {/* Show strengths, interests, and areas for improvement */}
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700">Strengths:</p>
                {selectedProfile.strengths && selectedProfile.strengths.length > 0 ? (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedProfile.strengths.map((strength, idx) => (
                      <span key={idx} className="inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                        {strength}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No strengths specified</p>
                )}
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-700">Interests:</p>
                {selectedProfile.interests && selectedProfile.interests.length > 0 ? (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedProfile.interests.map((interest, idx) => (
                      <span key={idx} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                        {interest}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No interests specified</p>
                )}
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-700">Areas for Improvement:</p>
                {selectedProfile.areas_for_improvement && selectedProfile.areas_for_improvement.length > 0 ? (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedProfile.areas_for_improvement.map((area, idx) => (
                      <span key={idx} className="inline-block px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                        {area}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No areas for improvement specified</p>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Plan Type Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Plan Type<span className="text-red-500">*</span>
          </label>
          <div className="flex flex-col sm:flex-row gap-4">
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-blue-600"
                name="planType"
                value="all_subjects"
                checked={planType === 'all_subjects'}
                onChange={() => setPlanType('all_subjects')}
              />
              <span className="ml-2 text-gray-700">Balanced Learning Plan (All Subjects)</span>
            </label>
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-blue-600"
                name="planType"
                value="single_subject"
                checked={planType === 'single_subject'}
                onChange={() => setPlanType('single_subject')}
              />
              <span className="ml-2 text-gray-700">Single Subject Focus</span>
            </label>
          </div>
        </div>
        
        {/* Subject Selection (only for single subject plans) */}
        {planType === 'single_subject' && (
          <div className="mb-4">
            <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
              Select Subject<span className="text-red-500">*</span>
            </label>
            <select
              id="subject"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              required={planType === 'single_subject'}
            >
              <option value="">Select a subject...</option>
              {subjects.map(subject => (
                <option key={subject} value={subject}>{subject}</option>
              ))}
            </select>
          </div>
        )}
        
        {/* Daily Study Time */}
        <div className="mb-4">
          <label htmlFor="dailyMinutes" className="block text-sm font-medium text-gray-700 mb-1">
            Daily Study Time (minutes)
          </label>
          <input
            type="number"
            id="dailyMinutes"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            value={dailyMinutes}
            onChange={(e) => setDailyMinutes(parseInt(e.target.value) || 60)}
            min="15"
            max="180"
          />
          <p className="mt-1 text-sm text-gray-500">
            Recommended: 30-60 minutes for elementary, 60-90 minutes for middle/high school
          </p>
        </div>
        
        {/* Learning Period Selection */}
        <div className="mb-6">
          <label htmlFor="learningPeriod" className="block text-sm font-medium text-gray-700 mb-1">
            Learning Period<span className="text-red-500">*</span>
          </label>
          <select
            id="learningPeriod"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            value={learningPeriod}
            onChange={(e) => setLearningPeriod(e.target.value)}
            required
          >
            {learningPeriods.map(period => (
              <option key={period.value} value={period.value}>
                {period.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-sm text-gray-500">
            Choose a learning period for the plan. Longer periods allow for more comprehensive learning journeys.
          </p>
        </div>
        
        {/* Description text based on plan type */}
        <div className="mb-6 bg-gray-50 p-4 rounded-md text-sm text-gray-700">
          {planType === 'all_subjects' ? (
            <p>
              A balanced learning plan will distribute study time across multiple subjects based on the student's strengths and areas for 
              improvement. More time will be allocated to subjects that need improvement while maintaining progress in 
              stronger areas.
            </p>
          ) : (
            <p>
              A single subject focus plan will create an intensive learning path for the selected subject,
              with a series of activities that build upon each other to strengthen understanding and skills in this area.
            </p>
          )}
        </div>
        
        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="mr-3 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !selectedProfileId || (planType === 'single_subject' && !selectedSubject)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Creating Plan...' : 'Create Learning Plan'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default LearningPlanCreator;