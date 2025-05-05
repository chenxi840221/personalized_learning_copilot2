// frontend/src/components/TestApiReport.js
import React, { useEffect, useState } from 'react';
import { getReports, apiClient } from '../services/api';
import { useEntraAuth } from '../hooks/useEntraAuth';

const TestApiReport = () => {
  const { user, getAccessToken, isAuthenticated, isTokenValid } = useEntraAuth();
  const [counter, setCounter] = useState(1);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const [authStatus, setAuthStatus] = useState('Checking...');
  
  // Function to make an API call directly
  const makeApiCall = async () => {
    try {
      // Check authentication first
      if (!isAuthenticated) {
        console.log(`🔥 TEST COMPONENT - CALL #${counter} - NOT AUTHENTICATED`);
        setLastResult('Not authenticated');
        setError('User is not authenticated');
        setCounter(prev => prev + 1);
        return null;
      }
      
      // Check if auth token is in headers
      const authHeader = apiClient.defaults.headers.common['Authorization'];
      console.log(`🔥 TEST COMPONENT - CALL #${counter} - Auth header exists: ${!!authHeader}`);
      
      if (!authHeader) {
        // Try to get a fresh token and set it
        try {
          const token = await getAccessToken();
          if (token) {
            console.log('Got fresh token, setting Authorization header');
            apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          } else {
            setLastResult('Could not get access token');
            setError('Token acquisition failed');
            setCounter(prev => prev + 1);
            return null;
          }
        } catch (tokenError) {
          console.error('Token acquisition error:', tokenError);
          setLastResult('Token error');
          setError(tokenError.message);
          setCounter(prev => prev + 1);
          return null;
        }
      }
      
      // Make the actual API call
      console.log(`🔥 TEST COMPONENT - CALL #${counter} - CALLING API DIRECTLY`);
      const reports = await getReports();
      console.log(`✅ Direct API call #${counter} result:`, reports);
      setLastResult(`Got ${reports?.length || 0} reports`);
      setError(null);
      setCounter(prev => prev + 1);
      return reports;
    } catch (error) {
      console.error(`❌ Direct API call #${counter} error:`, error);
      setError(error.message || 'Unknown error');
      setCounter(prev => prev + 1);
      return null;
    }
  };
  
  // Check authentication status
  useEffect(() => {
    const checkAuth = async () => {
      // Check if authenticated
      if (!isAuthenticated) {
        setAuthStatus('❌ Not authenticated');
        return;
      }
      
      // Check if token is valid
      if (!isTokenValid()) {
        setAuthStatus('⚠️ Token invalid or expired');
        return;
      }
      
      try {
        // Try to get a fresh token
        const token = await getAccessToken();
        if (!token) {
          setAuthStatus('⚠️ Could not get access token');
          return;
        }
        
        // Check if token is set in axios
        if (!apiClient.defaults.headers.common['Authorization']) {
          setAuthStatus('⚠️ No Authorization header in API client');
          // Set it manually
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        } else {
          setAuthStatus('✅ Authentication OK');
        }
        
        // Show token details
        console.log('🔑 Token preview:', token.substring(0, 15) + '...');
      } catch (error) {
        setAuthStatus(`❌ Auth error: ${error.message}`);
      }
    };
    
    checkAuth();
  }, [isAuthenticated, isTokenValid, getAccessToken, user]);
  
  useEffect(() => {
    // This will run once on component mount, directly triggering the API call
    console.log('🔥 TEST COMPONENT MOUNTED - INITIAL API CALL');
    
    // Make immediate API call
    makeApiCall();
    
    // Set up recurring API calls every 5 seconds
    const interval = setInterval(() => {
      makeApiCall();
    }, 5000);
    
    return () => {
      clearInterval(interval);
      console.log('🔥 TEST COMPONENT UNMOUNTED - CLEARING INTERVAL');
    };
  }, []);

  return (
    <div style={{ background: '#f0f0f0', padding: '20px', margin: '20px', border: '2px solid red' }}>
      <h2>API Test Component</h2>
      <p>This component directly makes an API call to the backend endpoint:</p>
      <pre style={{ background: '#000', color: '#fff', padding: '10px' }}>GET /student-reports</pre>
      
      <div style={{ 
        background: isAuthenticated ? '#d4edda' : '#f8d7da', 
        padding: '10px',
        borderRadius: '5px', 
        marginBottom: '10px' 
      }}>
        <h3 style={{ color: isAuthenticated ? '#155724' : '#721c24' }}>Authentication Status</h3>
        <p style={{ color: isAuthenticated ? '#155724' : '#721c24' }}>
          Status: {authStatus}
        </p>
        <p>
          {isAuthenticated ? '✅' : '❌'} User: {user ? user.name || user.email : 'Not logged in'}
        </p>
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
        <div>
          <h3>Last API call result:</h3>
          <p style={{ color: lastResult ? 'green' : 'gray' }}>
            {lastResult || 'No results yet'}
          </p>
        </div>
        
        <div>
          <h3>Errors:</h3>
          <p style={{ color: error ? 'red' : 'gray' }}>
            {error || 'No errors'}
          </p>
        </div>
      </div>
      
      <div style={{ marginTop: '10px' }}>
        <button 
          onClick={makeApiCall}
          style={{ 
            background: '#4CAF50', 
            border: 'none', 
            color: 'white', 
            padding: '10px 15px', 
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Make API Call Now
        </button>
        <p>Call count: {counter-1}</p>
        <p>Automatic calls every 5 seconds + manual calls</p>
      </div>
    </div>
  );
};

export default TestApiReport;