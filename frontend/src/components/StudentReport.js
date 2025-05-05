// frontend/src/components/StudentReport.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useEntraAuth } from '../hooks/useEntraAuth';
import { useLocation } from 'react-router-dom';
import { uploadReport, getReports, getReport, deleteReport, apiClient } from '../services/api';
import TestApiReport from './TestApiReport';

const StudentReport = () => {
  const { user } = useAuth();
  const { getAccessToken, isAuthenticated } = useEntraAuth();
  const location = useLocation();
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [lastFetchTime, setLastFetchTime] = useState(0);
  const fetchTimeoutRef = useRef(null);
  const [tokenRefreshed, setTokenRefreshed] = useState(false);
  
  // Forward declaration of fetchReports for use in useCallback
  const fetchReportsRef = useRef(null);
  
  // Create a debounced version of fetchReports to prevent too many API calls
  const debouncedFetchReports = useCallback(() => {
    // Clear any existing timeout
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
    }
    
    // Get current time
    const now = Date.now();
    
    // Only fetch if it's been at least 2 seconds since the last fetch
    if (now - lastFetchTime < 2000) {
      console.log('Throttling fetch request...');
      // Schedule a fetch after delay
      fetchTimeoutRef.current = setTimeout(() => {
        fetchReportsRef.current();
      }, 2000 - (now - lastFetchTime));
      return;
    }
    
    // Otherwise fetch immediately
    fetchReportsRef.current();
  }, [lastFetchTime]);

  // This runs when the component mounts
  useEffect(() => {
    console.log('📌 StudentReport component mounted');
    
    if (user) {
      // Immediately fetch on mount
      console.log('🚀 Component mounted with authenticated user, fetching reports');
      fetchReports();
      
      // Set up a periodic refresh at 30 second intervals while the component is mounted
      const intervalId = setInterval(() => {
        console.log('⏰ Periodic refresh triggered');
        if (document.visibilityState === 'visible') {
          fetchReports();
        }
      }, 30000); // 30 seconds
      
      // Also set a short timeout to ensure data is loaded after mount
      const initialDelayId = setTimeout(() => {
        if (document.visibilityState === 'visible') {
          console.log('⏱️ Secondary fetch to ensure data is loaded');
          fetchReports();
        }
      }, 1500); // 1.5 second delay for secondary fetch
      
      return () => {
        clearInterval(intervalId);
        clearTimeout(initialDelayId);
        console.log('⏰ Cleared refresh timers');
      };
    } else {
      console.log('⚠️ Component mounted without authenticated user, skipping fetch');
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);
  
  // Set up a listener that will refresh the reports whenever this component gains focus or after navigation
  useEffect(() => {
    // Create a function to handle route changes in single-page app
    const handleRouteChange = () => {
      // We are interested only in routes to the reports page
      if (window.location.pathname === '/reports') {
        console.log('📍 Navigation detected to reports page - triggering refresh');
        // Use multiple timeouts at different intervals for better reliability
        if (user) {
          // Immediate fetch
          fetchReports();
          
          // Then again after a short delay to ensure component is fully mounted
          setTimeout(() => fetchReports(), 500);
          
          // And one more time after a longer delay to catch any race conditions
          setTimeout(() => fetchReports(), 2000);
        }
      }
    };
    
    // This function runs when this component receives focus
    const handleFocus = () => {
      console.log('💡 Window focus event detected, checking if on reports page');
      if (window.location.pathname === '/reports' && user) {
        console.log('🔄 On reports page, refreshing data on focus');
        fetchReports();
      }
    };
    
    // Function to handle history changes (forward/back navigation)
    const handleHistoryChange = () => {
      if (window.location.pathname === '/reports' && user) {
        console.log('⏮️ History navigation detected, refreshing reports');
        fetchReports();
        // Try again after a short delay
        setTimeout(() => fetchReports(), 800);
      }
    };
    
    // Listen for popstate events (browser navigation)
    window.addEventListener('popstate', handleRouteChange);
    // Listen for focus events
    window.addEventListener('focus', handleFocus);
    // Listen for route changes
    document.addEventListener('routeChange', handleRouteChange);
    // Listen for history changes (forward/back buttons)
    window.addEventListener('popstate', handleHistoryChange);
    
    // Call once right now if we're on the reports page
    if (window.location.pathname === '/reports') {
      console.log('📍 Currently on reports page - triggering refresh');
      if (user) {
        // Multiple fetches at different times for better reliability
        fetchReports();
        setTimeout(() => fetchReports(), 200);
        setTimeout(() => fetchReports(), 1000);
      }
    }
    
    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('routeChange', handleRouteChange);
      window.removeEventListener('popstate', handleHistoryChange);
      console.log('🔴 StudentReport navigation listeners removed');
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);
  
  // Effect for handling user authentication changes
  useEffect(() => {
    // If a user becomes authenticated while the component is mounted
    if (user) {
      console.log('👤 User authenticated, fetching reports');
      fetchReports();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);
  
  // Track location changes to reload data when navigating back to this page
  useEffect(() => {
    console.log('📌 Location changed:', location.pathname);
    if (location.pathname === '/reports' && user) {
      console.log('🔍 Detected navigation to reports page via location change');
      fetchReports();
      
      // Multiple fetch attempts for reliability
      const timeoutIds = [
        setTimeout(() => fetchReports(), 200),
        setTimeout(() => fetchReports(), 800)
      ];
      
      return () => {
        timeoutIds.forEach(id => clearTimeout(id));
      };
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, user]);
  
  // Add handling for various events that should trigger a data refresh
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && user) {
        console.log('🔄 Tab became visible, fetching reports...');
        fetchReports(); // Use direct fetch for visibility change
      }
    };
    
    const handleFocus = () => {
      if (user) {
        console.log('🔄 Window gained focus, fetching reports...');
        fetchReports(); // Use direct fetch for focus
      }
    };
    
    const handleNavigation = (event) => {
      if (user) {
        console.log('🔄 Navigation to reports triggered refresh');
        // Small delay to ensure DOM is ready
        setTimeout(() => {
          fetchReports();
        }, 100);
      }
    };

    const handleCustomRefresh = () => {
      if (user) {
        console.log('🔄 Custom refresh event received, fetching reports...');
        fetchReports(); // Use direct fetch for explicit refresh
      }
    };
    
    // Register event listeners
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('popstate', handleNavigation);
    window.addEventListener('refresh-reports', handleCustomRefresh);
    
    // Add a second fetch after a delay to catch any race conditions
    if (user) {
      const delayedFetch = setTimeout(() => {
        console.log('🕒 Delayed fetch to ensure data is loaded');
        fetchReports();
      }, 1000);
      
      return () => clearTimeout(delayedFetch);
    }
    
    return () => {
      // Clean up event listeners
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('popstate', handleNavigation);
      window.removeEventListener('refresh-reports', handleCustomRefresh);
      
      // Clear any pending timeouts on unmount
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Function to ensure auth token is set before making API calls
  const ensureAuth = async () => {
    if (!isAuthenticated) {
      console.log('⚠️ Not authenticated, skipping token refresh');
      return false;
    }
    
    // Check if Authorization header is already set
    const authHeader = apiClient.defaults.headers.common['Authorization'];
    if (!authHeader) {
      console.log('🔐 Authorization header not set, getting fresh token');
      try {
        const token = await getAccessToken();
        if (token) {
          console.log('🔑 Setting new Authorization header with fresh token');
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          setTokenRefreshed(true);
          return true;
        } else {
          console.error('❌ Failed to get access token');
          return false;
        }
      } catch (error) {
        console.error('❌ Error getting access token:', error);
        return false;
      }
    } else {
      // Even if header exists, check if token is valid and refresh if needed
      try {
        // Always get a fresh token to ensure it's valid
        const token = await getAccessToken({ forceRefresh: false });
        if (token) {
          // Update header with fresh token
          console.log('🔄 Refreshing existing Authorization header with fresh token');
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      } catch (error) {
        console.warn('⚠️ Error refreshing token, continuing with existing token:', error);
        // Continue with existing token
      }
      
      console.log('✅ Authorization header already set');
      return true;
    }
  };

  const fetchReports = async () => {
    console.log('🔄 FETCH REPORTS CALLED - API REQUEST STARTING');
    
    // Ensure authentication first with multiple retry attempts
    let authSuccess = false;
    
    // First try
    authSuccess = await ensureAuth();
    
    // If first try failed, try one more time after a short delay
    if (!authSuccess) {
      console.log('⚠️ First auth attempt failed, trying again...');
      await new Promise(resolve => setTimeout(resolve, 500));
      authSuccess = await ensureAuth();
    }
    
    if (!authSuccess) {
      console.error('❌ Authentication check failed, cannot fetch reports');
      setError('Authentication required. Please log in.');
      setLoading(false);
      return;
    }
    
    // Don't set loading state if we already have reports to prevent flickering
    // Only show loading indicator on initial load, not on refresh
    const isInitialLoad = reports.length === 0;
    if (isInitialLoad) {
      setLoading(true);
    }
    
    // Update the last fetch time
    setLastFetchTime(Date.now());
    
    try {
      // No filters needed anymore
      console.log('📡 API Request: GET /student-reports');
      const data = await getReports();
      console.log('✅ API Response received. Reports fetched:', data?.length || 0, 'reports');
      
      // If we got data, update the reports
      if (data) {
        setReports(data);
        setError('');
      } else {
        // If we get null/undefined but no error, set empty array
        setReports([]);
        setError('');
      }
    } catch (err) {
      // Special handling for authentication errors
      if (err?.response?.status === 401) {
        console.error('🔒 Authentication error (401), trying to refresh token');
        try {
          // Try to get a completely fresh token with force refresh
          const token = await getAccessToken({ forceRefresh: true });
          
          if (token) {
            // Set the fresh token in the header
            console.log('🔑 Setting fresh token after 401 error');
            apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            
            // Try the request again with the new token
            console.log('🔄 Retrying fetch with new token');
            const data = await getReports();
            if (data) {
              setReports(data);
              setError('');
              return;
            }
          }
        } catch (refreshError) {
          console.error('Failed to refresh token:', refreshError);
        }
      }
      
      // On error, keep the existing reports (don't clear them)
      // Only show error message if this was an initial load
      if (isInitialLoad) {
        setError('Failed to fetch reports. Please try again.');
      } else {
        // For refresh errors, show a less disruptive error message
        console.error('Error refreshing reports:', err);
      }
    } finally {
      // Only update loading state if this was the initial load
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };
  
  // Set the ref to point to the actual function
  // This needs to happen after the function is defined
  useEffect(() => {
    fetchReportsRef.current = fetchReports;
  }, [reports.length]); // Re-assign when reports length changes because of the conditional loading state

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    // Track uploading state separately from general loading
    setUploading(true);
    setUploadProgress(0);
    setError('');
    setSuccessMessage('');
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('report_type', 'primary'); // Default to primary

      // Create a custom uploader with progress tracking
      const onUploadProgress = (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
        console.log(`Upload progress: ${percentCompleted}%`);
      };

      // Custom implementation to handle progress
      const data = await new Promise((resolve, reject) => {
        apiClient.post('/student-reports/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 600000, // 10 minutes for large files
          onUploadProgress
        })
        .then(response => resolve(response.data))
        .catch(error => reject(error));
      });
      
      // Add the new report to the list and reset form
      setReports([data, ...reports]);
      setSelectedFile(null);
      
      // Set success message if profile was processed
      if (data.profile_processed) {
        setSuccessMessage('Student report uploaded and student profile updated successfully.');
      } else {
        setSuccessMessage('Student report uploaded successfully.');
      }
      
      // Reset the file input
      document.getElementById('report-file-input').value = '';
    } catch (err) {
      console.error('Error uploading report:', err);
      
      // Check if it's a timeout error
      if (err.message && err.message.includes('timeout')) {
        setError('Document processing timeout. Please try a smaller file or try again later.');
      } else if (err.response && err.response.status) {
        // Server returned an error status
        const status = err.response.status;
        let errorMsg = '';
        
        switch (status) {
          case 400:
            errorMsg = 'Invalid file format. Please check your file and try again.';
            break;
          case 401:
            errorMsg = 'You need to log in again to upload reports.';
            break;
          case 413:
            errorMsg = 'File is too large. Please upload a smaller file.';
            break;
          case 500:
            errorMsg = 'Server error while processing the report. Our team has been notified.';
            break;
          default:
            errorMsg = `Error (${status}): Failed to upload report. Please try again later.`;
        }
        
        setError(errorMsg);
      } else {
        // Generic error
        setError('Failed to upload report. The document processing may be taking too long. Please try again with a smaller file or try again later.');
      }
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleViewReport = async (reportId) => {
    setLoading(true);
    try {
      const data = await getReport(reportId);
      setSelectedReport(data);
      setError('');
    } catch (err) {
      setError('Failed to fetch report details. Please try again.');
      console.error('Error fetching report details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteReport = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report?')) return;

    setLoading(true);
    try {
      await deleteReport(reportId);
      
      // Remove the deleted report from the list
      setReports(reports.filter(report => report.id !== reportId));
      
      // Clear selected report if it was the one deleted
      if (selectedReport && selectedReport.id === reportId) {
        setSelectedReport(null);
      }
      
      setError('');
    } catch (err) {
      setError('Failed to delete report. Please try again.');
      console.error('Error deleting report:', err);
    } finally {
      setLoading(false);
    }
  };

  const closeReportDetail = () => {
    setSelectedReport(null);
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  // Generate a unique key for rendering
  const componentKey = `reports-${lastFetchTime}`;
  
  // Restructured for easier debugging
  return (
    <div id="reports-container" className="container mx-auto px-4 py-8" key={componentKey}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Student Reports</h1>
        <button 
          onClick={() => {
            console.log('Header refresh button clicked');
            // Clear state and force refresh
            setReports([]);
            setLoading(true);
            fetchReports();
          }}
          className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-700 border border-blue-300 rounded hover:bg-blue-200"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Reports
        </button>
      </div>
      
      {/* TestApiReport component removed as requested */}
      
      {/* Upload Form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Upload New Report</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Report File (PDF, DOCX, JPG, PNG)
            </label>
            <input
              id="report-file-input"
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.docx,.jpg,.jpeg,.png"
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
          </div>
          
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedFile}
            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {uploading ? 'Processing...' : 'Upload Report'}
          </button>
          
          {uploading && (
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {uploadProgress < 100 ? 
                  `Uploading: ${uploadProgress}%` : 
                  'Processing document... This may take up to 2 minutes.'}
              </p>
              <p className="text-sm text-blue-600 mt-1">
                {uploadProgress === 100 && 
                  'Analyzing report and updating student profile...'}
              </p>
            </div>
          )}
          
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          {successMessage && <p className="text-green-600 text-sm mt-2">{successMessage}</p>}
        </div>
      </div>
      
      {/* Reports List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Student Reports</h2>
        
        {loading && !selectedReport && (
          <p className="text-gray-500 text-center py-4">Loading reports...</p>
        )}
        
        {!loading && reports.length === 0 && (
          <div>
            <p className="text-gray-500 text-center py-4">No reports found. Upload your first report above.</p>
            <button 
              onClick={() => fetchReports()} 
              className="w-full mt-2 py-2 px-4 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              Refresh Reports List
            </button>
          </div>
        )}
        
        {reports.length > 0 && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <p className="text-gray-700">Found {reports.length} reports</p>
              <button 
                onClick={() => {
                  console.log('Manual refresh button clicked');
                  fetchReports();
                }} 
                className="py-1 px-3 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
              >
                Refresh List
              </button>
            </div>
            
            {/* Debug panel removed as requested */}
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {reports.map((report) => (
              <div 
                key={report.id} 
                className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow hover:shadow-md transition-shadow duration-300"
              >
                {/* Report Header */}
                <div className="bg-blue-50 border-b border-gray-200 px-4 py-3">
                  <div className="flex justify-between items-center">
                    <div className="font-medium text-blue-900 truncate">
                      {report.student_name || 'Unknown Student'}
                    </div>
                    <div className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-1 rounded-full">
                      {formatDate(report.report_date || report.created_at)}
                    </div>
                  </div>
                </div>
                
                {/* Report Content */}
                <div className="p-4">
                  <div className="mb-3 space-y-1">
                    {report.school_year && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">School Year:</span>{' '}
                        <span className="text-gray-900">{report.school_year}</span>
                      </div>
                    )}
                    
                    {report.term && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">Term:</span>{' '}
                        <span className="text-gray-900">{report.term}</span>
                      </div>
                    )}
                    
                    {report.grade_level && (
                      <div className="text-sm">
                        <span className="font-medium text-gray-500">Grade Level:</span>{' '}
                        <span className="text-gray-900">{report.grade_level}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Subject Highlights */}
                  {report.subjects && report.subjects.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-medium text-gray-500 mb-1">Subjects:</div>
                      <div className="flex flex-wrap gap-1">
                        {report.subjects.slice(0, 5).map((subject, idx) => (
                          <span key={idx} className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">
                            {subject.name}
                          </span>
                        ))}
                        {report.subjects.length > 5 && (
                          <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded">
                            +{report.subjects.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Actions */}
                  <div className="mt-4 flex justify-between">
                    <button
                      onClick={() => handleViewReport(report.id)}
                      className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-sm font-medium rounded text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      View Details
                    </button>
                    
                    <button
                      onClick={() => handleDeleteReport(report.id)}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
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
          </div>
        )}
      </div>
      
      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 overflow-y-auto z-50">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-5xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Report Details
                    </h3>
                    
                    <div className="mt-6 space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-500">School Information</h4>
                          <p className="mt-1">
                            <span className="font-medium">School: </span>
                            {selectedReport.school_name || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Year: </span>
                            {selectedReport.school_year || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Term: </span>
                            {selectedReport.term || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Grade Level: </span>
                            {selectedReport.grade_level || 'N/A'}
                          </p>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium text-gray-500">Report Information</h4>
                          <p className="mt-1">
                            <span className="font-medium">Type: </span>
                            {selectedReport.report_type}
                          </p>
                          <p>
                            <span className="font-medium">Date: </span>
                            {formatDate(selectedReport.report_date)}
                          </p>
                          <p>
                            <span className="font-medium">Teacher: </span>
                            {selectedReport.teacher_name || 'N/A'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Attendance */}
                      {selectedReport.attendance && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Attendance</h4>
                          <div className="mt-1 grid grid-cols-3 gap-4">
                            <div className="text-center p-2 bg-green-50 rounded">
                              <p className="text-xs text-gray-500">Present</p>
                              <p className="text-xl font-bold text-green-600">
                                {selectedReport.attendance.days_present || 0}
                              </p>
                            </div>
                            <div className="text-center p-2 bg-red-50 rounded">
                              <p className="text-xs text-gray-500">Absent</p>
                              <p className="text-xl font-bold text-red-600">
                                {selectedReport.attendance.days_absent || 0}
                              </p>
                            </div>
                            <div className="text-center p-2 bg-yellow-50 rounded">
                              <p className="text-xs text-gray-500">Late</p>
                              <p className="text-xl font-bold text-yellow-600">
                                {selectedReport.attendance.days_late || 0}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Subjects */}
                      {selectedReport.subjects && selectedReport.subjects.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Subject Performance</h4>
                          <div className="mt-2 space-y-6">
                            {selectedReport.subjects.map((subject, index) => (
                              <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                                <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                                  <div className="flex justify-between items-center">
                                    <h3 className="text-md font-medium text-gray-900">{subject.name}</h3>
                                    <div className="flex items-center space-x-3">
                                      {subject.grade && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                          Grade: {subject.grade}
                                        </span>
                                      )}
                                      {subject.achievement_level && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                          {subject.achievement_level}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="p-4 space-y-4">
                                  {/* Comments */}
                                  {subject.comments && (
                                    <div>
                                      <h4 className="text-xs font-medium text-gray-500">Comments</h4>
                                      <p className="mt-1 text-sm text-gray-700">
                                        {subject.comments}
                                      </p>
                                    </div>
                                  )}
                                  
                                  {/* Strengths */}
                                  {subject.strengths && subject.strengths.length > 0 && (
                                    <div>
                                      <h4 className="text-xs font-medium text-gray-500">Strengths</h4>
                                      <ul className="mt-1 list-disc list-inside text-sm text-gray-700 pl-1">
                                        {subject.strengths.map((strength, idx) => (
                                          <li key={idx}>{strength}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                  
                                  {/* Areas for Improvement */}
                                  {subject.areas_for_improvement && subject.areas_for_improvement.length > 0 && (
                                    <div>
                                      <h4 className="text-xs font-medium text-gray-500">Areas for Improvement</h4>
                                      <ul className="mt-1 list-disc list-inside text-sm text-gray-700 pl-1">
                                        {subject.areas_for_improvement.map((area, idx) => (
                                          <li key={idx}>{area}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* General Comments */}
                      {selectedReport.general_comments && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">General Comments</h4>
                          <div className="mt-1 p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-700">
                              {selectedReport.general_comments}
                            </p>
                          </div>
                        </div>
                      )}
                      
                      {/* Document Link */}
                      {selectedReport.document_url && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Original Document</h4>
                          <div className="mt-1">
                            <a 
                              href={selectedReport.document_url} 
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                              View Original Document
                            </a>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={closeReportDetail}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentReport;