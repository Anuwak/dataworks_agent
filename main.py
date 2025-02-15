import os
import subprocess
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
import requests
import aiohttp

app = FastAPI()
DATA_DIR = Path("/data")
AIPROXY_URL = "https://api.ai-proxy.com/v1/chat/completions"

def sanitize_path(path: str) -> Path:
    full_path = (DATA_DIR / path).resolve()
    if not str(full_path).startswith(str(DATA_DIR)):
        raise HTTPException(400, "Path outside /data not allowed")
    return full_path

async def query_llm(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['AIPROXY_TOKEN']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(AIPROXY_URL, headers=headers, json=data) as response:
            result = await response.json()
            return result['choices'][0]['message']['content']

@app.post("/run")
async def run_task(task: str = Query(...)):
    try:
        # Task parsing with LLM
        prompt = f"""Convert this task to executable steps: {task}
        Output format: {{"steps": [{{"action": "command|file|llm", "command": "...", "output_file": "..."}}]}}"""
        
        llm_response = await query_llm(prompt)
        steps = json.loads(llm_response)["steps"]

        # Execute steps
        for step in steps:
            if step["action"] == "command":
                proc = subprocess.run(
                    step["command"],
                    shell=True,
                    capture_output=True,
                    cwd="/data"
                )
                if proc.returncode != 0:
                    raise HTTPException(500, f"Command failed: {proc.stderr.decode()}")
                
            elif step["action"] == "file":
                Path(step["output_file"]).write_text(step["content"])
                
        return {"status": "success"}

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid task format")
    except KeyError:
        raise HTTPException(500, "Agent processing error")

@app.get("/read")
async def read_file(path: str = Query(...)):
    try:
        file_path = sanitize_path(path)
        if not file_path.exists():
            raise HTTPException(404, "File not found")
        return file_path.read_text()
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
