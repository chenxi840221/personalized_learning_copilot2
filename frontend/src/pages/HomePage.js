import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const HomePage = () => {
  const { user } = useAuth();

  return (
    <div className="container mx-auto px-4 py-12">
      {/* Hero Section */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
        <div className="lg:w-1/2">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
            Personalized Learning Co-pilot
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Your AI-powered companion for personalized education. Discover tailored learning
            plans and resources designed specifically for your students' learning styles and interests.
          </p>
          
          {user ? (
            <Link
              to="/dashboard"
              className="bg-blue-600 text-white px-6 py-3 rounded-md text-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Go to Your Dashboard
            </Link>
          ) : (
            <div className="flex flex-wrap gap-4">
              <Link
                to="/register"
                className="bg-blue-600 text-white px-6 py-3 rounded-md text-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Get Started as a Teacher
              </Link>
              <Link
                to="/login"
                className="border border-blue-600 text-blue-600 px-6 py-3 rounded-md text-lg font-medium hover:bg-blue-50 transition-colors"
              >
                Login
              </Link>
            </div>
          )}
        </div>
        
        <div className="lg:w-1/2">
          <img 
            src="/images/DXCLearningCopilot.png" 
            alt="Learning illustration" 
            className="rounded-lg shadow-lg w-full"
          />
        </div>
      </div>
      
      {/* Features Section */}
      <div className="py-16">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          How It Works
        </h2>
        
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <div className="bg-blue-100 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Create Your Students' Profiles</h3>
            <p className="text-gray-600">
              Tell us about your students' learning styles, demographics, and educational goals to personalize their learning experience.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <div className="bg-blue-100 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Get Learning Plans</h3>
            <p className="text-gray-600">
              Our AI creates personalized learning plans with curated resources matched to your students' needs.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <div className="bg-blue-100 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Track Students' Progress</h3>
            <p className="text-gray-600">
              Monitor your students' learning journeys and see their improvement over time with detailed analytics.
            </p>
          </div>
        </div>
      </div>
      
      {/* Subjects Section */}
      <div className="py-16 bg-gray-50 -mx-4 px-4">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Explore Subjects
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="h-40 bg-blue-200 flex items-center justify-center">
                <span className="text-4xl">📐</span>
              </div>
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">Mathematics</h3>
                <p className="text-gray-600 mb-4">
                  From basic arithmetic to advanced calculus, discover personalized math resources.
                </p>
                <Link to="/content/Mathematics" className="text-blue-600 font-medium hover:underline">
                  Explore Math Resources →
                </Link>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="h-40 bg-green-200 flex items-center justify-center">
                <span className="text-4xl">🔬</span>
              </div>
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">Science</h3>
                <p className="text-gray-600 mb-4">
                  Explore biology, chemistry, physics, and more with interactive and engaging content.
                </p>
                <Link to="/content/Science" className="text-blue-600 font-medium hover:underline">
                  Explore Science Resources →
                </Link>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="h-40 bg-yellow-200 flex items-center justify-center">
                <span className="text-4xl">📚</span>
              </div>
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">English</h3>
                <p className="text-gray-600 mb-4">
                  Literature, grammar, writing skills and language arts for all levels.
                </p>
                <Link to="/content/English" className="text-blue-600 font-medium hover:underline">
                  Explore English Resources →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Call to Action */}
      <div className="py-16 text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-6">
          Ready to Boost Your Teaching Journey with an AI Assistant?
        </h2>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Let us help students who are discovering the power of personalized learning.
          Get started today and unlock your teaching potential.
        </p>
        
        {user ? (
          <Link
            to="/dashboard"
            className="bg-blue-600 text-white px-8 py-4 rounded-md text-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Go to Your Dashboard
          </Link>
        ) : (
          <Link
            to="/register"
            className="bg-blue-600 text-white px-8 py-4 rounded-md text-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Create Your Teacher Account
          </Link>
        )}
      </div>
    </div>
  );
};

export default HomePage;