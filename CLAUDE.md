# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MoneyPrinterTurbo is an AI-powered automated video generation system that creates short videos from a single topic or keyword. It generates video scripts, materials, audio, subtitles, and background music, then combines them into high-quality videos. The system supports both API and Web UI interfaces, with a classic MVC architecture and a newer Chana orchestrator integration.

**Key Features:**
- Full MVC architecture with clear separation of concerns
- Supports multiple video formats (9:16 portrait, 16:9 landscape)
- AI-generated video scripts (OpenAI, Moonshot, DeepSeek, Azure, Qwen, Gemini, etc.)
- Multiple subtitle providers (Edge, Whisper)
- Background music support
- Batch video generation
- Video material combination workflow for orchestrator integration

## Project Structure

```
MoneyPrinterTurbo/
├── app/                          # Main application
│   ├── chana_ai/                 # Chana orchestrator integration
│   │   ├── steps/                # Processing pipeline steps (InitStep, DownloadMaterialsStep, etc.)
│   │   ├── chana_video_process.py  # Core video processing for Chana workflow
│   │   ├── chana_video_combination_manager.py  # Manages video clip combination tasks
│   │   └── oss_uploader.py       # OSS upload utility
│   ├── controllers/              # API endpoints
│   │   ├── v1/                   # v1 API routes
│   │   │   ├── video.py          # Video generation endpoints
│   │   │   └── llm.py            # LLM endpoints
│   │   ├── manager/              # Task queue managers
│   │   │   ├── redis_manager.py      # Redis task queue manager
│   │   │   └── chana_redis_manager.py # Chana-specific queue manager
│   │   └── base.py               # Base controller utilities
│   ├── models/                   # Data models
│   │   ├── schema.py             # Pydantic models (VideoParams, VideoScriptParams, etc.)
│   │   ├── event.py              # Event models (VideoClipCombineTask, VideoTaskCompleteEvent)
│   │   ├── Video_task_event.py   # Task event definitions
│   │   └── const.py              # Constants (task states, statuses)
│   ├── services/                 # Business logic layer
│   │   ├── task.py               # Task orchestration (original MoneyPrint workflow)
│   │   ├── chanaVideo.py         # Chana video services (preprocess, generate, combine)
│   │   ├── video.py              # Core video processing (moviepy operations)
│   │   ├── material.py           # Video material fetching/downloading
│   │   ├── llm.py                # LLM provider integration
│   │   ├── voice.py              # TTS (text-to-speech) services
│   │   ├── subtitle.py           # Subtitle generation (Edge/Whisper)
│   │   ├── state.py              # State management (Redis/Memory)
│   │   └── oss.py                # OSS resource handling
│   ├── utils/                    # Utilities
│   │   └── utils.py              # Helper functions
│   ├── config/                   # Configuration
│   │   └── config.py             # Load/save config from TOML
│   └── asgi.py                   # FastAPI app entry point
├── webui/                        # Streamlit web interface
│   └── Main.py                   # Streamlit UI
├── resource/                     # Resources
│   ├── fonts/                    # Subtitle fonts
│   └── songs/                    # Background music files
├── storage/                      # Video storage (default: ./storage/cache_videos)
├── config.toml                   # Main configuration file
├── config.example.toml           # Configuration template
├── main.py                       # API server entry point
├── webui.sh                      # WebUI startup script
└── requirements.txt              # Python dependencies

```

## Architecture Patterns

### MVC Architecture

**Controllers (app/controllers/v1/):** Handle HTTP requests, orchestrate workflows, return responses
- `video.py`: Video generation endpoints (`POST /videos`, `GET /tasks/{task_id}`, etc.)
- `llm.py`: LLM prompt/request endpoints

**Services (app/services/):** Core business logic and video processing
- `task.py`: Original MoneyPrint workflow orchestration (script → materials → audio → subtitles → combine → finalize)
- `chanaVideo.py`: Chana video services (OSS download, preprocess, combine)
- `video.py`: MoviePy-based video operations (combine_videos, generate_video, add_subtitle)
- `material.py`: Fetch video materials from Pexels/Pixabay or local files
- `llm.py`: Provider abstraction (OpenAI, Moonshot, DeepSeek, Azure, Qwen, Gemini, Ollama, G4F)
- `voice.py`: Text-to-speech services (Azure, openai)
- `subtitle.py`: Subtitle generation (edge_tts, faster-whisper)
- `state.py`: State management abstraction (Redis/Memory)
- `oss.py`: OSS resource handling and signed URLs

**Models (app/models/):** Pydantic models for validation and serialization
- `schema.py`: VideoParams, VideoScriptParams, TaskVideoRequest, etc.
- `event.py`: Event models (VideoClipCombineTask, VideoClipCombineCompleteEvent, VideoTaskCompleteEvent)
- `const.py`: Task states (QUEUING, PROCESSING, SUCCESS, FAILED), statuses (COMPLETE, FAILED)

### Two Workflow Patterns

