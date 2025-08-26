from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import threading
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from helpers import generate_srt, overlay_subtitles, check_ffmpeg_installation
import whisper
import gc
import psutil
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure CORS for Vercel frontend
CORS(app, 
     origins=[
         "https://capvid.app",
         "https://www.capvid.app",
         "http://localhost:3000",
         "https://localhost:3000"
     ],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True,
     max_age=3600
)

# Use system temporary directory with size limit
TEMP_STORAGE_LIMIT = 250 * 1024 * 1024  # 250MB in bytes
TEMP_BASE_DIR = tempfile.mkdtemp(prefix='capvid_')
UPLOAD_FOLDER = os.path.join(TEMP_BASE_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(TEMP_BASE_DIR, 'processed')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Thread-safe job management with longer retention
job_status = {}
file_timestamps = {}
download_timestamps = {}  # Track when files were first downloaded
processing_lock = threading.Lock()

# Global model to avoid reloading
whisper_model = None
model_load_lock = threading.Lock()

# Allowed video file extensions
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v', '.3gp', '.wmv'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def get_directory_size(directory):
    """Calculate total size of all files in directory"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Error calculating directory size: {e}")
    return total_size

def cleanup_old_files():
    """Remove files older than 4 hours or when storage limit is exceeded"""
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(hours=4)  # Increased to 4 hours retention
    download_cutoff_time = current_time - timedelta(hours=1)  # Keep downloaded files for 1 hour
    
    # Get current storage usage
    total_size = get_directory_size(TEMP_BASE_DIR)
    
    files_to_remove = []
    
    # Remove files older than 4 hours
    for job_id, timestamp in list(file_timestamps.items()):
        if timestamp < cutoff_time:
            files_to_remove.append(job_id)
    
    # Remove downloaded files older than 1 hour
    for job_id, download_time in list(download_timestamps.items()):
        if download_time < download_cutoff_time and job_id not in files_to_remove:
            files_to_remove.append(job_id)
    
    # If still over limit, remove oldest completed jobs first (but keep recently downloaded)
    if total_size > TEMP_STORAGE_LIMIT:
        with processing_lock:
            completed_jobs = []
            for job_id, status_info in job_status.items():
                if status_info.get('status') in ['completed', 'failed', 'completed_srt_only']:
                    if job_id in file_timestamps:
                        # Don't remove recently downloaded files unless absolutely necessary
                        if job_id not in download_timestamps or download_timestamps[job_id] < download_cutoff_time:
                            completed_jobs.append((job_id, file_timestamps[job_id]))
            
            # Sort by timestamp and remove oldest completed jobs
            completed_jobs.sort(key=lambda x: x[1])
            for job_id, _ in completed_jobs:
                if job_id not in files_to_remove:
                    files_to_remove.append(job_id)
                    # Check if we're under limit after adding this file
                    if get_directory_size(TEMP_BASE_DIR) < TEMP_STORAGE_LIMIT * 0.8:
                        break
    
    # Remove identified files
    for job_id in files_to_remove:
        cleanup_job_files(job_id)

def cleanup_job_files(job_id):
    """Remove all files associated with a job"""
    try:
        with processing_lock:
            # Remove from status tracking
            if job_id in job_status:
                logger.info(f"Removing job {job_id} from status tracking")
                del job_status[job_id]
            if job_id in file_timestamps:
                del file_timestamps[job_id]
            if job_id in download_timestamps:
                del download_timestamps[job_id]
        
        # Remove actual files
        for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    if filename.startswith(job_id):
                        filepath = os.path.join(folder, filename)
                        try:
                            os.remove(filepath)
                            logger.info(f"Removed file: {filepath}")
                        except Exception as e:
                            logger.error(f"Failed to remove {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up job {job_id}: {e}")

def periodic_cleanup():
    """Run cleanup every 30 minutes"""
    while True:
        time.sleep(1800)  # 30 minutes
        try:
            cleanup_old_files()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

def load_whisper_model():
    """Load Whisper model with memory optimization"""
    global whisper_model
    
    with model_load_lock:
        if whisper_model is not None:
            return whisper_model
        
        try:
            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            logger.info(f"Available memory: {available_gb:.1f}GB")
            
            if available_gb < 0.5:  # Less than 500MB available
                model_name = "tiny"
                logger.info("Using tiny model due to memory constraints")
            elif available_gb < 1.0:  # Less than 1GB available
                model_name = "base"
                logger.info("Using base model due to memory constraints")
            else:
                model_name = "small"
                logger.info("Using small model")
            
            logger.info(f"Loading Whisper model: {model_name}")
            whisper_model = whisper.load_model(model_name)
            logger.info(f"Successfully loaded Whisper model: {model_name}")
            
            return whisper_model
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Fallback to tiny model
            try:
                logger.info("Falling back to tiny model")
                whisper_model = whisper.load_model("tiny")
                logger.info("Successfully loaded tiny model as fallback")
                return whisper_model
            except Exception as fallback_error:
                logger.error(f"Failed to load fallback model: {fallback_error}")
                raise

def process_video_task(job_id, filepath, original_filename):
    """Process video file: transcribe and add subtitles"""
    try:
        logger.info(f"Starting video processing for job {job_id}")
        logger.info(f"Processing file: {filepath}")
        logger.info(f"File size: {os.path.getsize(filepath)} bytes")
        
        # Log memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage before processing: {memory.used / 1024 / 1024:.1f}MB")
        
        with processing_lock:
            job_status[job_id] = {'status': 'transcribing', 'filename': original_filename}

        # Load model
        model = load_whisper_model()
        logger.info("Starting transcription")
        
        # Enhanced transcription with better error handling
        try:
            result = model.transcribe(
                filepath,
                language=None,  # Auto-detect language
                task="transcribe",
                verbose=False,
                word_timestamps=True,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            # Validate transcription result
            if not result or 'segments' not in result or not result['segments']:
                raise Exception("No speech detected in the video or transcription failed")
            
            logger.info(f"Transcription completed. Found {len(result['segments'])} segments")
                
        except Exception as transcribe_error:
            logger.error(f"Transcription failed for job {job_id}: {transcribe_error}")
            with processing_lock:
                job_status[job_id] = {
                    'status': 'failed',
                    'filename': original_filename,
                    'error': f'Transcription failed: {str(transcribe_error)}'
                }
            return

        # Log memory after transcription
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage after transcription: {memory.used / 1024 / 1024:.1f}MB")

        with processing_lock:
            job_status[job_id] = {'status': 'generating_captions', 'filename': original_filename}
        
        # Generate SRT file
        srt_path = os.path.join(PROCESSED_FOLDER, f"{job_id}_captions.srt")
        
        # Create output video filename with subtitles
        name, ext = os.path.splitext(original_filename)
        output_video_filename = f"{job_id}_with_subtitles{ext}"
        output_video_path = os.path.join(PROCESSED_FOLDER, output_video_filename)

        # Generate SRT file
        try:
            generate_srt(result["segments"], srt_path)
            logger.info(f"SRT file generated: {srt_path}")
        except Exception as srt_error:
            logger.error(f"Failed to generate SRT for job {job_id}: {srt_error}")
            with processing_lock:
                job_status[job_id] = {
                    'status': 'failed',
                    'filename': original_filename,
                    'error': f'Failed to generate SRT file: {str(srt_error)}'
                }
            return
        
        with processing_lock:
            job_status[job_id] = {'status': 'embedding_subtitles', 'filename': original_filename}
        
        # Overlay subtitles on video
        try:
            overlay_subtitles(filepath, srt_path, output_video_path)
            
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                logger.info(f"Video processing completed successfully for job {job_id}")
                with processing_lock:
                    job_status[job_id] = {
                        'status': 'completed',
                        'filename': original_filename,
                        'download_url': f"/download/{output_video_filename}",
                        'srt_url': f"/download_srt/{job_id}_captions.srt"
                    }
                
                # Remove original upload file to save space AFTER successful processing
                try:
                    os.remove(filepath)
                    logger.info(f"Removed original upload file: {filepath}")
                except Exception as e:
                    logger.error(f"Could not remove upload file: {e}")
                    
            else:
                raise Exception("Output video file was not created or is empty")
                
        except Exception as subtitle_error:
            logger.error(f"Failed to embed subtitles for job {job_id}: {str(subtitle_error)}")
            with processing_lock:
                job_status[job_id] = {
                    'status': 'completed_srt_only',
                    'filename': original_filename,
                    'error': f'Failed to embed subtitles: {str(subtitle_error)}. SRT file is still available.',
                    'srt_url': f"/download_srt/{job_id}_captions.srt"
                }
        
        # Log final memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage after processing complete: {memory.used / 1024 / 1024:.1f}MB")
        
        # Force garbage collection
        gc.collect()
            
    except Exception as e:
        logger.error(f"Video processing failed for job {job_id}: {str(e)}")
        with processing_lock:
            job_status[job_id] = {
                'status': 'failed',
                'filename': original_filename,
                'error': str(e)
            }

@app.route('/upload', methods=['POST'])
def upload_video():
    """Handle video file upload and start processing"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']
    if video.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Validate file type
    if not allowed_file(video.filename):
        return jsonify({
            'error': f'Unsupported file type. Allowed formats: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    # Check file size (limit to 100MB per file)
    if request.content_length and request.content_length > 100 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 100MB per file.'}), 400

    # Check available storage space
    current_storage = get_directory_size(TEMP_BASE_DIR)
    estimated_size = request.content_length or 0
    
    if current_storage + estimated_size > TEMP_STORAGE_LIMIT:
        # Try cleanup first
        cleanup_old_files()
        current_storage = get_directory_size(TEMP_BASE_DIR)
        
        if current_storage + estimated_size > TEMP_STORAGE_LIMIT:
            return jsonify({'error': 'Temporary storage full. Please try again in a few minutes.'}), 507

    job_id = str(uuid.uuid4())
    filename = f"{job_id}_{video.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        video.save(filepath)
        
        with processing_lock:
            file_timestamps[job_id] = datetime.now()
            job_status[job_id] = {'status': 'uploaded', 'filename': video.filename}
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_video_task, 
            args=(job_id, filepath, video.filename),
            daemon=True
        )
        thread.start()

        logger.info(f"Upload successful for job {job_id}, file: {video.filename}")
        return jsonify({'job_id': job_id}), 202
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status for a job"""
    with processing_lock:
        if job_id not in job_status:
            logger.warning(f"Job {job_id} not found in status dictionary")
            return jsonify({'error': 'Job not found or expired'}), 404
        
        status_info = job_status[job_id].copy()  # Create a copy to avoid race conditions
        logger.debug(f"Status check for job {job_id}: {status_info.get('status', 'unknown')}")
        return jsonify(status_info)

@app.route('/file_exists/<filename>', methods=['GET'])
def check_file_exists(filename):
    """Check if a processed file still exists"""
    path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    exists = os.path.exists(path)
    
    if exists:
        file_size = os.path.getsize(path)
        return jsonify({
            'exists': True,
            'size_bytes': file_size,
            'size_mb': round(file_size / 1024 / 1024, 2)
        })
    else:
        return jsonify({'exists': False})

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download processed video file"""
    path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(path):
        logger.warning(f"Download requested for non-existent file: {filename}")
        return jsonify({'error': 'File not found or expired'}), 404
    
    # Extract job_id from filename
    job_id = filename.split('_')[0]
    
    # Track download timestamp to prevent immediate cleanup
    with processing_lock:
        download_timestamps[job_id] = datetime.now()
    
    # Get original filename from job status
    original_filename = "video"  # default fallback
    with processing_lock:
        if job_id in job_status and 'filename' in job_status[job_id]:
            original_filename = job_status[job_id]['filename']
    
    # Generate CapVid filename with original name
    original_name_without_ext = os.path.splitext(original_filename)[0]
    original_extension = filename.split('.')[-1]
    capvid_filename = f"CapVid-{original_name_without_ext}.{original_extension}"
    
    logger.info(f"Serving download: {filename} as {capvid_filename} for job {job_id}")
    
    try:
        response = send_from_directory(
            app.config['PROCESSED_FOLDER'], 
            filename, 
            as_attachment=True,
            download_name=capvid_filename
        )
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response
    except Exception as e:
        logger.error(f"Error serving download for {filename}: {e}")
        return jsonify({'error': 'Failed to serve file'}), 500

@app.route('/download_srt/<filename>', methods=['GET'])
def download_srt(filename):
    """Download SRT subtitle file"""
    path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(path):
        logger.warning(f"SRT download requested for non-existent file: {filename}")
        return jsonify({'error': 'SRT file not found or expired'}), 404
    
    # Extract job_id from filename
    job_id = filename.split('_')[0]
    
    # Track download timestamp to prevent immediate cleanup
    with processing_lock:
        download_timestamps[job_id] = datetime.now()
    
    logger.info(f"Serving SRT download: {filename} for job {job_id}")
    
    try:
        response = send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response
    except Exception as e:
        logger.error(f"Error serving SRT download for {filename}: {e}")
        return jsonify({'error': 'Failed to serve SRT file'}), 500

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_job(job_id):
    """Manual cleanup endpoint for specific job - only cleanup after completion"""
    with processing_lock:
        if job_id in job_status:
            status = job_status[job_id].get('status')
            if status not in ['completed', 'failed', 'completed_srt_only']:
                return jsonify({'error': 'Cannot cleanup job that is still processing'}), 400
    
    cleanup_job_files(job_id)
    logger.info(f"Manual cleanup performed for job {job_id}")
    return jsonify({'message': f'Job {job_id} cleaned up successfully'}), 200

@app.route('/storage_info', methods=['GET'])
def storage_info():
    """Get current storage usage information"""
    current_usage = get_directory_size(TEMP_BASE_DIR)
    with processing_lock:
        active_jobs = len(job_status)
        downloaded_jobs = len(download_timestamps)
    
    return jsonify({
        'current_usage_mb': round(current_usage / 1024 / 1024, 2),
        'limit_mb': round(TEMP_STORAGE_LIMIT / 1024 / 1024, 2),
        'usage_percentage': round((current_usage / TEMP_STORAGE_LIMIT) * 100, 2),
        'active_jobs': active_jobs,
        'downloaded_jobs': downloaded_jobs,
        'temp_directory': TEMP_BASE_DIR
    })

@app.route('/system_info', methods=['GET'])
def system_info():
    """Get system and model information"""
    # Get memory info
    memory = psutil.virtual_memory()
    
    # Check FFmpeg status
    ffmpeg_status = check_ffmpeg_installation()
    
    return jsonify({
        'whisper_models': ["tiny", "base", "small"],
        'current_model': 'adaptive (tiny/base/small based on memory)',
        'temp_storage_mb': round(TEMP_STORAGE_LIMIT / 1024 / 1024, 2),
        'memory_total_gb': round(memory.total / (1024**3), 1),
        'memory_available_gb': round(memory.available / (1024**3), 1),
        'memory_used_gb': round(memory.used / (1024**3), 1),
        'ffmpeg_installed': ffmpeg_status,
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'features': [
            'Auto language detection',
            'Word-level timestamps',
            'Enhanced accuracy settings',
            'Automatic cleanup',
            'Temporary storage management',
            'Adaptive model selection',
            'Extended job retention (4 hours)',
            'Download protection (1 hour after download)',
            'Cross-platform subtitle embedding',
            'File type validation'
        ]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        memory = psutil.virtual_memory()
        storage_usage = get_directory_size(TEMP_BASE_DIR)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'memory_available_gb': round(memory.available / (1024**3), 1),
            'storage_usage_mb': round(storage_usage / 1024 / 1024, 2),
            'temp_directory': TEMP_BASE_DIR,
            'ffmpeg_available': check_ffmpeg_installation()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Cleanup on app shutdown
import atexit

def cleanup_on_exit():
    """Clean up temporary directory on app shutdown"""
    try:
        shutil.rmtree(TEMP_BASE_DIR)
        logger.info(f"Cleaned up temporary directory: {TEMP_BASE_DIR}")
    except Exception as e:
        logger.error(f"Failed to cleanup on exit: {e}")

atexit.register(cleanup_on_exit)

def startup_checks():
    """Perform startup checks"""
    logger.info("Performing startup checks...")
    logger.info(f"Temporary storage directory: {TEMP_BASE_DIR}")
    logger.info(f"Storage limit: {TEMP_STORAGE_LIMIT / 1024 / 1024:.1f}MB")
    
    if not check_ffmpeg_installation():
        logger.warning("FFmpeg not found! Video processing will fail.")
    else:
        logger.info("FFmpeg is available")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting CapVid Backend on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    # Perform startup checks
    startup_checks()
    
    app.run(host=host, port=port, debug=debug)