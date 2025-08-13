# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Setup & Commands

This Course Materials RAG System requires Python 3.13+ and uses `uv` for dependency management.

**Installation:**
```bash
uv sync
```

**Environment setup:**
Create `.env` file with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Running the application:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Access:**
- Web Interface: http://localhost:8000  
- API Documentation: http://localhost:8000/docs

## Development Memories

- Always use `uv run server` instead of `pip`
- Use uv to handle all dependency

## Architecture Overview

This is a **tool-enhanced RAG system** that differs from traditional retrieve-then-generate patterns. Instead of direct vector retrieval followed by generation, it uses Claude AI with dynamic tool calling.

### Directory Structure
```
backend/              # Core Python application
├── app.py           # FastAPI main application with endpoints
├── rag_system.py    # Central orchestrator and coordinator
├── models.py        # Data models (Course, Lesson, CourseChunk)
├── ai_generator.py  # Claude API integration with tool support
├── vector_store.py  # ChromaDB integration with dual collections
├── document_processor.py  # Document parsing and chunking
├── search_tools.py  # Tool system and CourseSearchTool
├── session_manager.py     # Conversation history management
└── config.py        # Configuration and environment settings

frontend/            # Web interface (HTML/JS/CSS)
docs/               # Course documents (.txt files)
```

### Core Data Flow

1. **Document Ingestion**: `docs/` → `DocumentProcessor` → `Course`/`CourseChunk` models → `VectorStore` (dual collections)
2. **User query** → FastAPI endpoints (`/api/query`, `/api/courses`)
3. **RAGSystem** orchestrates the process with component coordination
4. **AIGenerator** sends query to Claude AI with registered tools
5. **Claude dynamically decides** when/how to search using tool analysis
6. **CourseSearchTool** queries ChromaDB vector store when needed
7. **Response assembled** with AI-generated content + retrieved sources + session context

### Key Architecture Principles

**Tool-Enhanced Processing (vs Traditional RAG):**
- **Traditional RAG**: Query → Retrieve → Generate
- **This System**: Query → Claude decides if/when to search → Dynamic tool calling → Generate
- `ToolManager` registers `CourseSearchTool` for Claude to use
- Claude calls tools selectively based on query analysis
- More contextual, efficient, and flexible responses

**Dual Vector Storage Strategy:**
- `course_catalog` collection: Course metadata and structure for semantic course name matching
- `course_content` collection: Chunked text content (800 chars, 100 overlap) with lesson context
- Both use `all-MiniLM-L6-v2` embeddings
- Enables fuzzy course name matching while maintaining content precision

**Context-Aware Document Processing:**
- Expects structured document format with course title, instructor, lessons
- Sentence-based chunking with configurable overlap
- Adds course title and lesson number context to each chunk
- Enables precise source attribution in responses

**Session Management:**
- Maintains conversation context (max 2 message exchanges = 4 messages)
- Session IDs track multi-turn conversations
- Role-based message structure with automatic truncation

### Component Architecture

**1. FastAPI Application Layer** (`app.py`):
- **Endpoints**: `POST /api/query`, `GET /api/courses`
- **Middleware**: CORS and trusted host configuration
- **Static Serving**: Frontend files with no-cache headers
- **Startup**: Auto-loads documents from `docs/` folder

**2. RAG System Orchestrator** (`rag_system.py`):
- **Central Coordinator**: Initializes and coordinates all components
- **Key Methods**: 
  - `query()`: Main processing with tool-enhanced generation
  - `add_course_document()`/`add_course_folder()`: Document processing
  - `get_course_analytics()`: Course statistics
- **Component Integration**: DocumentProcessor, VectorStore, AIGenerator, SessionManager, ToolManager

**3. Data Models** (`models.py`):
- **Course**: title (unique ID), course_link, instructor, lessons list
- **Lesson**: lesson_number, title, lesson_link
- **CourseChunk**: content, course_title, lesson_number, chunk_index

**4. AI Generator with Tool Support** (`ai_generator.py`):
- **Claude Integration**: Uses `claude-sonnet-4-20250514` model
- **Two-Step Processing**: Initial response → Tool execution → Final synthesis
- **System Prompt**: Optimized for educational content with search guidelines
- **Configuration**: Temperature=0, max_tokens=800 for consistency

**5. Vector Store with ChromaDB** (`vector_store.py`):
- **Persistent Storage**: ChromaDB with sentence-transformers embeddings
- **Advanced Search**: Course name resolution, optional lesson filtering
- **SearchResults Class**: Structured results with metadata and error handling

**6. Tool System** (`search_tools.py`):
- **Abstract Tool Interface**: Extensible tool system
- **CourseSearchTool**: Main search with smart course name matching
- **ToolManager**: Registers and executes tools, manages tool state

**7. Session Management** (`session_manager.py`):
- **Conversation Context**: User-assistant message history
- **Configurable Limits**: Automatic truncation of old messages

### Database Schema (ChromaDB)

**Course Catalog Collection:**
- **Document**: Course title for semantic matching
- **Metadata**: title, instructor, course_link, lessons_json, lesson_count
- **ID**: Course title

**Course Content Collection:**
- **Document**: Chunk content with course/lesson context
- **Metadata**: course_title, lesson_number, chunk_index
- **ID**: `{course_title}_{chunk_index}`

### Frontend Integration

**Single Page Application** (`frontend/`):
- **Real-time Chat**: WebSocket-style interaction with loading states
- **Course Statistics**: Live course count and titles display
- **Markdown Rendering**: Marked.js for formatted responses
- **Session Continuity**: Maintains session across page interactions
- **Suggested Questions**: Pre-defined queries for user guidance

### Configuration Management

**Environment Settings** (`backend/config.py`):
- **AI Model**: `claude-sonnet-4-20250514`
- **Embeddings**: `all-MiniLM-L6-v2`
- **Chunking**: Size=800, Overlap=100
- **Search**: Max results=5, Max history=2
- **Storage**: ChromaDB path=`./chroma_db`

The system's key innovation is letting Claude AI decide when to search rather than always retrieving first, combined with dual vector storage and context-aware chunking for more intelligent and efficient responses.