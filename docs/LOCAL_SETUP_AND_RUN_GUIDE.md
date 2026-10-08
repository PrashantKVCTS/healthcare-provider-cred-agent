# Local Project Setup & Run Instructions Guide
## Healthcare Provider Credentialing Approval Agentic System

**Environment**: Local Development (Visual Studio Code, PowerShell, Terminal, Docker)  
**Supported Platforms**: Windows 10/11, macOS, Linux  
**Python Version**: 3.10, 3.11, 3.12, 3.13 (Verified on Python 3.13.2)  

---

## 1. Prerequisites Checklist

Before running the project locally, verify the following tools are installed:

| Tool | Minimum Version | Verification Command |
|---|---|---|
| **Python** | 3.10+ | `python --version` |
| **Pip** | 23.0+ | `pip --version` |
| **Git** | 2.30+ | `git --version` |
| **VS Code** *(Optional)* | 1.80+ | `code --version` |
| **Docker** *(Optional)* | 24.0+ | `docker --version` |

---

## 2. Step-by-Step Local Setup

### Step 2.1: Open the Project Directory
Open your terminal (PowerShell, Command Prompt, or bash) and navigate to the project directory:

```powershell
cd C:\Users\866223\.gemini\antigravity\scratch\provider_cred_agent
```

### Step 2.2: Automated 1-Click Setup (Recommended for Windows)

The project includes pre-configured automation scripts that create the environment, install dependencies, run tests, and execute a sample CLI run:

* **Using PowerShell**:
  ```powershell
  .\setup.ps1
  ```
  *(If PowerShell displays a script execution policy restriction, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

* **Using Windows Command Prompt**:
  Double-click `setup.bat` or run:
  ```cmd
  setup.bat
  ```

---

### Step 2.3: Manual Virtual Environment Setup

If you prefer configuring the environment manually:

1. **Create Virtual Environment**:
   ```powershell
   # Windows PowerShell / CMD
   python -m venv .venv

   # macOS / Linux
   python3 -m venv .venv
   ```

2. **Activate Virtual Environment**:
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1

   # Windows Command Prompt
   .\.venv\Scripts\activate.bat

   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Upgrade Pip & Install Dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run Pytest to Confirm Environment**:
   ```bash
   python -m pytest tests/test_cred_agent.py -v
   ```
   *Expected result: 11 passed in ~5 seconds.*

---

## 3. Running the Application Locally (4 Execution Modes)

### Mode 1: Visual Studio Code 1-Click Debugging (F5)

The repository includes pre-configured `.vscode/launch.json` debug profiles:

1. Open the folder in VS Code:
   ```powershell
   code C:\Users\866223\.gemini\antigravity\scratch\provider_cred_agent
   ```
2. Press **Ctrl + Shift + D** (or click the **Run & Debug** tab on the left).
3. Select your desired launch target from the dropdown:
   * **`🚀 1. Run Appian Credentialing API (FastAPI)`**: Starts the REST API on `http://localhost:8000` with hot-reloading.
   * **`🏥 2. Run Streamlit Dashboard`**: Starts the interactive web UI on `http://localhost:8501`.
   * **`📋 3. Run CLI Batch Roster Process`**: Runs credentialing against `data/sample_provider_roster.csv`.
   * **`🧪 4. Run Pytest Test Suite`**: Executes all 11 unit and integration tests with coverage.
4. Press **F5** to start!

---

### Mode 2: Terminal / CLI Execution

#### A. Start the Appian REST API:
```bash
python -m uvicorn api.appian_api:app --host 127.0.0.1 --port 8000 --reload
```
* **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Appian OpenAPI 3.0 Export**: [http://localhost:8000/api/v1/appian/openapi.json](http://localhost:8000/api/v1/appian/openapi.json)

#### B. Start the Streamlit Operations Cockpit:
```bash
streamlit run ui/app.py
```
* Automatically opens in your browser at: **`http://localhost:8501`**
* Features:
  - **📁 Roster Batch Ingestion**: Drag-and-drop CSV rosters, view batch metrics, download Appian-ready JSON results.
  - **🩺 On-Demand Single Provider**: Test individual provider credentialing with live PSV verification.
  - **🔔 Event Subscriptions & Webhooks**: Register Appian webhook endpoints, send test pings, and run continuous 90-day alert scans.
  - **⚡ Appian Integration Specs**: Download OpenAPI spec and view Appian Connected System parameters.
  - **⚙️ Market Lines Rules**: Inspect healthcare payer product rules and NCQA 36-month cycles.

#### C. Run the Standalone CLI Batch Runner:
```bash
python run_agent.py --roster data/sample_provider_roster.csv
```
Options:
* `--roster <path>`: Path to CSV or JSON roster file (default: `data/sample_provider_roster.csv`).
* `--output <path>`: Optional path to save JSON results (e.g. `--output results.json`).
* `--npi <10-digit-npi>`: Quick credentialing check for an individual provider NPI.

---

### Mode 3: Local Containerized Execution (Docker Compose)

To run the entire multi-container stack locally without needing Python installed on the host:

1. **Build & Start Services**:
   ```bash
   docker compose up --build
   ```
2. **Access Endpoints**:
   * Appian REST API: `http://localhost:8000/docs`
   * Streamlit Operations Cockpit: `http://localhost:8501`
3. **Stop Services**:
   ```bash
   docker compose down
   ```

---

### Mode 4: Automated Testing Suite

Run the full pytest suite to verify all agent algorithms, business rules, and API endpoints:

```bash
# Standard verbose run
python -m pytest tests/test_cred_agent.py -v

# Run with test timings
python -m pytest tests/test_cred_agent.py --durations=0

# Run specific test (e.g. subscription lifecycle)
python -m pytest tests/test_cred_agent.py -k test_subscription_lifecycle -v
```

---

## 4. Local API Verification & Testing Recipes (cURL / PowerShell)

### Recipe 1: Health Check
```bash
curl -X GET http://localhost:8000/api/v1/health
```
**Response**:
```json
{
  "status": "UP",
  "service": "Healthcare Provider Credentialing Agent API",
  "version": "2.0.0",
  "connected_system_ready": true,
  "active_subscriptions": 1
}
```

### Recipe 2: On-Demand Provider Credentialing
```bash
curl -X POST http://localhost:8000/api/v1/provider/credential \
  -H "Content-Type: application/json" \
  -d '{
    "npi": "1234567893",
    "first_name": "Sarah",
    "last_name": "Conner",
    "specialty": "Family Medicine",
    "practice_state": "TX",
    "appian_case_id": "APP-CASE-101"
  }'
```

### Recipe 3: Trigger Continuous Monitoring Alert Scan
```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/scan-alerts
```
**Response**:
```json
{
  "scan_timestamp": "2026-10-08T12:00:00Z",
  "providers_evaluated": 5,
  "recred_alerts_dispatched": 0,
  "caqh_alerts_dispatched": 1,
  "sanction_alerts_dispatched": 1,
  "total_notifications_sent": 2
}
```

---

## 5. Local Troubleshooting & FAQ

### Issue 1: PowerShell Script Execution Policy Restriction
* **Symptom**: `.\setup.ps1 : File cannot be loaded because running scripts is disabled on this system.`
* **Solution**: Run this command once in your PowerShell session:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### Issue 2: Port 8000 or 8501 Already in Use
* **Symptom**: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`
* **Solution**: Check which process is using the port and kill it, or launch on a different port:
  ```powershell
  # Check PID on port 8000
  netstat -ano | findstr :8000

  # Or run Uvicorn on port 8080 instead:
  uvicorn api.appian_api:app --port 8080 --reload
  ```

### Issue 3: Windows Console Unicode Encoding
* **Symptom**: `UnicodeEncodeError: 'charmap' codec can't encode character...`
* **Solution**: The project is already hardened with `sys.stdout.reconfigure(encoding='utf-8')` and ASCII badges (`[APPROVED]`, `[OK]`, `[DENIED]`). If running outside Python, set your terminal encoding:
  ```powershell
  $OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
  ```

---

## 6. Project Documentation Index

All documents are located in the `docs/` and `appian/` directories:
* **[`docs/LOCAL_SETUP_AND_RUN_GUIDE.md`](LOCAL_SETUP_AND_RUN_GUIDE.md)**: *(This Document)* Local setup, VS Code, CLI, and Docker guide.
* **[`docs/TECHNICAL_DESIGN_DOCUMENT.md`](TECHNICAL_DESIGN_DOCUMENT.md)**: Full architecture specification, NCQA/CMS compliance rules, database/CDT schemas, HMAC security, and sequence diagrams.
* **[`docs/CLOUD_PRODUCTION_DEPLOYMENT_GUIDE.md`](CLOUD_PRODUCTION_DEPLOYMENT_GUIDE.md)**: Step-by-step production deployment to Google Cloud Platform (Cloud Run, HIPAA compliance, Secret Manager, Cloud Armor WAF, CI/CD, and Appian Cloud connectivity).
* **[`docs/AGENTIC_AI_TECHNICAL_LEARNINGS.md`](AGENTIC_AI_TECHNICAL_LEARNINGS.md)**: Comprehensive deep dive on Agentic AI vs. Chatbots/Scripts, Multi-Agent System (MAS) architecture, technology choices, and Low-Code + Agentic AI synergy.
* **[`appian/appian_integration_guide.md`](../appian/appian_integration_guide.md)**: Step-by-step Appian developer guide, Process Model patterns, Web API callback configuration, and SAIL interface code.
* **[`appian/openapi.json`](../appian/openapi.json)**: OpenAPI 3.0 specification for 1-click import into Appian Designer.
