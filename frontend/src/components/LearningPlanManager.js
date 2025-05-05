import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { deleteLearningPlan, updateLearningPlan, exportLearningPlan } from '../services/content';

const LearningPlanManager = ({ plan, onUpdate, onDelete }) => {
  const [isEditMode, setIsEditMode] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [editedPlan, setEditedPlan] = useState({ ...plan });
  const [error, setError] = useState('');
  const [exportFormat, setExportFormat] = useState('json');
  
  // Handle edit mode toggle
  const handleEditToggle = () => {
    if (isEditMode) {
      // Reset to original plan if canceling edit
      setEditedPlan({ ...plan });
    }
    setIsEditMode(!isEditMode);
    setError('');
  };
  
  // Handle plan field changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditedPlan({ ...editedPlan, [name]: value });
  };
  
  // Handle save changes
  const handleSave = async () => {
    try {
      setError('');
      
      // Basic validation
      if (!editedPlan.title.trim()) {
        setError('Title is required');
        return;
      }
      
      // Update the plan
      const updatedPlan = await updateLearningPlan(plan.id, {
        title: editedPlan.title,
        description: editedPlan.description,
        subject: editedPlan.subject
      });
      
      // Call parent update handler
      if (onUpdate) {
        onUpdate(updatedPlan);
      }
      
      // Exit edit mode
      setIsEditMode(false);
    } catch (err) {
      console.error('Error saving plan:', err);
      setError('Failed to save changes');
    }
  };
  
  // Handle delete plan
  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this learning plan? This action cannot be undone.')) {
      return;
    }
    
    try {
      setIsDeleting(true);
      setError('');
      
      await deleteLearningPlan(plan.id);
      
      // Call parent delete handler
      if (onDelete) {
        onDelete(plan.id);
      }
    } catch (err) {
      console.error('Error deleting plan:', err);
      setError('Failed to delete plan');
      setIsDeleting(false);
    }
  };
  
  // Handle plan export
  const handleExport = async () => {
    try {
      setIsExporting(true);
      setError('');
      
      const exported = await exportLearningPlan(plan.id, exportFormat);
      
      // Handle different export formats
      if (exportFormat === 'json') {
        // For JSON, create and download a file
        const dataStr = JSON.stringify(exported, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `${plan.title.replace(/\s+/g, '_')}_plan.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
      } else if (exportFormat === 'html' || exportFormat === 'pdf') {
        // For HTML content, open in a new tab or create a download
        if (exported.content) {
          const blob = new Blob([exported.content], { type: 'text/html' });
          const url = URL.createObjectURL(blob);
          
          // Open in a new tab
          window.open(url, '_blank');
          
          // Cleanup
          setTimeout(() => {
            URL.revokeObjectURL(url);
          }, 100);
        } else {
          setError('Failed to generate export content');
        }
      }
      
      setIsExporting(false);
    } catch (err) {
      console.error('Error exporting plan:', err);
      setError('Failed to export plan');
      setIsExporting(false);
    }
  };
  
  // Share plan via email or copy link
  const handleShare = () => {
    // Create a share message with plan details
    const shareText = `Check out this learning plan: ${plan.title}\n\nSubject: ${plan.subject}\n\nDescription: ${plan.description}`;
    
    // Try to use the Web Share API if available
    if (navigator.share) {
      navigator.share({
        title: `Learning Plan: ${plan.title}`,
        text: shareText,
      }).catch(err => {
        console.error('Error sharing:', err);
        // Fallback to clipboard copy
        copyToClipboard(shareText);
      });
    } else {
      // Fallback to clipboard copy
      copyToClipboard(shareText);
    }
  };
  
  // Helper to copy text to clipboard
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Plan details copied to clipboard!');
    }).catch(err => {
      console.error('Failed to copy:', err);
      alert('Failed to copy to clipboard. Please try again.');
    });
  };
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
      {isEditMode ? (
        /* Edit Mode */
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Learning Plan</h3>
          
          {error && (
            <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                Title
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={editedPlan.title}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            
            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-gray-700">
                Subject
              </label>
              <input
                type="text"
                id="subject"
                name="subject"
                value={editedPlan.subject}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                value={editedPlan.description}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            
            <div className="flex justify-end space-x-3 pt-3">
              <button
                type="button"
                onClick={handleEditToggle}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Management Mode */
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Manage Learning Plan</h3>
          
          {error && (
            <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Edit Button */}
              <button
                type="button"
                onClick={handleEditToggle}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
              >
                <svg className="h-5 w-5 mr-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Plan Details
              </button>
              
              {/* Delete Button */}
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="inline-flex items-center px-4 py-2 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none"
              >
                <svg className="h-5 w-5 mr-2 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                {isDeleting ? 'Deleting...' : 'Delete Plan'}
              </button>
              
              {/* Export Section */}
              <div className="md:col-span-2 p-4 bg-gray-50 rounded-md">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Export Learning Plan</h4>
                <div className="flex items-center flex-wrap gap-3">
                  <select
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                  >
                    <option value="json">JSON Format</option>
                    <option value="html">HTML Format</option>
                    <option value="pdf">PDF Format</option>
                  </select>
                  
                  <button
                    type="button"
                    onClick={handleExport}
                    disabled={isExporting}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
                  >
                    <svg className="h-4 w-4 mr-1.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    {isExporting ? 'Exporting...' : 'Export'}
                  </button>
                  
                  <button
                    type="button"
                    onClick={handleShare}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
                  >
                    <svg className="h-4 w-4 mr-1.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                    </svg>
                    Share
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

LearningPlanManager.propTypes = {
  plan: PropTypes.object.isRequired,
  onUpdate: PropTypes.func,
  onDelete: PropTypes.func
};

export default LearningPlanManager;