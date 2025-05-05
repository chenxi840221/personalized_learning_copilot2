import React from 'react';
import { useAuth } from '../hooks/useAuth';

const Profile = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center mb-6">
        <div className="h-20 w-20 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-2xl font-bold mr-4">
          {user.given_name ? user.given_name.charAt(0) : (user.full_name ? user.full_name.charAt(0) : user.username.charAt(0))}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            {user.given_name && user.family_name 
              ? `${user.given_name} ${user.family_name}` 
              : (user.full_name || user.username)}
          </h1>
          <p className="text-gray-600">{user.email}</p>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4">
        <h2 className="text-lg font-medium text-gray-800 mb-3">Student Information</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Grade Level</p>
            <p className="mt-1">{user.grade_level || 'Not specified'}</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-500">Learning Style</p>
            <p className="mt-1 capitalize">
              {user.learning_style 
                ? user.learning_style.replace('_', '/') 
                : 'Not specified'}
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 mt-4 pt-4">
        <h2 className="text-lg font-medium text-gray-800 mb-3">Subjects of Interest</h2>
        
        {user.subjects_of_interest && user.subjects_of_interest.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {user.subjects_of_interest.map(subject => (
              <span 
                key={subject}
                className="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded"
              >
                {subject}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No subjects specified</p>
        )}
      </div>

      <div className="mt-6">
        <button
          onClick={() => window.location.href = '/profile'}
          className="bg-blue-600 text-white font-medium py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
        >
          Edit Profile
        </button>
      </div>
    </div>
  );
};

export default Profile;