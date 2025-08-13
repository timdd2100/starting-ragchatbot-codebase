# RAG Chatbot System Flow Diagram (ASCII Style)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   User Interface      │
                          │   (index.html)        │
                          │                       │
                          │  ┌─────────────────┐  │
                          │  │   Chat Input    │  │ User Query
                          │  │   Box           │  │────────┐
                          │  └─────────────────┘  │        │
                          │                       │        │
                          │  ┌─────────────────┐  │        │
                          │  │   Course Stats  │  │        │
                          │  │   Sidebar       │  │        │
                          │  └─────────────────┘  │        │
                          └───────────────────────┘        │
                                      │                    │
                          ┌───────────▼───────────┐        │
                          │   JavaScript          │◄───────┘
                          │   (script.js)         │
                          └───────────┬───────────┘
                                      │
                              ┌───────▼────────┐
                              │  POST /api/query │
                              │  GET /api/courses│
                              └───────┬────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                               API LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   FastAPI App         │
                          │   (app.py)            │
                          │                       │
                          │  ┌─────────────────┐  │
                          │  │ /api/query      │  │──┐
                          │  │ Endpoint        │  │  │
                          │  └─────────────────┘  │  │
                          │                       │  │
                          │  ┌─────────────────┐  │  │
                          │  │ /api/courses    │  │  │
                          │  │ Endpoint        │  │  │
                          │  └─────────────────┘  │  │
                          └───────────────────────┘  │
                                      │              │
┌─────────────────────────────────────▼──────────────▼───────────────────────┐
│                            RAG SYSTEM CORE                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   RAG System          │
                          │   (rag_system.py)     │
                          └─────┬─────┬─────┬─────┘
                                │     │     │
                    ┌───────────▼─┐ ┌─▼─┐ ┌─▼───────────┐
                    │  Session    │ │ AI │ │ Tool        │
                    │  Manager    │ │Gen │ │ Manager     │
                    │             │ │    │ │             │
                    └─────────────┘ └─┬─┘ └─┬───────────┘
                                      │     │
                                      │   ┌─▼──────────┐
                                      │   │ Vector     │
                                      │   │ Search     │
                                      │   └─┬──────────┘
                                      │     │
┌─────────────────────────────────────▼─────▼─────────────────────────────────┐
│                           DATA & STORAGE LAYER                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │                   │
                    ┌─────────▼───────┐  ┌──────▼──────┐
                    │   Claude API    │  │ Vector Store│
                    │   (Anthropic)   │  │ (ChromaDB)  │
                    │                 │  │             │
                    └─────────────────┘  └──────┬──────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │  Document Processor   │
                                    │                       │
                                    └───────────┬───────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │   Course Documents    │
                                    │   (docs/*.txt)        │
                                    └───────────────────────┘

DATA FLOW:
==========

1. USER INPUT FLOW:
   User Input → JavaScript → API Request

2. QUERY PROCESSING FLOW:
   /api/query → RAG System → Session Manager (get history)
                           → AI Generator (with Claude API)
                           → Tool Manager (vector search)
                           → Vector Store (retrieve content)

3. RESPONSE FLOW:
   Claude API → AI Generator → RAG System → API Response → JavaScript → UI Update

4. COURSE STATS FLOW:
   /api/courses → RAG System → Vector Store → Course Analytics → JavaScript → Sidebar Update

KEY COMPONENTS:
===============
- Frontend: HTML/CSS/JavaScript interface
- API: FastAPI with CORS and static file serving
- RAG Core: Session management, AI generation, tool-based search
- Storage: ChromaDB vector store with course documents
- AI: Anthropic Claude for response generation
```

## Flow Description

### 1. User Interaction Flow
1. **User Input** → Chat interface (`index.html`)
2. **JavaScript Handler** → Captures input (`script.js`)
3. **API Request** → Sends to backend endpoints

### 2. API Processing Flow
- **Query Endpoint** (`/api/query`) → Processes user questions
- **Courses Endpoint** (`/api/courses`) → Returns course statistics

### 3. RAG System Flow
1. **Session Management** → Tracks conversation history
2. **AI Generation** → Uses Claude API with tools
3. **Vector Search** → Searches course content via ChromaDB
4. **Response Assembly** → Combines AI response with sources

### 4. Data Flow
- **Documents** → Processed and stored in vector database
- **Vector Search** → Retrieves relevant content chunks
- **AI Enhancement** → Claude generates contextual responses

### 5. Response Flow
- **Generated Answer** → Returns to frontend
- **Sources** → Provides document references
- **UI Update** → Displays response and updates interface