import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { EntraAuthProvider } from './context/EntraAuthContext';

// Layout Components
import Navigation from './components/Navigation';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ContentPage from './pages/ContentPage';
import ProfilePage from './pages/ProfilePage';
import AuthCallback from './components/AuthCallback';

// Student Components
import StudentReport from './components/StudentReport';
import StudentProfiles from './components/StudentProfiles';
import StudentProfileCreator from './components/StudentProfileCreator';

// Protected Route Component
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <EntraAuthProvider>
      <div className="App min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } />
            
            <Route path="/content/:subject?" element={
              <ProtectedRoute>
                <ContentPage />
              </ProtectedRoute>
            } />
            
            <Route path="/profile" element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            } />
            
            <Route path="/reports" element={
              <ProtectedRoute>
                <StudentReport />
              </ProtectedRoute>
            } />
            
            <Route path="/profiles" element={
              <ProtectedRoute>
                <StudentProfiles />
              </ProtectedRoute>
            } />

            <Route path="/profiles/create" element={
              <ProtectedRoute>
                <StudentProfileCreator />
              </ProtectedRoute>
            } />
            
            <Route path="/profiles/edit/:profileId" element={
              <ProtectedRoute>
                <StudentProfileCreator />
              </ProtectedRoute>
            } />
            
            {/* Fallback Route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </EntraAuthProvider>
  );
}

export default App;