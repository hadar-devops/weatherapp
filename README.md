
---

## 4) **weatherapp/README.md**

```markdown
# WeatherApp — Python/Flask Monolith

This repository contains the **application code** for the WeatherApp.  
It’s a monolithic Python/Flask app, containerized with Docker and deployed via Helm + ArgoCD.

---

## Usage

Run locally:

```bash
pip install -r requirements.txt
python app.py

Run with Docker:
```bash
docker build -t weatherapp:local .
docker run -p 5000:5000 weatherapp:local
```

CI/CD Flow

When a developer pushes code here:

1.Jenkins pipeline triggers automatically.

2.Pipeline runs linting, tests, and builds a Docker image.

3.The Docker image is pushed to Docker Hub.

4.The Helm chart in helm-weatherapp-chart is updated with the new image tag.

5.ArgoCD detects the Helm update and deploys the new app version to EKS.


Project Flow

1.Code changes are pushed to this repo.

2.Jenkins builds, tests, and creates/pushes a Docker image.

3.Image tag updates are synced into the Helm chart.

4.ArgoCD deploys changes automatically into the cluster.
