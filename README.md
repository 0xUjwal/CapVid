# 🎬 CapVid - AI-Powered Video Subtitle Generator

**Transform your videos with AI-generated subtitles in minutes!**

CapVid is a modern, full-stack web application that uses OpenAI's Whisper AI to automatically generate and embed subtitles into your videos. With an intuitive interface, real-time processing updates, and smart storage management, it's the easiest way to make your content more accessible.

[![Preview](assets/CapVid.gif)](https://www.capvid.app)


## ✨ Key Features

- 🎯 **AI-Powered Transcription** - High accuracy with adaptive Whisper models (tiny/base)
- 🚀 **Real-time Processing** - Live status updates throughout the workflow
- 📱 **Responsive Design** - Mobile-optimized layout with desktop compatibility
- 🔄 **Smart Storage** - Auto-cleanup with 200MB temporary storage limit
- 🎵 **Multi-format Support** - MP4, AVI, MOV, MKV, WebM, FLV, M4V, 3GP, WMV
- 🌍 **Auto Language Detection** - Supports 50+ languages automatically
- ⚡ **Memory Optimized** - Adaptive model selection based on available memory
- 🛡️ **Extended Retention** - 6-hour file retention with download protection
- 🎬 **Enhanced Subtitles** - Bottom-positioned, readable subtitles with optimal word chunking
- 💾 **File Recovery** - Status recovery from existing files for reliability

## 🛠️ Tech Stack

### Frontend
- **React 18.2.0** - Modern React with hooks and functional components
- **Tailwind CSS 3.4.17** - Utility-first CSS framework
- **anime.js 3.2.1** - Smooth SVG path animations for custom logo
- **@splinetool/react-spline 2.2.6** - 3D background integration

### Backend
- **Flask 3.1.0** - Lightweight Python web framework with CORS support
- **OpenAI Whisper** - Adaptive model selection (tiny/base based on memory)
- **FFmpeg** - Video processing and subtitle embedding with mobile-optimized positioning
- **psutil 6.1.0** - System monitoring and memory management
- **Python 3.8+** - Modern Python with threading and file management

### Infrastructure
- **Temporary Storage** - Smart 200MB limit with 6-hour retention
- **Real-time Updates** - Thread-safe status tracking with file-based persistence
- **Cross-platform** - Windows, macOS, Linux support
- **Memory Adaptive** - Automatic model selection based on available RAM
- **Auto-cleanup** - Conservative cleanup with download protection

## 🏗️ Project Structure

```
CapVid/
├── .github/                 # GitHub Actions workflows
│   └── deploy.yml          # Auto-deployment configuration
├── .vscode/                # VS Code settings and configurations
├── assets/                 # Project assets and media
│   ├── CapVid.gif         # Demo GIF
│   └── CapVid.png         # Logo/screenshot
├── backend/                # Flask backend API
│   ├── __pycache__/       # Python cache files
│   ├── processed/         # Temporary processed video storage
│   ├── uploads/           # Temporary upload storage
│   ├── venv/              # Python virtual environment
│   ├── app.py             # Main Flask application with adaptive AI
│   ├── helpers.py         # Video processing utilities
│   ├── requirements.txt   # Python dependencies
│   ├── test_downloads.py  # Backend testing utilities
│   └── wsgi.py            # WSGI configuration for production
├── frontend/              # React frontend application
│   ├── .vercel/           # Vercel deployment configuration
│   ├── build/             # Production build files
│   ├── node_modules/      # Node.js dependencies
│   ├── public/            # Static assets
│   │   ├── index.html     # HTML template
│   │   └── logo.ico       # Favicon
│   ├── src/               # React source code
│   │   ├── components/    # React components
│   │   │   ├── AnimatedStatusDisplay.js    # Real-time status display
│   │   │   ├── AnimatedUploadForm.js       # Mobile-optimized upload form
│   │   │   ├── ErrorBoundary.js            # Error handling component
│   │   │   ├── GitHubFooter.js             # GitHub repository link
│   │   │   └── SVGAnimatedLogo.js          # Animated CapVid logo
│   │   ├── lib/           # Utility libraries
│   │   │   └── utils.js   # Helper functions
│   │   ├── App.css        # Application styles with responsive design
│   │   ├── App.js         # Main React application with mobile layout
│   │   ├── App.test.js    # Application tests
│   │   ├── index.css      # Global styles
│   │   ├── index.js       # React entry point
│   │   ├── reportWebVitals.js  # Performance monitoring
│   │   └── setupTests.js  # Test configuration
│   ├── .env.local         # Local environment variables
│   ├── .env.production    # Production environment variables
│   ├── .gitignore         # Frontend-specific git ignore
│   ├── .stylelintrc.json  # CSS linting configuration
│   ├── package.json       # Node.js dependencies and scripts
│   ├── package-lock.json  # Dependency lock file
│   ├── postcss.config.js  # PostCSS configuration
│   └── tailwind.config.js # Tailwind CSS configuration
├── .gitattributes         # Git attributes configuration
├── .gitignore             # Git ignore rules
├── CONTRIBUTING.md        # Contribution guidelines
├── README.md              # Project documentation (this file)
└── restart-backend.sh     # Backend restart script
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **FFmpeg** installed on your system

### 1. Clone the Repository

```bash
git clone https://github.com/0xUjwal/CapVid.git
cd CapVid
```

### 2. Install FFmpeg (Windows)

**Most systems don't have FFmpeg pre-installed, which is required for video processing.**

#### Quick Install via CMD (Windows 10+)

Open **Command Prompt as Administrator**:

```cmd
cd C:\

curl -L -o ffmpeg.zip https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

mkdir C:\ffmpeg

tar -xf ffmpeg.zip -C C:\ffmpeg --strip-components=1

setx /M PATH "%PATH%;C:\ffmpeg\bin"
```

**Verify installation** (close and reopen CMD):
```cmd
ffmpeg -version
```

#### Alternative for macOS/Linux:

```bash
# macOS (with Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python app.py
```

The backend will run on `http://localhost:5001`

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will run on `http://localhost:3000`

## 📱 Usage

1. **Upload**: Drag and drop or select a video file (up to 100MB)
2. **Process**: Watch real-time status as AI transcribes your video
3. **Download**: Get your video with embedded subtitles (auto-downloaded as `CapVid-{originalname}.mp4`)

### Supported Formats
- **Input**: MP4, AVI, MOV, MKV, WebM, FLV, M4V, 3GP, WMV
- **Output**: MP4 with embedded subtitles, SRT subtitle files
- **File Limits**: 100MB per file, 200MB total storage

### Processing Steps
1. **Upload & Validation**: Secure file upload with format validation
2. **AI Transcription**: Adaptive Whisper model (tiny/base) converts speech to text
3. **Subtitle Generation**: Create properly timed SRT with optimized word chunking (6 words max)
4. **Video Processing**: Embed subtitles in bottom quarter with enhanced readability
5. **Smart Cleanup**: Files retained for 6 hours with download protection

## 🎯 Key Features & Performance

### Adaptive AI Model System
- **Primary Model**: Whisper `base` (balanced performance and accuracy)
- **Fallback Model**: Whisper `tiny` (memory-constrained environments)
- **Smart Selection**: Automatic model choice based on available memory (<1GB = tiny, ≥1GB = base)
- **Language Support**: Auto-detection for 50+ languages
- **Subtitle Optimization**: Max 6 words per subtitle for enhanced readability

### Smart Storage Management
- **Temporary Storage**: 200MB maximum with conservative cleanup
- **File Lifecycle**: 6-hour retention with 2-hour download protection
- **Status Recovery**: File-based job tracking for multi-worker reliability
- **Memory Optimization**: Original uploads deleted after successful processing
- **Auto-cleanup**: Runs every 2 hours, only when storage >80% capacity

### Enhanced User Experience
- **Mobile-First Design**: Responsive layout optimized for mobile devices
- **Real-time Updates**: Thread-safe status tracking with persistent storage
- **Subtitle Positioning**: Bottom-quarter placement with optimal font sizing
- **Error Recovery**: Graceful fallbacks and detailed error messages
- **Background Processing**: Non-blocking video processing with progress tracking

## 🔧 API Endpoints

### Core Processing
- `GET /` - API health check and status confirmation
- `POST /upload` - Upload video file for processing (100MB max)
- `GET /status/<job_id>` - Get real-time processing status with recovery
- `GET /download/<filename>` - Download processed video with subtitles
- `GET /download_srt/<filename>` - Download SRT subtitle file
- `GET /file_exists/<filename>` - Check if processed file still exists

### System Monitoring & Management
- `GET /storage_info` - Real-time storage usage, limits, and active jobs
- `GET /system_info` - Whisper model info, memory stats, and capabilities
- `GET /health` - Comprehensive health check with system metrics

## ⚙️ Environment Variables

### Backend Configuration
- `FLASK_ENV`: Set to 'production' for production deployment
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to run on (default: 5001)
- `FLASK_DEBUG`: Enable/disable debug mode (default: False)

### Frontend Configuration
- `REACT_APP_API_BASE_URL`: Backend API URL (auto-detects localhost in development)
- `NODE_ENV`: React environment mode (development/production)

## 🚀 Deployment

### Production Deployment
- **Frontend**: Deployed on Vercel with environment-based API detection
- **Backend**: Flask application with Gunicorn and Nginx
- **Auto-deployment**: GitHub Actions workflow for continuous deployment
- **Domain**: https://capvid.app (frontend) and https://api.capvid.app (backend)

⭐ **Star this repository if you found it helpful!**

>Made with ❤️ by Ujwal