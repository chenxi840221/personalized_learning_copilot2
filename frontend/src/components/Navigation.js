// frontend/src/components/Navigation.js
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useEntraAuth } from '../hooks/useEntraAuth';

const Navigation = () => {
  const { user, loading, logout, isAuthenticated } = useEntraAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileView, setIsMobileView] = useState(false);
  
  // Check if we're on mobile view on first render and when resizing
  useEffect(() => {
    const checkMobileView = () => {
      setIsMobileView(window.innerWidth < 640);
    };
    
    // Initial check
    checkMobileView();
    
    // Add resize listener
    window.addEventListener('resize', checkMobileView);
    
    // Cleanup
    return () => window.removeEventListener('resize', checkMobileView);
  }, []);
  
  // Close mobile menu on navigation
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);
  
  // Toggle mobile menu
  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };
  
  // Close mobile menu
  const closeMenu = () => {
    setIsMenuOpen(false);
  };
  
  // Handle logout
  const handleLogout = () => {
    logout();
    closeMenu();
  };
  
  // Check if a link is active
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };
  
  return (
    <nav className="bg-white shadow-md">
      <div className="container mx-auto px-4">
        <div className="flex justify-between h-16">
          {/* Logo and main nav links */}
          <div className="flex">
            {/* Logo */}
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="font-bold text-xl text-blue-600">
                Learning Co-pilot
              </Link>
            </div>
            
            {/* Desktop Navigation Links */}
            <div className="hidden sm:ml-6 sm:flex sm:space-x-4 sm:items-center">
              <Link
                to="/"
                className={`px-3 py-2 text-sm font-medium rounded-md ${
                  isActive('/') 
                    ? 'bg-blue-50 text-blue-700' 
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                Home
              </Link>
              
              {isAuthenticated && (
                <>
                  <Link
                    to="/dashboard"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/dashboard') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    Dashboard
                  </Link>
                  
                  <Link
                    to="/content"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/content') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    Content
                  </Link>
                  
                  <Link
                    to="/reports"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/reports') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                    onClick={() => {
                      // Force report refresh when clicked
                      // This is a workaround for the navigation issue
                      if (isActive('/reports')) {
                        console.log('Refreshing reports from navigation click');
                        // Dispatch a custom event that StudentReport will listen for
                        window.dispatchEvent(new CustomEvent('refresh-reports'));
                      }
                    }}
                  >
                    Student Reports
                  </Link>

                  <Link
                    to="/profiles"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/profiles') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    Student Profiles
                  </Link>
                </>
              )}
            </div>
          </div>
          
          {/* User menu and mobile menu button */}
          <div className="flex items-center">
            {/* Authentication Links (Desktop) */}
            <div className="hidden sm:flex sm:items-center">
              {isAuthenticated ? (
                <div className="ml-3 relative">
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-700 mr-2">
                      {user?.full_name || user?.name || user?.username || user?.email}
                    </span>
                    
                    <Link to="/profile" className="mr-2">
                      <button className="bg-white p-1 rounded-full text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </button>
                    </Link>
                    
                    <button
                      onClick={handleLogout}
                      className="bg-blue-600 text-white px-3 py-1 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex space-x-2">
                  <Link
                    to="/login"
                    className="px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                  >
                    Login
                  </Link>
                  
                  <Link
                    to="/login"
                    className="px-3 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
            
            {/* Mobile menu button */}
            <div className="flex items-center sm:hidden">
              <button
                onClick={toggleMenu}
                aria-expanded={isMenuOpen}
                aria-label="Toggle navigation menu"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              >
                <span className="sr-only">{isMenuOpen ? 'Close menu' : 'Open menu'}</span>
                {/* Icon when menu is closed */}
                {!isMenuOpen ? (
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                ) : (
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile menu - Fixed position with full screen overlay */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-50 bg-white sm:hidden overflow-y-auto">
          <div className="absolute top-0 right-0 p-2">
            <button
              onClick={closeMenu}
              className="rounded-md p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
            >
              <span className="sr-only">Close menu</span>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="pt-16 pb-8 px-4">
            {/* Mobile nav links */}
            <div className="flex flex-col space-y-2">
              <Link
                to="/"
                className={`block px-4 py-3 text-lg font-medium rounded-md ${
                  isActive('/') 
                    ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                }`}
                onClick={closeMenu}
              >
                Home
              </Link>
              
              {isAuthenticated && (
                <>
                  <Link
                    to="/dashboard"
                    className={`block px-4 py-3 text-lg font-medium rounded-md ${
                      isActive('/dashboard') 
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                    }`}
                    onClick={closeMenu}
                  >
                    Dashboard
                  </Link>
                  
                  <Link
                    to="/content"
                    className={`block px-4 py-3 text-lg font-medium rounded-md ${
                      isActive('/content') 
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                    }`}
                    onClick={closeMenu}
                  >
                    Content
                  </Link>
                  
                  <Link
                    to="/reports"
                    className={`block px-4 py-3 text-lg font-medium rounded-md ${
                      isActive('/reports') 
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                    }`}
                    onClick={(e) => {
                      closeMenu();
                      // Force report refresh when clicked
                      if (isActive('/reports')) {
                        console.log('Refreshing reports from mobile navigation click');
                        // Dispatch a custom event that StudentReport will listen for
                        window.dispatchEvent(new CustomEvent('refresh-reports'));
                      }
                    }}
                  >
                    Student Reports
                  </Link>
                  
                  <Link
                    to="/profiles"
                    className={`block px-4 py-3 text-lg font-medium rounded-md ${
                      isActive('/profiles') 
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                    }`}
                    onClick={closeMenu}
                  >
                    Student Profiles
                  </Link>
                  
                  <Link
                    to="/profile"
                    className={`block px-4 py-3 text-lg font-medium rounded-md ${
                      isActive('/profile') 
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                    }`}
                    onClick={closeMenu}
                  >
                    Profile
                  </Link>
                </>
              )}
            </div>
            
            {/* Mobile user section */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              {isAuthenticated ? (
                <div>
                  <div className="flex items-center px-4 py-2">
                    <div className="flex-shrink-0">
                      <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-blue-600 font-semibold text-xl">
                          {user?.full_name 
                            ? user.full_name.charAt(0) 
                            : user?.name 
                              ? user.name.charAt(0) 
                              : user?.username 
                                ? user.username.charAt(0) 
                                : user?.email.charAt(0)}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-base font-medium text-gray-800">
                        {user?.full_name || user?.name || user?.username || user?.email}
                      </div>
                      <div className="text-sm font-medium text-gray-500">{user?.email}</div>
                    </div>
                  </div>
                  
                  <div className="mt-6">
                    <button
                      onClick={handleLogout}
                      className="w-full flex justify-center items-center px-4 py-3 bg-blue-600 text-white text-base font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <svg className="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      Logout
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 px-4">
                  <Link
                    to="/login"
                    className="w-full flex justify-center items-center px-4 py-3 border border-blue-500 text-blue-600 text-base font-medium rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    onClick={closeMenu}
                  >
                    Login
                  </Link>
                  
                  <Link
                    to="/login"
                    className="w-full flex justify-center items-center px-4 py-3 bg-blue-600 text-white text-base font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    onClick={closeMenu}
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navigation;