#### 1. Original MoneyPrint Workflow (app/services/task.py)
- **Queues**: Task queue via Redis
- **Flow**: LLM generates script → materials downloaded → audio generated → subtitles generated → materials processed → combined → finalized
- **State**: Managed via Redis state (`enable_redis: true`)

#### 2. Chana Orchestrator Workflow (app/chana_ai/)
- **Purpose**: Integration with external orchestrator for clip combination
- **Queues**: 
  - `compile_clips_queue`: Task queue for clip combination
  - `compile_clips_complete_queue`: Completion queue
- **Flow**: `InitStep` → `DownloadMaterialsStep` → `ProjectMaterialStep` → `CombineStep` → `PostProcessStep`
- **Event-Driven**: Clips are pre-generated by orchestrator, this service only combines them
- **Key Components**:
  - `process_steps.py`: Pipeline steps for combining clips
  - `chana_video_combination_manager.py`: Manages queue consumption and task processing
  - `chana_video_process.py`: Combines clips and adds final audio/subtitles

### State Management

- **RedisState** (default when `enable_redis=true`): Distributed task state
  - Tasks stored as Redis hashes with keys like `chana_task:{project_id}:{stage_id}:{task_id}`
  - Task complete events pushed to `task_complete_queue`
- **MemoryState** (default when `enable_redis=false`): In-memory task state
- **State Events**: Fire events to notify completion (fire_event method)

### Task Queue Pattern

**RedisTaskManager** (app/controllers/manager/redis_manager.py):
- Monitors task queue via `brpop`
- Manages concurrent task execution (max_concurrent_tasks config)
- Handles task submission and completion

**AtomicCounter** (app/controllers/manager/chana_redis_manager.py):
- Thread-safe counter for task tracking

## Running the Project

### Docker Deployment (Recommended)

```bash
cd MoneyPrinterTurbo
docker-compose up
```

Access:
- Web UI: http://0.0.0.0:8501
- API docs: http://0.0.0.0:8080/docs or http://0.0.0.0:8080/redoc

### Manual Deployment

**Prerequisites:**
- Python 3.10+
- ImageMagick (static build recommended)
- FFmpeg (usually auto-downloaded)
- Network access for LLM APIs and video sources

**Setup:**

1. Create conda environment:
```bash
git clone https://github.com/harry0703/MoneyPrinterTurbo.git
cd MoneyPrinterTurbo
conda create -n MoneyPrinterTurbo python=3.10
conda activate MoneyPrinterTurbo
pip install -r requirements.txt
```

2. Configure:
```bash
cp config.example.toml config.toml
# Edit config.toml with your API keys and settings
```

3. Install ImageMagick:
- Windows: Download static build from imagemagick.org
- Mac: `brew install imagemagick`
- Linux: `sudo apt-get install imagemagick` or `sudo yum install ImageMagick`

4. Start API server:
```bash
python main.py
```

5. Start Web UI (separate terminal):
```bash
# Windows
webui.bat

# Mac/Linux
sh webui.sh
```

### Test Environment

For testing with free OpenAI GPT-3.5:
```bash
docker run -p 3040:3040 missuo/freegpt35
# Then configure in config.toml:
# openai_base_url = "http://localhost:3040/v1/"
# openai_api_key = "123456"
# openai_model_name = "gpt-3.5-turbo"
```

## Configuration

Configuration is loaded from `config.toml` (created from `config.example.toml`). Key settings:

**App Settings:**
- `video_source`: "pexels" or "pixabay"
- `llm_provider`: openai, moonshot, deepseek, azure, qwen, gemini, ollama, g4f
- `max_concurrent_tasks`: Max parallel video generations
- `enable_redis`: Enable distributed state (true for production)
- `redis_*`: Redis connection settings

**LLM Provider Settings:**
- OpenAI: `openai_api_key`, `openai_base_url`, `openai_model_name`
- DeepSeek: `deepseek_api_key`, `deepseek_base_url`, `deepseek_model_name`
- Moonshot: `moonshot_api_key`, `moonshot_base_url`, `moonshot_model_name`
- Azure: `azure_api_key`, `azure_base_url`, `azure_model_name`, `azure_api_version`
- Qwen: `qwen_api_key`, `qwen_model_name`
- Gemini: `gemini_api_key`, `gemini_model_name`
- Ollama: `ollama_base_url`, `ollama_model_name`

**Video Processing:**
- `subtitle_provider`: "edge" (fast) or "whisper" (accurate)
- `imagemagick_path`: Path to ImageMagick binary (Windows only)
- `ffmpeg_path`: Path to FFmpeg binary (if auto-download fails)

**Queues:**
- `task_complete_queue`: Redis queue for task completion events
- `compile_clips_queue`: Redis queue for Chana clip combination tasks
- `compile_clips_complete_queue`: Redis queue for clip combination completion

## Key APIs

### Video Generation

**POST /videos**
Generate a short video from a topic/script
- Body: `TaskVideoRequest` (VideoParams with video_subject, script, etc.)
- Returns: `TaskResponse` with task_id
- Task status can be queried via `GET /tasks/{task_id}`

