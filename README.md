# 🎯 AI Resume Screener

<div align="center">

![AI Resume Screener](https://img.shields.io/badge/AI-Resume%20Screener-blue?style=for-the-badge&logo=artificial-intelligence)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)

**Intelligent resume matching powered by AI • Fast • Accurate • Scalable**

[🚀 Live Demo](https://huggingface.co/spaces/youssef-abd/AI_resume_parser) • [📖 Documentation](#documentation) • [🛠️ Installation](#installation) • [🤝 Contributing](#contributing)

</div>

---

## 🌟 Overview

AI Resume Screener is a cutting-edge application that revolutionizes the recruitment process by leveraging advanced AI technologies to match resumes with job descriptions. Built with modern web technologies and powered by vector similarity search, it provides recruiters and HR professionals with intelligent, data-driven candidate recommendations.

### ✨ Key Highlights

- 🧠 **AI-Powered Matching**: Uses sentence transformers and semantic similarity for intelligent resume-job matching
- ⚡ **Vector Search**: Lightning-fast similarity search using PostgreSQL with pgvector extension  
- 📊 **Multi-Dimensional Scoring**: Combines semantic similarity, skills overlap, and composite scoring
- 🎨 **Modern UI**: Clean, responsive Streamlit interface with real-time results
- 🐳 **Production Ready**: Fully containerized with Docker and Nginx reverse proxy
- 🔄 **Real-time Processing**: Instant resume parsing and job matching capabilities

---

## 🚀 Features

### 💼 Job Management
- **Smart Job Creation**: Create detailed job postings with automatic skill extraction
- **Flexible Input**: Supports any text format - markdown, bullet points, or plain text
- **Persistent Storage**: Jobs saved with unique IDs for easy reference

### 📄 Resume Processing  
- **Multi-Format Support**: PDF and DOCX resume parsing
- **Batch Upload**: Process multiple resumes simultaneously
- **Candidate Management**: Optional candidate name association
- **Real-time Feedback**: Live upload progress and detailed results

### 🎯 Intelligent Matching
- **Semantic Analysis**: Deep understanding of job requirements vs. resume content
- **Skills Extraction**: Automatic identification and matching of technical skills
- **Composite Scoring**: Weighted algorithm combining multiple matching factors
- **Visual Rankings**: Interactive charts and detailed comparison tables

### 📊 Advanced Analytics
- **Score Breakdown**: Detailed explanation of matching algorithms
- **Skills Gap Analysis**: Identify missing skills for each candidate
- **Context Highlighting**: Visual highlighting of matched content
- **Export Capabilities**: Download results for further analysis

---

## 🏗️ Architecture

```mermaid
graph TB
    A[Streamlit Frontend] --> B[Nginx Reverse Proxy]
    B --> C[FastAPI Backend]
    C --> D[PostgreSQL + pgvector]
    C --> E[Sentence Transformers]
    C --> F[spaCy NLP Pipeline]
    
    subgraph "AI Components"
        E
        F
        G[Vector Embeddings]
    end
    
    subgraph "Data Layer"
        D
        H[Resume Storage]
        I[Job Storage]
    end
```

### 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Interactive web interface |
| **Backend** | FastAPI | High-performance API server |
| **Database** | PostgreSQL + pgvector | Vector similarity search |
| **AI/ML** | sentence-transformers | Text embeddings |
| **NLP** | spaCy | Text processing & analysis |
| **Deployment** | Docker + Nginx | Containerized production setup |
| **Hosting** | Hugging Face Spaces | Cloud deployment |

---

## 🛠️ Installation

### 🐳 Quick Start with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/youssef-abd/AI_resume_parser.git
cd AI_resume_parser

# Start all services
docker-compose up -d

# Access the application
open http://localhost:7860
```

### 🔧 Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

#### Prerequisites
- Python 3.9+
- PostgreSQL 14+
- Node.js (for development)

#### Backend Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
# Start Streamlit app
streamlit run src/streamlit_app.py --server.port 8501
```

#### Database Setup
```sql
-- Create database and enable pgvector
CREATE DATABASE resume_parser;
\c resume_parser;
CREATE EXTENSION vector;
```

</details>

---

## 📖 Usage

### 1️⃣ Create a Job Posting
- Navigate to the "Create Job" tab
- Enter job title and description (any format supported)
- Add required skills (optional)
- Click "Create Job Posting" and save the Job ID

### 2️⃣ Upload Resumes
- Go to "Upload Resumes" tab  
- Select PDF/DOCX files (supports batch upload)
- Optionally add candidate names
- Monitor upload progress and results

### 3️⃣ Run Matching Analysis
- Switch to "Match & Analyze" tab
- Enter your Job ID
- Set number of top results to display
- Click "Run Matching" for instant AI-powered analysis

### 4️⃣ Analyze Results
- Review composite scores and rankings
- Examine skills gap analysis
- Use highlighted text comparisons
- Export results for decision making

---

## 📊 Scoring Algorithm

Our intelligent matching system uses a sophisticated multi-factor approach:

### 🧮 Score Components

| Score Type | Range | Description |
|------------|-------|-------------|
| **Cosine Similarity** | 0.0 - 1.0 | Semantic similarity between job description and resume |
| **Skills Overlap** | 0.0 - 1.0 | Percentage of required skills found in resume |
| **Composite Score** | 0.0 - 1.0 | Weighted combination optimized for best results |

### 🎯 Matching Process

1. **Text Preprocessing**: Clean and normalize job descriptions and resumes
2. **Embedding Generation**: Convert text to high-dimensional vectors using sentence-transformers
3. **Similarity Calculation**: Compute cosine similarity between job and resume vectors
4. **Skills Extraction**: Use spaCy NLP to identify and match technical skills
5. **Composite Scoring**: Combine semantic and skills-based scores with optimized weights
6. **Ranking & Analysis**: Sort candidates and provide detailed explanations

---

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/resume_parser
POSTGRES_DB=resume_parser
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# API Configuration  
API_BASE_URL=http://localhost:8000
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Streamlit Configuration
STREAMLIT_HOST=0.0.0.0
STREAMLIT_PORT=8501

# AI Model Configuration
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
```

### Docker Configuration

The application uses a multi-service Docker setup:

- **FastAPI Backend**: Handles API requests and AI processing
- **Streamlit Frontend**: Provides the user interface  
- **PostgreSQL Database**: Stores data with vector search capabilities
- **Nginx Proxy**: Routes traffic and serves static files

---

## 🚀 Deployment

### Hugging Face Spaces

This project is deployed on Hugging Face Spaces for easy access:

[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/youssef-abd/AI_resume_parser)

### Local Production Deployment

```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d

# With custom domain
docker-compose -f docker-compose.prod.yml up -d --build
```

### Cloud Deployment Options

- **AWS**: Use ECS with RDS PostgreSQL
- **Google Cloud**: Deploy on Cloud Run with Cloud SQL
- **Azure**: Use Container Instances with Azure Database
- **DigitalOcean**: App Platform with Managed Database

---

## 🧪 Testing

```bash
# Run backend tests
pytest app/tests/

# Run frontend tests  
python -m pytest src/tests/

# Run integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 📈 Performance

### Benchmarks

| Metric | Performance |
|--------|-------------|
| **Resume Processing** | ~2-3 seconds per resume |
| **Job Matching** | ~500ms for 100 resumes |
| **Concurrent Users** | 50+ simultaneous users |
| **Database Queries** | <100ms average response |
| **Memory Usage** | ~2GB for full stack |

### Optimization Features

- ⚡ **Vector Indexing**: Fast similarity search with pgvector
- 🔄 **Async Processing**: Non-blocking API operations
- 💾 **Caching**: Intelligent caching of embeddings and results
- 📦 **Batch Processing**: Efficient multi-resume handling

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### 🐛 Bug Reports
- Use the [issue tracker](https://github.com/youssef-abd/AI_resume_parser/issues)
- Include detailed reproduction steps
- Provide system information and logs

### ✨ Feature Requests
- Check existing [feature requests](https://github.com/youssef-abd/AI_resume_parser/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
- Describe the use case and expected behavior
- Consider implementation complexity

### 🔧 Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/AI_resume_parser.git
cd AI_resume_parser

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
# ...

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Create Pull Request
```

### 📋 Development Guidelines

- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation
- Use conventional commit messages
- Ensure Docker builds pass

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Hugging Face** for hosting and Spaces platform
- **Sentence Transformers** for powerful text embeddings
- **spaCy** for advanced NLP capabilities
- **Streamlit** for rapid UI development
- **FastAPI** for high-performance backend
- **PostgreSQL & pgvector** for vector similarity search

---

## 📞 Support & Contact

- 🐛 **Issues**: [GitHub Issues](https://github.com/youssef-abd/AI_resume_parser/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/youssef-abd/AI_resume_parser/discussions)
- 🚀 **Live Demo**: [Hugging Face Spaces](https://huggingface.co/spaces/youssef-abd/AI_resume_parser)

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ by [Youssef Abd](https://github.com/youssef-abd)

</div>