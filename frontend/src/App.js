// src/App.js
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Spline from '@splinetool/react-spline';
import './App.css';
import SVGAnimatedLogo from './components/SVGAnimatedLogo';
import AnimatedUploadForm from './components/AnimatedUploadForm';
import AnimatedStatusDisplay from './components/AnimatedStatusDisplay';
import ErrorBoundary from './components/ErrorBoundary';
import GitHubFooter from './components/GitHubFooter';

function App() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [originalFile, setOriginalFile] = useState(null);

  // Smart API URL configuration (consistent with components)
  const API_BASE_URL = useMemo(() => {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0';
    
    if (process.env.REACT_APP_API_BASE_URL) {
      return process.env.REACT_APP_API_BASE_URL;
    } else if (isDevelopment || isLocalhost) {
      return 'http://localhost:5001';
    } else {
      return 'https://api.capvid.app';
    }
  }, []);

  const fetchStatus = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/status/${id}`);
      
      if (response.status === 404) {
        // Job not found or expired, stop polling
        console.log('Job not found or expired, stopping status polling');
        setError('Job expired or not found. Please try uploading again.');
        return;
      }
      
      const data = await response.json();
      
      if (response.ok) {
        setStatus(data);
      } else {
        setError(data.error || 'Failed to fetch status');
      }
    } catch (err) {
      console.error('Status fetch error:', err);
      setError(err.message || 'Network error. Please try again.');
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    let interval;
    if (jobId && status?.status !== 'completed' && status?.status !== 'failed' && status?.status !== 'completed_srt_only' && !error) {
      interval = setInterval(() => {
        fetchStatus(jobId);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, status, error, fetchStatus]);

  // Cleanup on component unmount or page refresh
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (jobId) {
        // Send cleanup request
        navigator.sendBeacon(`${API_BASE_URL}/cleanup/${jobId}`, '');
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Cleanup when component unmounts
      if (jobId) {
        fetch(`${API_BASE_URL}/cleanup/${jobId}`, { method: 'POST' })
          .catch(() => {}); // Ignore errors
      }
    };
  }, [jobId, API_BASE_URL]);

  const handleUploadSuccess = (id, file) => {
    setJobId(id);
    setOriginalFile(file);
    setError(null);
  };

  const handleUploadError = (errorMessage) => {
    // Ensure we always set a string error message, or null for clearing
    if (!errorMessage || errorMessage === '') {
      setError(null);
      return;
    }
    
    const message = typeof errorMessage === 'string' ? errorMessage : 
                   errorMessage?.message || 
                   'An unknown error occurred';
    setError(message);
  };

  const handleReset = async () => {
    // Cleanup current job before reset
    if (jobId) {
      try {
        await fetch(`${API_BASE_URL}/cleanup/${jobId}`, { method: 'POST' });
      } catch (err) {
        console.log('Cleanup failed:', err);
      }
    }
    
    setJobId(null);
    setStatus(null);
    setError(null);
    setOriginalFile(null);
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Spline 3D Background */}
      <div className="absolute inset-0 z-0">
        <Spline scene="https://prod.spline.design/y-a25jUyL3qY3NA7/scene.splinecode" />
      </div>
      
      {/* Main Content Layout - Responsive */}
      <div className="relative z-10 min-h-screen flex flex-col lg:flex-row">
        <ErrorBoundary>
          {/* Logo and Text Section */}
          <div className="flex-1 flex flex-col justify-center items-center 
                         px-4 py-8 lg:pl-28 lg:pr-8 lg:py-0
                         min-h-[40vh] lg:min-h-screen">
            <div className="w-full max-w-6xl flex flex-col items-center lg:items-start
                           text-center lg:text-left">
              {/* SVG Animated Logo */}
              <SVGAnimatedLogo className="mb-4 w-full max-w-lg lg:max-w-none" />
              
              <p 
                className="text-lg sm:text-xl md:text-2xl text-gray-200 opacity-90 
                          leading-relaxed px-4 lg:px-0"
                style={{ fontFamily: 'Urbanist, sans-serif' }}
              >
                AI based video captioning service
              </p>
            </div>
          </div>
          
          {/* Upload Form or Status Display Section */}
          <div className="flex-1 flex flex-col justify-center items-center 
                         px-4 py-8 lg:pr-16 lg:pl-8 lg:py-0
                         min-h-[60vh] lg:min-h-screen">
            <div className="w-full max-w-md">
              {!jobId ? (
                <AnimatedUploadForm onSuccess={handleUploadSuccess} onError={handleUploadError} />
              ) : (
                <AnimatedStatusDisplay 
                  status={status} 
                  error={error} 
                  onReset={handleReset}
                  jobId={jobId}
                  originalFile={originalFile}
                />
              )}
            </div>
          </div>
        </ErrorBoundary>
      </div>
      
      {/* GitHub Footer */}
      <GitHubFooter />
    </div>
  );
}

export default App;