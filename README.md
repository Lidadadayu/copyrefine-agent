python -m uvicorn interfaces.http.main:app --reload --port 8000
python -m streamlit run frontend/streamlit_app.py