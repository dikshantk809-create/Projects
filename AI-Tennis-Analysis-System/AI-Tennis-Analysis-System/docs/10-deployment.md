# 10 — Deployment (Tennis)
```bash
cd project-3-tennis-analysis && cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build
# API http://localhost:8003/docs  Dashboard http://localhost:5176
```
Run the edge pipeline on a Jetson Orin / GPU node (ball tracking is compute-heavy).
Calibrate the court (4 corners → homography) and store on the match before play.
