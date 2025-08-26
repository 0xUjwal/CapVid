import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def generate_srt(segments, srt_path):
    """Generate SRT subtitle file from Whisper segments with shorter text chunks"""
    try:
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            subtitle_index = 1
            
            for segment in segments:
                text = segment['text'].strip()
                
                # Skip empty segments
                if not text:
                    continue
                
                # Split long text into shorter chunks (max 6-8 words per subtitle)
                words = text.split()
                max_words_per_subtitle = 7
                
                # If segment has few words, keep as is
                if len(words) <= max_words_per_subtitle:
                    start_time = format_time(segment['start'])
                    end_time = format_time(segment['end'])
                    
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{text}\n\n")
                    subtitle_index += 1
                else:
                    # Split into smaller chunks
                    total_duration = segment['end'] - segment['start']
                    chunks = [words[i:i + max_words_per_subtitle] for i in range(0, len(words), max_words_per_subtitle)]
                    chunk_duration = total_duration / len(chunks)
                    
                    for i, chunk in enumerate(chunks):
                        chunk_text = ' '.join(chunk)
                        chunk_start = segment['start'] + (i * chunk_duration)
                        chunk_end = min(segment['start'] + ((i + 1) * chunk_duration), segment['end'])
                        
                        start_time = format_time(chunk_start)
                        end_time = format_time(chunk_end)
                        
                        srt_file.write(f"{subtitle_index}\n")
                        srt_file.write(f"{start_time} --> {end_time}\n")
                        srt_file.write(f"{chunk_text}\n\n")
                        subtitle_index += 1
        
        logger.info(f"SRT file generated successfully: {srt_path}")
        
        # Verify file was created and has content
        if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
            raise Exception("SRT file was not created or is empty")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate SRT file: {e}")
        raise Exception(f"Failed to generate SRT file: {str(e)}")

