---
title: AI Resume Parser
emoji: 🚀
colorFrom: red
colorTo: red
sdk: docker
app_port: 7860
tags:
- streamlit
- fastapi
- resume-parser
pinned: false
short_description: AI-powered resume parser with FastAPI backend and Streamlit frontend
---

# AI Resume Parser

AI-powered resume parser with vector similarity search and job matching capabilities.

## Features
- Resume parsing and analysis
- Job matching with vector similarity
- FastAPI backend with Streamlit frontend
- PostgreSQL with pgvector extension

## Architecture
- FastAPI API server on `/api/` routes
- Streamlit UI on root `/` routes  
- Nginx reverse proxy handling both services