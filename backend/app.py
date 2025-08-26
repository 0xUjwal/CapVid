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
import glob

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure CORS for production and development
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

# Storage configuration optimized for 4GB server
TEMP_STORAGE_LIMIT = 200 * 1024 * 1024  # 200MB limit
TEMP_BASE_DIR = tempfile.mkdtemp(prefix='capvid_')
UPLOAD_FOLDER = os.path.join(TEMP_BASE_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(TEMP_BASE_DIR, 'processed')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Thread-safe job management with extended retention
job_status = {}
file_timestamps = {}
download_timestamps = {}
processing_lock = threading.Lock()

# Global model to avoid reloading
whisper_model = None
model_load_lock = threading.Lock()

@app.route("/")
def home():
    """Root endpoint to confirm API is running"""
    return jsonify({"message": "🚀 CapVid API is running!"})

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
    """Conservative cleanup - only remove very old completed jobs"""
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(hours=6)  # Increased to 6 hours
    download_cutoff_time = current_time - timedelta(hours=2)  # Keep downloaded files for 2 hours
    
    total_size = get_directory_size(TEMP_BASE_DIR)
    files_to_remove = []
    
    with processing_lock:
        # Only remove very old completed jobs
        for job_id, timestamp in list(file_timestamps.items()):
            if timestamp < cutoff_time:
                status = job_status.get(job_id, {}).get('status')
                if status in ['completed', 'failed', 'completed_srt_only']:
                    files_to_remove.append(job_id)
        
        # If still over limit, remove old downloaded files
        if total_size > TEMP_STORAGE_LIMIT and len(files_to_remove) < 3:
            for job_id, download_time in list(download_timestamps.items()):
                if download_time < download_cutoff_time:
                    status = job_status.get(job_id, {}).get('status')
                    if status in ['completed', 'failed', 'completed_srt_only'] and job_id not in files_to_remove:
                        files_to_remove.append(job_id)
                        if len(files_to_remove) >= 5:  # Limit cleanup batch size
                            break
    
    # Remove identified files
    removed_count = 0
    for job_id in files_to_remove:
        try:
            cleanup_job_files(job_id)
            removed_count += 1
        except Exception as e:
            logger.error(f"Error cleaning up job {job_id}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleanup completed: removed {removed_count} jobs")

def cleanup_job_files(job_id):
    """Remove all files associated with a job"""
    try:
        with processing_lock:
            # Remove from tracking dictionaries
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
    """Run cleanup every 2 hours - very conservative"""
    while True:
        time.sleep(7200)  # 2 hours
        try:
            current_usage = get_directory_size(TEMP_BASE_DIR)
            usage_percentage = (current_usage / TEMP_STORAGE_LIMIT) * 100
            
            # Only cleanup if over 80% capacity
            if usage_percentage > 80:
                logger.info(f"Storage usage at {usage_percentage:.1f}%, running cleanup")
                cleanup_old_files()
            else:
                logger.info(f"Storage usage at {usage_percentage:.1f}%, skipping cleanup")
                
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

def load_whisper_model():
    """Load Whisper model with memory optimization for 4GB server"""
    global whisper_model
    
    with model_load_lock:
        if whisper_model is not None:
            return whisper_model
        
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            logger.info(f"Available memory: {available_gb:.1f}GB")
            
            # Conservative model selection for 4GB server
            if available_gb < 1.0:
                model_name = "tiny"
                logger.info("Using tiny model due to memory constraints")
            else:
                model_name = "base"
                logger.info("Using base model")
            
            logger.info(f"Attempting to load Whisper model: {model_name}")
            whisper_model = whisper.load_model(model_name)
            logger.info(f"Successfully loaded Whisper model: {model_name}")
            
            return whisper_model
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            try:
                logger.info("Falling back to tiny model")
                whisper_model = whisper.load_model("tiny")
                logger.info("Successfully loaded tiny model as fallback")
                return whisper_model
            except Exception as fallback_error:
                logger.error(f"Failed to load fallback model: {fallback_error}")
                raise

def process_video_task(job_id, filepath, filename):
    """Process video with enhanced error handling and status persistence"""
    try:
        logger.info(f"Starting video processing for job {job_id}")
        
        # Log memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage before processing: {memory.used / 1024 / 1024:.1f}MB")
        
        with processing_lock:
            job_status[job_id] = {'status': 'transcribing', 'filename': filename}

        # Load model
        model = load_whisper_model()
        logger.info(f"Starting transcription")
        
        try:
            result = model.transcribe(
                filepath,
                language=None,
                task="transcribe",
                verbose=False,
                word_timestamps=True,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            if not result or 'segments' not in result or not result['segments']:
                raise Exception("No speech detected in the video")
                
        except Exception as transcribe_error:
            logger.error(f"Transcription failed for job {job_id}: {transcribe_error}")
            with processing_lock:
                job_status[job_id] = {
                    'status': 'failed',
                    'filename': filename,
                    'error': f'Transcription failed: {str(transcribe_error)}'
                }
            return

        memory = psutil.virtual_memory()
        logger.info(f"Memory usage after transcription: {memory.used / 1024 / 1024:.1f}MB")

        with processing_lock:
            job_status[job_id] = {'status': 'generating_captions', 'filename': filename}
        
        srt_path = os.path.join(PROCESSED_FOLDER, f"{job_id}_captions.srt")
        name, ext = os.path.splitext(filename)
        output_video_filename = f"{job_id}_with_subtitles{ext}"
        output_video_path = os.path.join(PROCESSED_FOLDER, output_video_filename)

        generate_srt(result["segments"], srt_path)
        
        with processing_lock:
            job_status[job_id] = {'status': 'embedding_subtitles', 'filename': filename}
        
        try:
            overlay_subtitles(filepath, srt_path, output_video_path)
            
            if os.path.exists(output_video_path):
                logger.info(f"Video processing completed successfully for job {job_id}")
                with processing_lock:
                    job_status[job_id] = {
                        'status': 'completed',
                        'filename': filename,
                        'download_url': f"/download/{output_video_filename}",
                        'srt_url': f"/download_srt/{job_id}_captions.srt"
                    }
                
                # Remove original upload file to save space
                try:
                    os.remove(filepath)
                    logger.info(f"Removed original upload file: {filepath}")
                except Exception as e:
                    logger.error(f"Could not remove upload file: {e}")
            else:
                with processing_lock:
                    job_status[job_id] = {
                        'status': 'completed_srt_only',
                        'filename': filename,
                        'error': 'Output video file was not created, but SRT file is available',
                        'srt_url': f"/download_srt/{job_id}_captions.srt"
                    }
        except Exception as subtitle_error:
            logger.error(f"Failed to embed subtitles for job {job_id}: {str(subtitle_error)}")
            with processing_lock:
                job_status[job_id] = {
                    'status': 'completed_srt_only',
                    'filename': filename,
                    'error': f'Failed to embed subtitles: {str(subtitle_error)}',
                    'srt_url': f"/download_srt/{job_id}_captions.srt"
                }
        
        # Force garbage collection
        gc.collect()
            
    except Exception as e:
        logger.error(f"Video processing failed for job {job_id}: {str(e)}")
        with processing_lock:
            job_status[job_id] = {
                'status': 'failed',
                'filename': filename,
                'error': str(e)
            }

@app.route('/upload', methods=['POST'])
def upload_video():
    """Upload video with enhanced validation"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']
    if video.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # Check file size (limit to 100MB per file)
    if request.content_length and request.content_length > 100 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 100MB.'}), 400

    # Check storage space
    current_storage = get_directory_size(TEMP_BASE_DIR)
    estimated_size = request.content_length or 0
    
    if current_storage + estimated_size > TEMP_STORAGE_LIMIT:
        cleanup_old_files()
        current_storage = get_directory_size(TEMP_BASE_DIR)
        
        if current_storage + estimated_size > TEMP_STORAGE_LIMIT:
            return jsonify({'error': 'Server storage full. Please try again in a few minutes.'}), 507

    job_id = str(uuid.uuid4())
    filename = f"{job_id}_{video.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        video.save(filepath)
        
        with processing_lock:
            file_timestamps[job_id] = datetime.now()
            job_status[job_id] = {'status': 'uploaded', 'filename': video.filename}
        
        # Start processing in background thread
        thread = threading.Thread(target=process_video_task, args=(job_id, filepath, video.filename))
        thread.daemon = True
        thread.start()

        logger.info(f"Upload successful for job {job_id}")
        return jsonify({'job_id': job_id}), 202
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status with recovery capability"""
    with processing_lock:
        if job_id not in job_status:
            logger.warning(f"Job {job_id} not found in status dictionary")
            
            # Try to recover status from existing files
            upload_pattern = os.path.join(UPLOAD_FOLDER, f"{job_id}_*")
            processed_pattern = os.path.join(PROCESSED_FOLDER, f"{job_id}_*")
            
            upload_files = glob.glob(upload_pattern)
            processed_files = glob.glob(processed_pattern)
            
            if upload_files or processed_files:
                logger.info(f"Recovering status for job {job_id}")
                
                if processed_files:
                    video_files = [f for f in processed_files if 'with_subtitles' in f]
                    srt_files = [f for f in processed_files if 'captions.srt' in f]
                    
                    if video_files:
                        output_filename = os.path.basename(video_files[0])
                        job_status[job_id] = {
                            'status': 'completed',
                            'filename': 'recovered_file',
                            'download_url': f"/download/{output_filename}",
                            'srt_url': f"/download_srt/{job_id}_captions.srt" if srt_files else None
                        }
                    elif srt_files:
                        job_status[job_id] = {
                            'status': 'completed_srt_only',
                            'filename': 'recovered_file',
                            'srt_url': f"/download_srt/{job_id}_captions.srt"
                        }
                elif upload_files:
                    job_status[job_id] = {
                        'status': 'processing',
                        'filename': 'recovered_file'
                    }
                
                file_timestamps[job_id] = datetime.now()
                status_info = job_status[job_id].copy()
                return jsonify(status_info)
            
            return jsonify({'error': 'Job not found or expired'}), 404
        
        status_info = job_status[job_id].copy()
        logger.debug(f"Status check for job {job_id}: {status_info.get('status', 'unknown')}")
        return jsonify(status_info)

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download processed video with tracking"""
    path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(path):
        return jsonify({'error': 'File not found or expired'}), 404
    
    # Track download to prevent immediate cleanup
    job_id = filename.split('_')[0]
    with processing_lock:
        download_timestamps[job_id] = datetime.now()
        if job_id in job_status:
            original_filename = job_status[job_id].get('filename', 'video')
        else:
            original_filename = 'video'
    
    # Generate CapVid filename
    original_name_without_ext = os.path.splitext(original_filename)[0]
    original_extension = filename.split('.')[-1]
    capvid_filename = f"CapVid-{original_name_without_ext}.{original_extension}"
    
    logger.info(f"File downloaded: {filename} -> {capvid_filename}")
    
    response = send_from_directory(
        app.config['PROCESSED_FOLDER'], 
        filename, 
        as_attachment=True,
        download_name=capvid_filename
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/download_srt/<filename>', methods=['GET'])
def download_srt(filename):
    """Download SRT file with tracking"""
    path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(path):
        return jsonify({'error': 'SRT file not found or expired'}), 404
    
    # Track download
    job_id = filename.split('_')[0]
    with processing_lock:
        download_timestamps[job_id] = datetime.now()
    
    logger.info(f"SRT file downloaded: {filename}")
    
    response = send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

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
        'downloaded_jobs': downloaded_jobs
    })

@app.route('/system_info', methods=['GET'])
def system_info():
    """Get system and model information"""
    memory = psutil.virtual_memory()
    
    return jsonify({
        'whisper_models': ["tiny", "base"],
        'current_model': 'adaptive (tiny/base based on memory)',
        'temp_storage_mb': round(TEMP_STORAGE_LIMIT / 1024 / 1024, 2),
        'memory_total_gb': round(memory.total / (1024**3), 1),
        'memory_available_gb': round(memory.available / (1024**3), 1),
        'memory_used_gb': round(memory.used / (1024**3), 1),
        'features': [
            'Auto language detection',
            'Word-level timestamps',
            'Enhanced accuracy settings',
            'Conservative cleanup (6+ hours)',
            'Status recovery capability',
            'Download tracking',
            'Adaptive model selection'
        ]
    })

# Cleanup on app shutdown
import atexit

def cleanup_on_exit():
    """Clean up temporary directory on app shutdown"""
    try:
        shutil.rmtree(TEMP_BASE_DIR)
        logger.info(f"Cleaned up temporary directory: {TEMP_BASE_DIR}")
    except:
        pass

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Temporary storage directory: {TEMP_BASE_DIR}")
    logger.info(f"Storage limit: {TEMP_STORAGE_LIMIT / 1024 / 1024:.1f}MB")
    
    app.run(host=host, port=port, debug=debug)