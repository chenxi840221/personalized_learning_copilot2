import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    confirm_password: '',
    grade_level: '',
    subjects_of_interest: [],
    learning_style: ''
  });
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();
  
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
    
    // Clear any previous errors
    setError('');
    
    // Validate passwords match
    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    
    // Validate grade level
    const gradeLevel = parseInt(formData.grade_level);
    if (isNaN(gradeLevel) || gradeLevel < 1 || gradeLevel > 12) {
      setError('Please enter a valid grade level (1-12)');
      return;
    }
    
    // Set loading state
    setIsLoading(true);
    
    try {
      // Prepare data for registration
      const userData = {
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
        grade_level: gradeLevel,
        subjects_of_interest: formData.subjects_of_interest,
        learning_style: formData.learning_style || null
      };
      
      // Attempt to register
      await register(userData);
      
      // Redirect to dashboard on success
      navigate('/dashboard');
    } catch (err) {
      // Display error message
      setError(err.message || 'Failed to register. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="flex justify-center items-center py-8">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-blue-600 mb-6">
          Create an Account
        </h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          {/* Basic Information */}
          <div className="mb-4">
            <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
              Username*
            </label>
            <input
              id="username"
              name="username"
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Choose a username"
              value={formData.username}
              onChange={handleChange}
              disabled={isLoading}
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="email" className="block text-gray-700 text-sm font-bold mb-2">
              Email*
            </label>
            <input
              id="email"
              name="email"
              type="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your email"
              value={formData.email}
              onChange={handleChange}
              disabled={isLoading}
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="full_name" className="block text-gray-700 text-sm font-bold mb-2">
              Full Name
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your full name"
              value={formData.full_name}
              onChange={handleChange}
              disabled={isLoading}
            />
          </div>
          
          {/* Password Fields */}
          <div className="mb-4">
            <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
              Password*
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Create a password"
              value={formData.password}
              onChange={handleChange}
              disabled={isLoading}
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="confirm_password" className="block text-gray-700 text-sm font-bold mb-2">
              Confirm Password*
            </label>
            <input
              id="confirm_password"
              name="confirm_password"
              type="password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Confirm your password"
              value={formData.confirm_password}
              onChange={handleChange}
              disabled={isLoading}
              required
            />
          </div>
          
          {/* Educational Information */}
          <div className="mb-4">
            <label htmlFor="grade_level" className="block text-gray-700 text-sm font-bold mb-2">
              Grade Level (1-12)*
            </label>
            <input
              id="grade_level"
              name="grade_level"
              type="number"
              min="1"
              max="12"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your grade level"
              value={formData.grade_level}
              onChange={handleChange}
              disabled={isLoading}
              required
            />
          </div>
          
          {/* Subjects of Interest */}
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
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
                    disabled={isLoading}
                  />
                  <label htmlFor={`subject-${subject}`} className="ml-2 block text-sm text-gray-700">
                    {subject}
                  </label>
                </div>
              ))}
            </div>
          </div>
          
          {/* Learning Style */}
          <div className="mb-6">
            <label htmlFor="learning_style" className="block text-gray-700 text-sm font-bold mb-2">
              Learning Style
            </label>
            <select
              id="learning_style"
              name="learning_style"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.learning_style}
              onChange={handleChange}
              disabled={isLoading}
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
          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50"
            disabled={isLoading}
          >
            {isLoading ? 'Registering...' : 'Register'}
          </button>
        </form>
        
        <div className="mt-4 text-center">
          <p className="text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-600 hover:underline">
              Login here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;