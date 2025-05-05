// frontend/src/pages/ProfilePage.js
import React, { useState, useEffect } from 'react';
import { useEntraAuth } from '../hooks/useEntraAuth';
import { api } from '../services/api';

const ProfilePage = () => {
  const { user } = useEntraAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    grade_level: '',
    subjects_of_interest: [],
    learning_style: ''
  });
  
  // Available subjects
  const availableSubjects = ['Mathematics', 'Science', 'English', 'History', 'Geography', 'Art'];
  
  // Available learning styles
  const learningStyles = [
    { value: 'visual', label: 'Visual' },
    { value: 'auditory', label: 'Auditory' },
    { value: 'reading_writing', label: 'Reading/Writing' },
    { value: 'kinesthetic', label: 'Kinesthetic' },
    { value: 'mixed', label: 'Mixed/Multiple' }
  ];
  
  // Initialize form data when user data changes
  useEffect(() => {
    if (user) {
      const displayName = user.given_name && user.family_name 
        ? `${user.given_name} ${user.family_name}` 
        : (user.full_name || '');
        
      setFormData({
        full_name: displayName,
        email: user.email || '',
        grade_level: user.grade_level || '',
        subjects_of_interest: user.subjects_of_interest || [],
        learning_style: user.learning_style || '',
        given_name: user.given_name || '',
        family_name: user.family_name || ''
      });
    }
  }, [user]);
  
  // Toggle edit mode
  const toggleEdit = () => {
    setIsEditing(!isEditing);
    setSuccessMessage('');
    setError('');
    
    // Reset form data if canceling edit
    if (isEditing && user) {
      const displayName = user.given_name && user.family_name 
        ? `${user.given_name} ${user.family_name}` 
        : (user.full_name || '');
        
      setFormData({
        full_name: displayName,
        email: user.email || '',
        grade_level: user.grade_level || '',
        subjects_of_interest: user.subjects_of_interest || [],
        learning_style: user.learning_style || '',
        given_name: user.given_name || '',
        family_name: user.family_name || ''
      });
    }
  };
  
  // Handle input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };
  
  // Handle checkbox changes for subjects
  const handleSubjectChange = (e) => {
    const { value, checked } = e.target;
    if (checked) {
      setFormData({
        ...formData,
        subjects_of_interest: [...formData.subjects_of_interest, value]
      });
    } else {
      setFormData({
        ...formData,
        subjects_of_interest: formData.subjects_of_interest.filter(subject => subject !== value)
      });
    }
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Clear any previous messages
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);
    
    try {
      // Validate grade level
      if (formData.grade_level) {
        const gradeLevel = parseInt(formData.grade_level);
        if (isNaN(gradeLevel) || gradeLevel < 1 || gradeLevel > 12) {
          setError('Please enter a valid grade level (1-12)');
          setIsSubmitting(false);
          return;
        }
      }
      
      // Prepare data for update
      const updateData = {
        full_name: formData.full_name,
        grade_level: formData.grade_level ? parseInt(formData.grade_level) : null,
        subjects_of_interest: formData.subjects_of_interest,
        learning_style: formData.learning_style || null
      };
      
      // Send update to API
      const updatedProfile = await api.put('/auth/profile', updateData);
      
      // Update success
      setSuccessMessage('Profile updated successfully!');
      
      // Exit edit mode
      setIsEditing(false);
    } catch (err) {
      console.error('Error updating profile:', err);
      setError(err.message || 'Failed to update profile. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Loading state when no user data
  if (!user) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Your Profile</h1>
          <button
            onClick={toggleEdit}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              isEditing 
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>
        
        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {successMessage}
          </div>
        )}
        
        {/* Error Message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {isEditing ? (
          // Edit Mode
          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Full Name */}
              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name
                </label>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.full_name}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
              </div>
              
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-100"
                  value={formData.email}
                  readOnly
                  disabled
                />
                <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
              </div>
              
              {/* Grade Level */}
              <div>
                <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
                  Grade Level (1-12)
                </label>
                <input
                  id="grade_level"
                  name="grade_level"
                  type="number"
                  min="1"
                  max="12"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.grade_level}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
              </div>
              
              {/* Subjects of Interest */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Subjects of Interest
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {availableSubjects.map(subject => (
                    <div key={subject} className="flex items-center">
                      <input
                        id={`subject-${subject}`}
                        type="checkbox"
                        name="subjects_of_interest"
                        value={subject}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        checked={formData.subjects_of_interest.includes(subject)}
                        onChange={handleSubjectChange}
                        disabled={isSubmitting}
                      />
                      <label htmlFor={`subject-${subject}`} className="ml-2 block text-sm text-gray-700">
                        {subject}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Learning Style */}
              <div>
                <label htmlFor="learning_style" className="block text-sm font-medium text-gray-700 mb-1">
                  Learning Style
                </label>
                <select
                  id="learning_style"
                  name="learning_style"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.learning_style}
                  onChange={handleChange}
                  disabled={isSubmitting}
                >
                  <option value="">Select your learning style</option>
                  {learningStyles.map(style => (
                    <option key={style.value} value={style.value}>
                      {style.label}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Submit Button */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </form>
        ) : (
          // View Mode
          <div className="space-y-6">
            {/* Basic Information */}
            <div className="border-b border-gray-200 pb-4">
              <h2 className="text-lg font-medium text-gray-800 mb-4">Basic Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Username/Email</p>
                  <p className="mt-1">{user.username || user.email}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Full Name</p>
                  <p className="mt-1">
                    {user.given_name && user.family_name 
                      ? `${user.given_name} ${user.family_name}` 
                      : (user.full_name || 'Not specified')}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Email</p>
                  <p className="mt-1">{user.email}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Grade Level</p>
                  <p className="mt-1">{user.grade_level || 'Not specified'}</p>
                </div>
              </div>
            </div>
            
            {/* Learning Preferences */}
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-4">Learning Preferences</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Learning Style</p>
                  <p className="mt-1 capitalize">
                    {user.learning_style 
                      ? learningStyles.find(style => style.value === user.learning_style)?.label || user.learning_style
                      : 'Not specified'}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Subjects of Interest</p>
                  {user.subjects_of_interest && user.subjects_of_interest.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {user.subjects_of_interest.map(subject => (
                        <span 
                          key={subject}
                          className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded"
                        >
                          {subject}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-1">No subjects specified</p>
                  )}
                </div>
              </div>
            </div>
            
            {/* Account Information */}
            <div className="border-t border-gray-200 pt-4">
              <h2 className="text-lg font-medium text-gray-800 mb-4">Account Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Account Status</p>
                  <p className="mt-1 flex items-center">
                    <span className="h-2.5 w-2.5 rounded-full bg-green-500 mr-2"></span>
                    Active
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Account Type</p>
                  <p className="mt-1">
                    Microsoft Account (Entra ID)
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;