**GET /tasks/{task_id}**
Query task status and download URLs
- Returns: `TaskQueryResponse` with state, progress, videos, combined_videos

**GET /download/{file_path:path}**
Download generated video

### LLM Services

**POST /llm/script**
Generate video script from topic
- Body: `VideoScriptRequest` (video_subject, video_language, paragraph_number)

**POST /llm/terms**
Generate video terms/materials from script
- Body: `VideoTermsRequest` (video_subject, video_script, amount)

**POST /llm/voice**
Generate voice audio from script
- Body: `VideoScriptRequest`
- Returns: audio file path

**POST /llm/subtitle**
Generate subtitles from script
- Body: `VideoScriptRequest`
- Returns: subtitle file path

### Chana Workflow

**POST /v1/chana/video/combine**
Submit clip combination task (internal API for orchestrator)
- Body: `VideoClipCombineTask` (clips, audio, subtitles, metadata)
- Queues task to `compile_clips_queue`

**GET /v1/chana/video/combine-status/{task_id}**
Query combination task status (internal)

## Video Processing Pipeline

### Original Workflow (task.py)
1. **Script Generation** (LLM)
2. **Material Fetching** (Pexels/Pixabay)
3. **Voice Generation** (TTS)
4. **Subtitle Generation** (Edge/Whisper)
5. **Material Preprocessing** (moviepy)
6. **Video Combination** (moviepy)
7. **Finalization** (add final touches, upload to OSS)

### Chana Workflow (chana_ai/steps/process_steps.py)
1. **InitStep**: Setup task context, paths
2. **DownloadMaterialsStep**: Download clips and resources
3. **ProjectMaterialStep**: Download main audio/subtitle/BGM
4. **CombineStep**: Combine clips with video processing
5. **PostProcessStep**: Upload to OSS and cleanup

### Chana Video Processing (chana_video_process.py)
- Combines multiple video clips
- Adds final audio track
- Merges subtitles (if provided)
- Outputs combined video + final video

## Common Tasks

### Adding a New LLM Provider

1. Add provider config to `config.example.toml` and `config.py`
2. Add provider adapter to `app/services/llm.py`
3. Update `VideoParams` in `schema.py` if needed
4. Configure API keys in `config.toml`

### Adding a New Processing Step

1. Create new class in `app/chana_ai/steps/process_steps.py` inheriting from `Step`
2. Implement `process(self, context, event)` method
3. Add to steps list in `ChanaVideoCombinationManager`

### Testing Local Video Processing

Test with existing resources or create a minimal test:

```python
from app.services.video import video
from app.models.schema import VideoParams, VideoConcatMode

# Create test params
params = VideoParams(
    video_subject="test",
    video_concat_mode=VideoConcatMode.random.value,
    video_clip_duration=5
)

# Test combine_videos
video.combine_videos(
    combined_video_path="test_output.mp4",
    video_paths=["clip1.mp4", "clip2.mp4"],
    audio_file="audio.mp3",
    video_aspect=VideoAspect.portrait,
    video_concat_mode=VideoConcatMode.random.value,
    max_clip_duration=5,
    threads=2
)
```

### Running Tests

No test framework currently set up. Tests can be added in a `tests/` directory following the project structure.

### Debugging Common Issues

**AttributeError: 'str' object has no attribute 'choices'**
- Network issue with LLM provider
- Use VPN or configure proxy
- Try Moonshot/DeepSeek (国内访问更快)

**RuntimeError: No ffmpeg exe could be found**
- Set `ffmpeg_path` in config.toml if auto-download fails
- Download from https://www.gyan.dev/ffmpeg/builds/

**Too many open files**
- Increase system file limit: `ulimit -n 10240`

**ImageMagick security policy error**
- Modify policy.xml in ImageMagick installation
- Change `rights="none"` to `rights="read|write"` for pattern="@" entries

**Whisper model download failure**
- Download manually from Baidu/Quark cloud drives
- Place in `./models/whisper-large-v3/` directory

## Code Conventions

- Use loguru logger instead of print statements
- Follow Pydantic models for validation
- Return unified response format via `utils.get_response()`
- Use async/await for I/O operations
- Thread-safe operations for shared state
- Error handling with try/except blocks and logger.error()
- Task IDs as UUIDs, user IDs from headers

## External Dependencies

- **moviepy**: Video processing library
- **faster-whisper**: Whisper model for subtitle generation
- **edge_tts**: Edge-based TTS
- **OpenAI SDK**: For OpenAI API access
- **Redis**: Task queues and state management
- **OSS2**: Alibaba Cloud OSS client
- **fastapi**: API framework
- **streamlit**: Web UI

## Key Files to Understand

- `app/config/config.py`: Configuration loading
- `app/services/task.py`: Original workflow orchestration
- `app/services/chanaVideo.py`: Chana video services
- `app/chana_ai/steps/process_steps.py`: Processing pipeline
- `app/chana_ai/chana_video_combination_manager.py`: Queue management
- `app/services/video.py`: MoviePy operations
- `app/models/schema.py`: Pydantic models
- `app/models/event.py`: Event models
