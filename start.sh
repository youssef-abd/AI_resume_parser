#!/bin/bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 & 
streamlit run src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0