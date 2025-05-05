import React, { useState } from 'react';
import { updateActivityStatus } from '../services/content';
import LearningPlanManager from './LearningPlanManager';

const LearningPlan = ({ plan, onUpdate, onDelete }) => {
  const [expandedPlan, setExpandedPlan] = useState(false);
  const [showManager, setShowManager] = useState(false);
  const [localPlan, setLocalPlan] = useState(plan);
  const [updating, setUpdating] = useState(false);
  
  // Toggle expansion of plan details
  const toggleExpand = () => {
    setExpandedPlan(!expandedPlan);
    // Close manager if expanding/collapsing the plan
    if (showManager) setShowManager(false);
  };

  // Toggle manager visibility
  const toggleManager = (e) => {
    e.stopPropagation(); // Prevent triggering the plan expansion
    setShowManager(!showManager);
  };
  
  // Handle updating activity status
  const handleStatusChange = async (activityId, newStatus) => {
    setUpdating(true);
    
    try {
      // Update on server
      await updateActivityStatus(localPlan.id, activityId, newStatus, 
        newStatus === 'completed' ? new Date().toISOString() : null);
      
      // Update local state
      const updatedActivities = localPlan.activities.map(activity => {
        if (activity.id === activityId) {
          return {
            ...activity,
            status: newStatus,
            completed_at: newStatus === 'completed' ? new Date().toISOString() : null
          };
        }
        return activity;
      });
      
      // Calculate new progress percentage
      const totalActivities = updatedActivities.length;
      const completedActivities = updatedActivities.filter(a => a.status === 'completed').length;
      const newProgressPercentage = totalActivities > 0 
        ? Math.round((completedActivities / totalActivities) * 100) 
        : 0;
      
      // Update plan status if all activities are completed
      const newPlanStatus = completedActivities === totalActivities ? 'completed' 
        : completedActivities > 0 ? 'in_progress' : 'not_started';
      
      // Update local plan
      const updatedPlan = {
        ...localPlan,
        activities: updatedActivities,
        progress_percentage: newProgressPercentage,
        status: newPlanStatus
      };
      
      setLocalPlan(updatedPlan);
      
      // Notify parent
      if (onUpdate) {
        onUpdate(updatedPlan);
      }
    } catch (error) {
      console.error('Failed to update activity status:', error);
      // You could show an error toast here
    } finally {
      setUpdating(false);
    }
  };
  
  // Handle plan update from manager
  const handlePlanUpdate = (updatedPlan) => {
    setLocalPlan({
      ...localPlan,
      ...updatedPlan
    });
    
    // Notify parent
    if (onUpdate) {
      onUpdate({
        ...localPlan,
        ...updatedPlan
      });
    }
    
    // Close manager
    setShowManager(false);
  };
  
  // Handle plan deletion from manager
  const handlePlanDelete = (planId) => {
    // Notify parent
    if (onDelete) {
      onDelete(planId);
    }
  };
  
  // Get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };
  
  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Not started';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };
  
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Plan Header */}
      <div 
        className="flex flex-wrap items-center justify-between p-4 bg-gray-50 cursor-pointer gap-2"
        onClick={toggleExpand}
      >
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-medium text-gray-900 truncate">{localPlan.title}</h3>
          <div className="flex items-center space-x-2">
            <p className="text-sm text-gray-500">{localPlan.subject}</p>
            {/* Ownership badge */}
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
              Created by you
            </span>
          </div>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 mt-2 sm:mt-0">
          {/* Manage Button */}
          <button
            onClick={toggleManager}
            className="text-sm text-gray-600 hover:text-indigo-600 hover:underline flex items-center border border-gray-200 rounded px-2 py-1"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            Manage
          </button>
          
          {/* Progress Badge */}
          <div className="text-sm font-medium">
            {localPlan.progress_percentage}% Complete
          </div>
          
          {/* Status Badge */}
          <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(localPlan.status)}`}>
            {localPlan.status === 'not_started' ? 'Not Started' : 
              localPlan.status === 'in_progress' ? 'In Progress' : 'Completed'}
          </span>
          
          {/* Expand/Collapse Icon */}
          <svg 
            className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedPlan ? 'rotate-180' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      
      {/* Plan Manager */}
      {showManager && (
        <div className="border-t border-gray-200">
          <LearningPlanManager
            plan={localPlan}
            onUpdate={handlePlanUpdate}
            onDelete={handlePlanDelete}
          />
        </div>
      )}
      
      {/* Plan Details */}
      {expandedPlan && (
        <div className="p-4 border-t border-gray-200">
          {/* Description */}
          <p className="text-gray-600 mb-4">{localPlan.description}</p>
          
          {/* Plan Period Info */}
          {localPlan.start_date && localPlan.end_date && (
            <div className="mb-4 bg-indigo-50 p-3 rounded-md">
              <div className="flex flex-wrap gap-4">
                <div>
                  <span className="text-xs text-indigo-600 font-medium">Start Date:</span>
                  <p className="text-sm font-medium">{new Date(localPlan.start_date).toLocaleDateString()}</p>
                </div>
                <div>
                  <span className="text-xs text-indigo-600 font-medium">End Date:</span>
                  <p className="text-sm font-medium">{new Date(localPlan.end_date).toLocaleDateString()}</p>
                </div>
                {localPlan.metadata?.learning_period && (
                  <div>
                    <span className="text-xs text-indigo-600 font-medium">Learning Period:</span>
                    <p className="text-sm font-medium">{localPlan.metadata.learning_period.replace('_', ' ').charAt(0).toUpperCase() + localPlan.metadata.learning_period.replace('_', ' ').slice(1)}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
            <div 
              className="bg-blue-600 h-2.5 rounded-full" 
              style={{width: `${localPlan.progress_percentage}%`}}
            ></div>
          </div>
          
          {/* Activities grouped by day */}
          <h4 className="text-md font-medium text-gray-900 mb-2">Daily Activities</h4>
          
          {/* Group activities by day */}
          {(() => {
            // Group activities by day
            const groupedActivities = {};
            
            // Sort activities by day and then by order
            const sortedActivities = [...localPlan.activities].sort((a, b) => {
              if (a.day !== b.day) return a.day - b.day;
              return a.order - b.order;
            });
            
            // Group activities by day
            sortedActivities.forEach(activity => {
              const day = activity.day || 1; // Default to day 1 if not specified
              if (!groupedActivities[day]) {
                groupedActivities[day] = [];
              }
              groupedActivities[day].push(activity);
            });
            
            // Convert to array for rendering
            return Object.entries(groupedActivities).map(([day, activities]) => (
              <div key={`day-${day}`} className="mb-6">
                <h5 className="text-lg font-medium text-indigo-800 mb-2 pb-2 border-b border-indigo-100">
                  Day {day}
                  {localPlan.start_date && (
                    <span className="ml-2 text-sm font-normal text-gray-500">
                      {new Date(new Date(localPlan.start_date).getTime() + (parseInt(day) - 1) * 24 * 60 * 60 * 1000).toLocaleDateString()}
                    </span>
                  )}
                </h5>
                <div className="space-y-3">
                  {activities.map((activity, index) => (
                    <div key={activity.id} className="border border-gray-200 rounded p-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center flex-wrap gap-2">
                            <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded mr-2">
                              {activity.order}
                            </span>
                            <h5 className="text-gray-900 font-medium">{activity.title}</h5>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{activity.description}</p>
                          
                          {/* Activity Metadata */}
                          <div className="flex flex-wrap items-center mt-2 text-xs text-gray-500 gap-3">
                            <span className="flex items-center">
                              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              {activity.duration_minutes} minutes
                            </span>
                            
                            {activity.status === 'completed' && (
                              <span className="flex items-center">
                                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                Completed on {formatDate(activity.completed_at)}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        {/* Status Controls */}
                        <div className="mt-3 sm:mt-0">
                          <select
                            className="w-full sm:w-auto text-sm border border-gray-300 rounded px-2 py-1"
                            value={activity.status}
                            onChange={(e) => handleStatusChange(activity.id, e.target.value)}
                            disabled={updating}
                            aria-label={`Set status for ${activity.title}`}
                          >
                            <option value="not_started">Not Started</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                          </select>
                        </div>
                      </div>
                      
                      {/* Education Content Information Section */}
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        {/* Always display activity information */}
                        <div className="mb-3 bg-gray-50 p-3 rounded-md">
                          <h6 className="font-medium text-gray-700 mb-1">Activity Details:</h6>
                          <p className="text-sm font-medium text-gray-800 mb-1">
                            {activity.title}
                          </p>
                          <p className="text-sm text-gray-600 mb-2">
                            {activity.description}
                          </p>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                            <span className="bg-gray-100 px-2 py-1 rounded-md">
                              Duration: {activity.duration_minutes} minutes
                            </span>
                            <span className={`px-2 py-1 rounded-md ${
                              activity.status === 'completed' ? 'bg-green-100 text-green-800' :
                              activity.status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              Status: {activity.status === 'not_started' ? 'Not Started' :
                                      activity.status === 'in_progress' ? 'In Progress' : 'Completed'}
                            </span>
                            <span className="bg-gray-100 px-2 py-1 rounded-md">
                              Order: {activity.order}
                            </span>
                          </div>
                        </div>
                        
                        {/* Display content information if available */}
                        {/* Show education resource section if there is content info or if content_id/url exists */}
                        {(activity.metadata?.content_info || activity.content_id || activity.content_url) && (
                          <div className="mb-3 bg-blue-50 p-3 rounded-md">
                            <h6 className="font-medium text-blue-700 mb-1">Education Resource:</h6>
                            
                            {/* Title from metadata or fallback to activity title */}
                            <p className="text-sm font-medium text-blue-800 mb-1">
                              {activity.metadata?.content_info?.title || 
                               (activity.title.includes(':') ? activity.title.split(':')[1].trim() : activity.title)}
                            </p>
                            
                            {/* Description from metadata or fallback to partial activity description */}
                            <p className="text-sm text-blue-700">
                              {activity.metadata?.content_info?.description || 
                               (activity.description && activity.description.length > 120 ? 
                                  `${activity.description.substring(0, 120)}...` : activity.description)}
                            </p>
                            
                            {/* Add subject tags either from metadata or extract from activity title */}
                            <div className="mt-2 flex flex-wrap gap-2 text-xs">
                              <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md">
                                Subject: {activity.metadata?.content_info?.subject || 
                                         (activity.title.includes(':') ? activity.title.split(':')[0] : 'General')}
                              </span>
                              
                              {/* Show difficulty level if available */}
                              {activity.metadata?.content_info?.difficulty_level && (
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md">
                                  Level: {activity.metadata.content_info.difficulty_level}
                                </span>
                              )}
                              
                              {/* Show content type if available */}
                              {activity.metadata?.content_info?.content_type && (
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md">
                                  Type: {activity.metadata.content_info.content_type}
                                </span>
                              )}
                              
                              {/* Add grade level if available */}
                              {activity.metadata?.content_info?.grade_level && Array.isArray(activity.metadata.content_info.grade_level) && 
                               activity.metadata.content_info.grade_level.length > 0 && (
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md">
                                  Grade Level: {activity.metadata.content_info.grade_level.join(', ')}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Learning Benefit - why this activity helps (always show, with default if missing) */}
                        <div className="mb-3 bg-indigo-50 text-indigo-700 p-3 rounded-md text-sm">
                          <div className="font-medium mb-1">How this helps you:</div>
                          <p>
                            {activity.learning_benefit || 
                             `This activity helps develop critical ${activity.title.includes(':') ? 
                               activity.title.split(':')[0] : 'subject'} skills through structured learning exercises.`}
                          </p>
                        </div>
                        
                        {/* Always show resource link - prioritize metadata URL if available */}
                        <div className="mt-2">
                          {(activity.metadata?.content_info?.url || activity.content_url || activity.content_id) ? (
                            <a 
                              href={activity.metadata?.content_info?.url || activity.content_url || `/content/${activity.content_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline text-sm flex items-center"
                            >
                              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              Open learning resource
                            </a>
                          ) : (
                            <p className="text-gray-500 text-sm italic">
                              <svg className="w-4 h-4 mr-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              No external resource is attached to this activity
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ));
          })()}
        </div>
      )}
    </div>
  );
};

export default LearningPlan;