def format_time(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    # Handle negative values
    if seconds < 0:
        seconds = 0
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    
    # Ensure values are within valid ranges
    hours = min(hours, 99)  # SRT format supports max 99 hours
    minutes = min(minutes, 59)
    secs = min(secs, 59)
    millis = min(millis, 999)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def overlay_subtitles(input_path, srt_path, output_path):
    """Overlay subtitles on video using FFmpeg with cross-platform compatibility"""
    try:
        # Convert to absolute paths
        input_path = os.path.abspath(input_path)
        srt_path = os.path.abspath(srt_path)
        output_path = os.path.abspath(output_path)
        
        # Validate input files exist
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video file not found: {input_path}")
        if not os.path.exists(srt_path):
            raise FileNotFoundError(f"SRT file not found: {srt_path}")
        
        logger.info(f"Processing video: {input_path}")
        logger.info(f"Using SRT file: {srt_path}")
        logger.info(f"Output will be: {output_path}")
        
        # Validate input file has content
        if os.path.getsize(input_path) == 0:
            raise Exception("Input video file is empty")
        if os.path.getsize(srt_path) == 0:
            raise Exception("SRT file is empty")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Cross-platform path handling for FFmpeg subtitle filter
        if os.name == 'nt':  # Windows
            # Windows: Use forward slashes and escape colons
            srt_filter_path = srt_path.replace("\\", "/").replace(":", "\\:")
        else:  # Linux/macOS
            # Unix: Escape single quotes in path
            srt_filter_path = srt_path.replace("'", "'\\''")
        
        # Build FFmpeg command with optimized settings and better subtitle positioning
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file without asking
            '-i', input_path,  # Input video
            '-vf', f"subtitles='{srt_filter_path}':force_style='FontSize=13,PrimaryColour=&H00ffffff,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=18,MarginL=20,MarginR=20,Alignment=2,FontName=Arial Bold,Bold=1'",
            '-c:a', 'copy',  # Copy audio stream without re-encoding
            '-c:v', 'libx264',  # Use H.264 video codec
            '-preset', 'medium',  # Balance between speed and compressionwrap
            '-crf', '23',  # Constant Rate Factor - good quality
            '-movflags', '+faststart',  # Optimize for web streaming
            '-max_muxing_queue_size', '9999',  # Handle large files
            output_path
        ]
        
        logger.info("Starting FFmpeg subtitle embedding...")
        logger.debug(f"FFmpeg command: {' '.join(command)}")
        
        # Run FFmpeg with timeout and capture output
        try:
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=os.path.dirname(output_path)  # Set working directory
            )
            
            logger.info("FFmpeg completed successfully")
            if result.stdout:
                logger.debug(f"FFmpeg stdout: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg operation timed out (10 minutes). Video may be too large or complex."
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except subprocess.CalledProcessError as e:
            # Log detailed error information
            error_msg = f"FFmpeg failed with return code {e.returncode}"
            if e.stderr:
                logger.error(f"FFmpeg stderr: {e.stderr}")
                error_msg += f": {e.stderr}"
            if e.stdout:
                logger.error(f"FFmpeg stdout: {e.stdout}")
            
            # Provide more specific error messages
            if "No such file or directory" in str(e.stderr):
                error_msg = "FFmpeg could not access the input files. Check file paths."
            elif "Invalid data found" in str(e.stderr):
                error_msg = "Input video file appears to be corrupted or invalid format."
            elif "Permission denied" in str(e.stderr):
                error_msg = "Permission denied accessing files. Check file permissions."
            elif "No space left on device" in str(e.stderr):
                error_msg = "Not enough disk space to create output video."
                
            raise Exception(error_msg)
        
        # Verify output file was created and has reasonable content
        if not os.path.exists(output_path):
            raise Exception("Output video file was not created by FFmpeg")
        
        output_size = os.path.getsize(output_path)
        if output_size == 0:
            raise Exception("Output video file is empty")
        
        # Check if output file is significantly smaller than input (potential issue)
        input_size = os.path.getsize(input_path)
        if output_size < input_size * 0.1:  # Less than 10% of original size
            logger.warning(f"Output file ({output_size} bytes) is much smaller than input ({input_size} bytes)")
        
        logger.info(f"Video processing completed successfully")
        logger.info(f"Input size: {input_size} bytes, Output size: {output_size} bytes")
        
        return True
        
    except FileNotFoundError as e:
        if "ffmpeg" in str(e).lower():
            error_msg = "FFmpeg not found. Please ensure FFmpeg is installed and in PATH."
            logger.error(error_msg)
            raise Exception(error_msg)
        else:
            logger.error(f"File not found: {e}")
            raise Exception(str(e))
            
    except Exception as e:
        # Clean up partial output file on error
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.info("Cleaned up partial output file")
            except:
                pass
        
        error_msg = f"Failed to embed subtitles: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def check_ffmpeg_installation():
    """Check if FFmpeg is installed and accessible"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract FFmpeg version from output
            version_line = result.stdout.split('\n')[0]
            logger.info(f"FFmpeg found: {version_line}")
            return True
        else:
            logger.error("FFmpeg command failed")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg version check timed out")
        return False
    except FileNotFoundError:
        logger.error("FFmpeg executable not found in PATH")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg version check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking FFmpeg: {e}")
        return False

def validate_video_file(filepath):
    """Validate that the file is a proper video file using FFprobe"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_streams', filepath
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            # Check if file has video stream
            has_video = any(stream.get('codec_type') == 'video' 
                          for stream in data.get('streams', []))
            
            if has_video:
                logger.info(f"Video file validation passed: {filepath}")
                return True
            else:
                logger.error(f"File has no video stream: {filepath}")
                return False
        else:
            logger.error(f"FFprobe failed for file: {filepath}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Could not validate video file (FFprobe not available or failed): {e}")
        # If FFprobe is not available, assume file is valid based on extension
        return True

# Optional: Test function for development
def test_helpers():
    """Test function to verify helpers work correctly"""
    print("Testing helpers.py...")
    
    # Test timestamp formatting
    test_cases = [
        (0, "00:00:00,000"),
        (1.5, "00:00:01,500"),
        (61.25, "00:01:01,250"),
        (3661.5, "01:01:01,500"),
        (7323.999, "02:02:03,999")
    ]
    
    for seconds, expected in test_cases:
        result = format_time(seconds)
        if result == expected:
            print(f"✓ format_time({seconds}) = {result}")
        else:
            print(f"✗ format_time({seconds}) = {result}, expected {expected}")
    
    # Test FFmpeg installation
    ffmpeg_ok = check_ffmpeg_installation()
    print(f"FFmpeg installation: {'✓ OK' if ffmpeg_ok else '✗ FAILED'}")
    
    return ffmpeg_ok

if __name__ == "__main__":
    test_helpers()