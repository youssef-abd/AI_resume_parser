#!/bin/bash
# Start FastAPI in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait for FastAPI to start
sleep 5

# Start Streamlit
streamlit run src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0