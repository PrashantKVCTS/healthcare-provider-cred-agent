# Cloud Production Deployment Guide
## Deploying Healthcare Provider Credentialing Agent to Google Cloud Platform (GCP)

**Target Environment**: Google Cloud Platform (GCP) / Hybrid Multi-Cloud  
**Target Services**: Google Cloud Run (Serverless Container) / Google Kubernetes Engine (GKE)  
**Security Standard**: HIPAA Compliant, SOC 2 Type II, BAA (Business Associate Agreement)  
**Integration Target**: Appian Cloud via Private Service Connect / Cloud Load Balancing  

---

## 1. Cloud Architecture Overview

```mermaid
flowchart TD
    subgraph Client_and_LowCode [Consumers]
        Appian[Appian Cloud Platform]
        PortalUsers[Healthcare PDM Operations Specialists]
    end

    subgraph GCP_Perimeter [Cloud Security Perimeter]
        CloudArmor[Google Cloud Armor: WAF & DDoS Shield]
        GLB[Cloud HTTPS Load Balancer with SSL/TLS 1.3]
    end

    subgraph GCP_VPC [Secure HIPAA Virtual Private Cloud - VPC]
        subgraph Serverless_Compute [Container Compute Layer]
            CloudRunAPI[Cloud Run: Credentialing Agent API (Autoscaling 1-100)]
            CloudRunUI[Cloud Run: Streamlit Credentialing Cockpit]
        end

        subgraph Storage_and_Events [Persistence & Event Layer]
            CloudSQL[Cloud SQL PostgreSQL: Subscriptions & Cases]
            PubSub[Cloud Pub/Sub: Batch Roster & Async Events]
            KMS[Cloud KMS: Customer-Managed Encryption Keys]
            Secrets[Cloud Secret Manager: API Keys, HMAC Secrets]
        end

        subgraph Observability [Cloud Operations Suite]
            Logging[Cloud Logging: HIPAA Audit Trail]
            Monitoring[Cloud Monitoring & Alerting]
            Trace[Cloud Trace: Latency & Spans]
        end
    end

    subgraph External_Primary_Sources [External PSV Endpoints]
        NPPES[CMS NPPES NPI Registry]
        CAQH[CAQH ProView Web Services]
        OIG[OIG LEIE & SAM.gov Debarments]
    end

    Appian -->|HTTPS with HMAC / mTLS| GLB
    PortalUsers -->|OAuth 2.0 / Cloud Identity| GLB
    GLB --> CloudArmor
    CloudArmor --> CloudRunAPI
    CloudArmor --> CloudRunUI
    CloudRunAPI --> CloudSQL
    CloudRunAPI --> PubSub
    CloudRunAPI --> Secrets
    CloudRunAPI --> KMS
    CloudRunAPI --> External_Primary_Sources
    CloudRunAPI --> Logging
    PubSub -->|Push Webhook| Appian
```

---

## 2. Phase-by-Phase Cloud Production Deployment

### Phase 1: Containerization & Artifact Registry Setup
1. **Container Hardening**:
   - The production [`Dockerfile`](../Dockerfile) utilizes a multi-stage Debian-slim build.
   - Runs under a dedicated unprivileged user (`appuser:appgroup` with UID/GID 1001) in compliance with CIS Docker Benchmarks.
   - Built-in container health check querying `/api/v1/health`.
2. **Create GCP Artifact Registry**:
   ```bash
   gcloud artifacts repositories create cred-agent-repo \
       --repository-format=docker \
       --location=us-central1 \
       --description="Production Docker repository for Credentialing Agent"
   ```
3. **Build & Push Secure Image**:
   ```bash
   # Authenticate Docker to GCP
   gcloud auth configure-docker us-central1-docker.pkg.dev

   # Tag and push container
   docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/cred-agent-repo/cred-agent-api:v2.0.0 .
   docker push us-central1-docker.pkg.dev/$PROJECT_ID/cred-agent-repo/cred-agent-api:v2.0.0
   ```
4. **Automated Vulnerability Scanning**:
   - Google Container Analysis automatically scans pushed images for CVEs, license compliance, and malicious dependencies. Ensure zero `CRITICAL` or `HIGH` vulnerabilities exist before triggering deployment.

---

### Phase 2: Compute Infrastructure Setup (Google Cloud Run)

Google Cloud Run provides serverless, autoscaling, containerized execution with built-in zero-scale cost efficiency and automatic HTTPS.

1. **Deploy Credentialing REST API**:
   ```bash
   gcloud run deploy cred-agent-api \
       --image=us-central1-docker.pkg.dev/$PROJECT_ID/cred-agent-repo/cred-agent-api:v2.0.0 \
       --platform=managed \
       --region=us-central1 \
       --memory=2Gi \
       --cpu=2 \
       --min-instances=1 \
       --max-instances=20 \
       --concurrency=80 \
       --timeout=300 \
       --service-account=cred-agent-sa@$PROJECT_ID.iam.gserviceaccount.com \
       --set-secrets="HMAC_SECRET=cred-hmac-key:latest,CMS_API_KEY=cms-nppes-key:latest" \
       --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=info" \
       --ingress=all \
       --allow-unauthenticated
   ```
2. **Deploy Streamlit Operations Cockpit**:
   ```bash
   gcloud run deploy cred-agent-ui \
       --image=us-central1-docker.pkg.dev/$PROJECT_ID/cred-agent-repo/cred-agent-api:v2.0.0 \
       --platform=managed \
       --region=us-central1 \
       --command="streamlit","run","ui/app.py","--server.port","8501","--server.address","0.0.0.0" \
       --port=8501 \
       --memory=1Gi \
       --cpu=1 \
       --min-instances=1 \
       --max-instances=5 \
       --ingress=internal-and-cloud-load-balancing
   ```

