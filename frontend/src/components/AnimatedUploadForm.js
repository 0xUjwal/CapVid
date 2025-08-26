import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

const AnimatedUploadForm = ({ onSuccess, onError }) => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [videoPreview, setVideoPreview] = useState(null);
  const fileInputRef = useRef(null);

  // Smart API URL configuration for development and production
  const API_BASE_URL = useMemo(() => {
    // Check if we're in development mode
    const isDevelopment = process.env.NODE_ENV === 'development';
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0';
    
    // Priority order for API URL selection:
    // 1. Environment variable (explicit override)
    // 2. Development mode detection
    // 3. Localhost detection
    // 4. Production default
    
    let apiUrl;
    
    if (process.env.REACT_APP_API_BASE_URL) {
      // Use explicitly set environment variable
      apiUrl = process.env.REACT_APP_API_BASE_URL;
    } else if (isDevelopment || isLocalhost) {
      // Development mode or localhost - use local backend
      apiUrl = 'http://localhost:5001';
    } else {
      // Production mode - use production API
      apiUrl = 'https://api.capvid.app';
    }
    
    console.log('🌐 Environment Detection:', {
      NODE_ENV: process.env.NODE_ENV,
      hostname: window.location.hostname,
      isDevelopment,
      isLocalhost,
      envVar: process.env.REACT_APP_API_BASE_URL,
      selectedURL: apiUrl
    });
    
    return apiUrl;
  }, []);

  // File validation constants
  const FILE_CONSTRAINTS = useMemo(() => ({
    allowedTypes: [
      'video/mp4', 
      'video/quicktime', 
      'video/x-msvideo', 
      'video/x-matroska', 
      'video/webm'
    ],
    maxSize: 250 * 1024 * 1024, // 250MB
    allowedExtensions: ['MP4', 'MOV', 'AVI', 'MKV', 'WEBM']
  }), []);

  // Test API connectivity on component mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        console.log('🔄 Testing API connection to:', API_BASE_URL);
        const response = await fetch(`${API_BASE_URL}/storage_info`, {
          method: 'GET',
          signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ API connected successfully:', data);
        } else {
          console.warn('⚠️ API responded but with error:', response.status);
        }
      } catch (error) {
        console.error('❌ API connection failed:', error.message);
        
        // If production API fails and we're not explicitly in development,
        // suggest alternative
        if (API_BASE_URL.includes('api.capvid.app')) {
          console.log('💡 Tip: If running locally, set REACT_APP_API_BASE_URL=http://localhost:5001');
        }
      }
    };

    testConnection();
  }, [API_BASE_URL]);

  // Cleanup video preview on unmount
  useEffect(() => {
    return () => {
      if (videoPreview) {
        URL.revokeObjectURL(videoPreview);
      }
    };
  }, [videoPreview]);

  // Auto-generate filename from uploaded file
  useEffect(() => {
    if (file && !fileName) {
      const nameWithoutExtension = file.name.replace(/\.[^/.]+$/, '');
      setFileName(nameWithoutExtension);
    }
  }, [file, fileName]);

  const validateAndSetFile = useCallback((file) => {
    // Reset previous errors
    onError('');
    
    // Check file type
    if (!FILE_CONSTRAINTS.allowedTypes.includes(file.type)) {
      onError('Invalid file type. Please upload MP4, MOV, AVI, MKV, or WebM video.');
      return;
    }
    
    // Check file size
    if (file.size > FILE_CONSTRAINTS.maxSize) {
      onError('File too large. Maximum size is 250MB.');
      return;
    }

    // Check if file is not corrupted (basic check)
    if (file.size === 0) {
      onError('File appears to be empty or corrupted.');
      return;
    }
    
    setFile(file);
    
    // Create video preview URL
    const previewURL = URL.createObjectURL(file);
    setVideoPreview(previewURL);
  }, [FILE_CONSTRAINTS, onError]);

  const handleFileChange = useCallback((e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  }, [validateAndSetFile]);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  }, [validateAndSetFile]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    
    // Validation
    if (!file) {
      onError('Please select a video file');
      return;
    }
    
    if (!fileName.trim()) {
      onError('Please enter a filename');
      return;
    }

    // Sanitize filename
    const sanitizedFileName = fileName.trim().replace(/[^a-zA-Z0-9\-_\s]/g, '');
    if (!sanitizedFileName) {
      onError('Please enter a valid filename (letters, numbers, spaces, hyphens, and underscores only)');
      return;
    }

    const formData = new FormData();
    formData.append('video', file);
    formData.append('filename', sanitizedFileName);

    const uploadUrl = `${API_BASE_URL}/upload`;
    console.log('📤 Uploading to:', uploadUrl);

    try {
      setUploading(true);
      setUploadProgress(0);
      onError(''); // Clear any previous errors

      // Create AbortController for request cancellation
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout

      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {
          // Don't set Content-Type for FormData, let browser set it with boundary
        },
        // Add retry logic
        retry: {
          retries: 2,
          retryDelay: 1000
        }
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorText;
        try {
          const errorData = await response.json();
          errorText = errorData.error || `Upload failed: ${response.status} ${response.statusText}`;
        } catch {
          errorText = await response.text() || `Upload failed: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorText);
      }

      const result = await response.json();
      console.log('✅ Upload successful:', result);
      
      // Validate response structure
      if (!result.job_id) {
        throw new Error('Invalid response: missing job_id');
      }
      
      // Cleanup preview URL
      if (videoPreview) {
        URL.revokeObjectURL(videoPreview);
        setVideoPreview(null);
      }
      
      // Reset form
      setFile(null);
      setFileName('');
      
      onSuccess(result.job_id, file);
      
    } catch (error) {
      console.error('❌ Upload failed:', error);
      
      if (error.name === 'AbortError') {
        onError('Upload timed out. Please try again with a smaller file.');
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        onError('Network error. Please check your connection and ensure the backend is running.');
      } else if (error.message.includes('507')) {
        onError('Server storage is full. Please try again later.');
      } else if (error.message.includes('413')) {
        onError('File too large. Please use a smaller file.');
      } else if (error.message.includes('400')) {
        onError('Invalid file format. Please use MP4, MOV, AVI, MKV, or WebM.');
      } else {
        onError(`Upload failed: ${error.message}`);
      }
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [file, fileName, API_BASE_URL, videoPreview, onSuccess, onError]);

  const formatFileSize = useCallback((bytes) => {
    if (bytes === 0) return '0 bytes';
    const k = 1024;
    const sizes = ['bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }, []);

  const clearFile = useCallback((e) => {
    if (e) {
      e.stopPropagation();
    }
    setFile(null);
    setFileName('');
    if (videoPreview) {
      URL.revokeObjectURL(videoPreview);
      setVideoPreview(null);
    }
    onError(''); // Clear any error messages
  }, [videoPreview, onError]);

  // Handle filename input change
  const handleFileNameChange = useCallback((e) => {
    setFileName(e.target.value);
  }, []);

  // Memoized drag zone classes
  const dragZoneClasses = useMemo(() => {
    const baseClasses = "relative bg-white bg-opacity-10 backdrop-blur-md border-2 border-dashed rounded-3xl p-8 text-center transition-all duration-300 cursor-pointer";
    
    if (dragActive) {
      return `${baseClasses} border-purple-400 bg-purple-900 bg-opacity-30 scale-105`;
    } else if (file) {
      return `${baseClasses} border-green-400 bg-green-900 bg-opacity-30`;
    } else {
      return `${baseClasses} border-gray-300 border-opacity-50 hover:border-purple-400 hover:bg-purple-900 hover:bg-opacity-20`;
    }
  }, [dragActive, file]);

  // Memoized button classes
  const buttonClasses = useMemo(() => {
    const baseClasses = "w-full mt-6 py-4 px-6 rounded-2xl font-semibold text-lg transition-all duration-300";
    
    if (!file || uploading) {
      return `${baseClasses} bg-gray-600 bg-opacity-50 cursor-not-allowed text-gray-400`;
    } else {
      return `${baseClasses} bg-cyan-600 hover:bg-cyan-700 text-white hover:scale-105 shadow-lg hover:shadow-cyan-500/25`;
    }
  }, [file, uploading]);

  return (
    <div className="w-full">
      {/* Development Mode Indicator */}
      {(process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost') && (
        <div className="mb-4 p-3 bg-yellow-500 bg-opacity-20 border border-yellow-400 rounded-lg">
          <p className="text-sm text-yellow-200 text-center">
            🔧 Development Mode | API: {API_BASE_URL}
          </p>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="w-full">
        {/* Filename Input Field */}
        {file && (
          <div className="mb-6">
            <label 
              htmlFor="filename-input"
              className="block text-sm font-medium text-white mb-2"
              style={{ fontFamily: 'Urbanist, sans-serif' }}
            >
              Video Name
            </label>
            <input
              id="filename-input"
              type="text"
              value={fileName}
              onChange={handleFileNameChange}
              placeholder="Enter video name..."
              className="w-full px-4 py-3 bg-white bg-opacity-10 backdrop-blur-md border border-gray-300 border-opacity-30 rounded-2xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all duration-300"
              style={{ fontFamily: 'Urbanist, sans-serif' }}
              maxLength={100}
              required
            />
          </div>
        )}

        {/* File Upload Area */}
        <div 
          className={dragZoneClasses}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload video file"
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !file) {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
        >
          {!file ? (
            <div className="space-y-6">
              {/* Upload Icon */}
              <div className="flex justify-center mb-4" aria-hidden="true">
                <div className="w-24 h-24 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <svg 
                    className="w-12 h-12 text-white" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={1.5} 
                      d="M12 4v16m8-8H4" 
                    />
                  </svg>
                </div>
              </div>
              
              <div>
                <h3 
                  className="text-3xl font-semibold text-white mb-2"
                  style={{ fontFamily: 'Urbanist, sans-serif' }}
                >
                  Upload Video
                </h3>
                <p 
                  className="text-gray-600 text-sm mb-4"
                  style={{ fontFamily: 'Urbanist, sans-serif' }}
                >
                  Drag and drop or click to browse
                </p>
              </div>

              {/* Supported Formats */}
              <div className="flex flex-wrap justify-center gap-2">
                {FILE_CONSTRAINTS.allowedExtensions.map((format) => (
                  <span 
                    key={format}
                    className="px-3 py-1 bg-white bg-opacity-20 text-black rounded-full text-xs font-medium"
                    style={{ fontFamily: 'Urbanist, sans-serif' }}
                  >
                    {format}
                  </span>
                ))}
              </div>

              <p 
                className="text-xs text-gray-400 mt-4"
                style={{ fontFamily: 'Urbanist, sans-serif' }}
              >
                Maximum file size: {formatFileSize(FILE_CONSTRAINTS.maxSize)}
              </p>

              <input
                ref={fileInputRef}
                data-testid="video-upload"
                accept={FILE_CONSTRAINTS.allowedTypes.join(',')}
                className="hidden"
                type="file"
                onChange={handleFileChange}
                aria-label="Select video file"
              />
            </div>
          ) : (
            /* File Selected View */
            <div className="space-y-4">
              <div className="text-green-400 text-4xl mb-4" aria-hidden="true">✓</div>
              <h3 
                className="text-xl font-semibold text-black break-words"
                style={{ fontFamily: 'Urbanist, sans-serif' }}
                title={file.name}
              >
                {file.name}
              </h3>
              <p 
                className="text-gray-600 text-sm"
                style={{ fontFamily: 'Urbanist, sans-serif' }}
              >
                {formatFileSize(file.size)}
              </p>
              
              {/* Video Preview */}
              {videoPreview && (
                <div className="mt-4">
                  <video 
                    src={videoPreview} 
                    controls 
                    className="w-full h-auto max-h-32 rounded-lg"
                    preload="metadata"
                    aria-label="Video preview"
                  />
                </div>
              )}

              <button
                type="button"
                onClick={clearFile}
                className="text-red-400 hover:text-red-300 text-sm underline focus:outline-none focus:ring-2 focus:ring-red-400 rounded"
                style={{ fontFamily: 'Urbanist, sans-serif' }}
                aria-label="Remove selected file"
              >
                Remove file
              </button>
            </div>
          )}
        </div>

        {/* Upload Progress */}
        {uploading && (
          <div className="mt-6" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={uploadProgress}>
            <div className="w-full bg-white bg-opacity-20 rounded-full h-2 mb-2">
              <div 
                className="bg-cyan-500 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p 
              className="text-center text-xs text-gray-600"
              style={{ fontFamily: 'Urbanist, sans-serif' }}
              aria-live="polite"
            >
              {uploadProgress < 100 ? `Uploading... ${uploadProgress}%` : 'Processing...'}
            </p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!file || uploading || !fileName.trim()}
          className={buttonClasses}
          style={{ fontFamily: 'Urbanist, sans-serif' }}
          aria-label={uploading ? 'Processing video' : 'Generate captions for video'}
        >
          {uploading ? 'Processing...' : 'Generate Captions'}
        </button>
      </form>
    </div>
  );
};

// PropTypes for better development experience
AnimatedUploadForm.propTypes = {
  onSuccess: PropTypes.func.isRequired,
  onError: PropTypes.func.isRequired,
};

export default AnimatedUploadForm;
