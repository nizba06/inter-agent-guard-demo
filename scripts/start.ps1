# Start IntelBrief API + UI (requires Ollama with llama3.2)

Write-Host "Starting IntelBrief API on http://127.0.0.1:8000 ..."
Start-Process -NoNewWindow py -ArgumentList "-3.12", "-m", "intelbrief"

Start-Sleep -Seconds 3

Write-Host "Starting Streamlit UI on http://127.0.0.1:8501 ..."
py -3.12 -m streamlit run ui/streamlit_app.py