---

### Phase 3: HIPAA Security Controls, KMS & Secrets Management

Healthcare credentialing data contains sensitive provider identity and Tax ID (EIN) information. Under HIPAA, technical safeguards must be enforced:

1. **Business Associate Agreement (BAA)**:
   - Ensure an active Google Cloud BAA is executed in the GCP Organization console under **Compliance & Agreements**.
2. **Customer-Managed Encryption Keys (Cloud KMS)**:
   - Encrypt storage buckets, Cloud SQL databases, and Secret Manager objects using a Customer-Managed Encryption Key (CMEK):
   ```bash
   gcloud kms keyrings create cred-agent-keyring --location=us-central1
   gcloud kms keys create cred-data-key \
       --location=us-central1 \
       --keyring=cred-agent-keyring \
       --purpose=encryption
   ```
3. **Secret Manager for Sensitive Credentials**:
   ```bash
   # Store HMAC Shared Secret for Appian Webhook Verification
   echo -n "Production-Super-Secret-HMAC-Key-2026" | \
       gcloud secrets create cred-hmac-key --data-file=-

   # Grant Cloud Run service account access
   gcloud secrets add-iam-policy-binding cred-hmac-key \
       --member="serviceAccount:cred-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```
4. **VPC Service Controls & Private Google Access**:
   - Establish a security perimeter around Cloud Run and Cloud Storage to prevent data exfiltration.

---

### Phase 4: Appian Cloud Connectivity & Network Topology

To integrate Appian Cloud securely with GCP:

1. **Inbound from Appian to Cloud Run API**:
   - **Method A (Public HTTPS with IP Whitelisting & Mutual TLS / HMAC)**:
     - Deploy a Google Cloud HTTPS Load Balancer with Cloud Armor WAF.
     - Add Cloud Armor security policy whitelisting Appian Cloud NAT gateway outbound IP addresses.
     - Require Appian to send `X-API-Key` or Bearer token header on every request.
   - **Method B (Google Private Service Connect / Cloud VPN)**:
     - For strict corporate requirements with zero public routing, provision an IPSec VPN tunnel between Appian Cloud and the GCP VPC.
     - Route requests directly over private IP space (`10.x.x.x`).

2. **Outbound from Cloud Run Subscription Service to Appian Web API**:
   - Cloud Run delivers webhook events (`CREDENTIALING_COMPLETED`, `RECREDENTIALING_ALERT`) to Appian Web API (`https://myhealthplan.appiancloud.com/suite/webapi/credentialing-callback`).
   - Every webhook includes the `X-CredAgent-Signature` HMAC-SHA256 header, allowing Appian's expression rule to cryptographically verify payload origin before invoking Process Models.

---

### Phase 5: Automated CI/CD Pipeline (Cloud Build / GitHub Actions)

Configure `.github/workflows/deploy.yml` for automated testing and deployment:

```yaml
name: Production CI/CD Pipeline

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Test Suite
        run: python -m pytest tests/test_cred_agent.py -v

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      - name: Build & Push Container Image
        run: |
          gcloud auth configure-docker us-central1-docker.pkg.dev
          docker build -t us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/cred-agent-repo/cred-agent-api:${{ github.sha }} .
          docker push us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/cred-agent-repo/cred-agent-api:${{ github.sha }}
      - name: Deploy to Cloud Run (Blue-Green)
        run: |
          gcloud run deploy cred-agent-api \
            --image=us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/cred-agent-repo/cred-agent-api:${{ github.sha }} \
            --region=us-central1 \
            --platform=managed
```

---

### Phase 6: SRE Observability, Logging & Alerting

1. **Cloud Logging**:
   - Structured JSON logs are automatically captured by GCP Cloud Logging.
   - PII/PHI scrubbing filter applied in middleware to ensure NPI/TIN compliance with HIPAA de-identification guidelines.
2. **Cloud Monitoring & Metrics**:
   - Track key Service Level Indicators (SLIs):
     * **API Latency (p95 / p99)**: Target $< 250\text{ ms}$ for single provider verification.
     * **Error Rate (5xx)**: Target $< 0.05\%$.
     * **Batch Throughput**: Target $> 500\text{ providers/min}$.
     * **Webhook Delivery Success Rate**: Target $> 99.9\%$.
3. **Alerting Policies**:
   - Send PagerDuty / Slack notifications if:
     * 5xx error rate exceeds 1% over a 5-minute rolling window.
     * Webhook delivery failure count exceeds 5 consecutive attempts.
     * Container health check fails for 3 consecutive intervals.

---

### Phase 7: Production Cutover & Rollback Strategy

1. **Canary / Traffic Splitting**:
   - Cloud Run supports traffic splitting with revision management:
     ```bash
     # Route 10% traffic to new revision
     gcloud run services update-traffic cred-agent-api \
         --to-revisions=cred-agent-api-v2-0=10,cred-agent-api-v1-9=90
     
     # Once validated, route 100% traffic to new revision
     gcloud run services update-traffic cred-agent-api \
         --to-revisions=cred-agent-api-v2-0=100
     ```
2. **Instant Rollback**:
   - If regressions or integration errors occur with Appian, immediately rollback traffic:
     ```bash
     gcloud run services update-traffic cred-agent-api \
         --to-revisions=cred-agent-api-v1-9=100
     ```
