import subprocess

backend = subprocess.Popen(
    ["uvicorn", "backend.main:app", "--port", "8000"]
)

frontend = subprocess.Popen(
    ["npm", "run", "dev"], cwd="frontend", shell=True
)

backend.wait()
frontend.wait()