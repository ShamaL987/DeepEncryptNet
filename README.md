# 🔐 DeepEncryptNet before

## Trust-Aware Privacy-Preserving Encrypted Traffic Monitoring

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-green?style=flat-square" />
  <img src="https://img.shields.io/badge/React%20%2B%20Vite-Frontend-646CFF?style=flat-square" />
  <img src="https://img.shields.io/badge/Docker-Ready-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Encrypted%20Traffic-Metadata%20Only-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Working%20MVP-success?style=flat-square" />
</p>

## 📌 Overview

DeepEncryptNet is a privacy-preserving encrypted network traffic analysis system designed to operate without inspecting payloads.
It relies purely on packet-level metadata, advanced feature extraction, and a hybrid CNN + Attention + RL decision pipeline to classify encrypted flows and safely handle unknown traffic.

This repository contains the backend implementation, including:

- Real-time flow extraction
- Metadata-only feature processing
- Deep learning inference
- Reinforcement-learning-based routing decisions
- Dockerized deployment with PostgreSQL
- A FastAPI dashboard backend


## 🧠 Key Principles

- 🔒 No payload inspection (TLS / UDP metadata only)
- 🧩 Flow-level analysis (not packet labeling)
- ⚡ Real-time capable
- 🚨 Unknown traffic routing instead of forced classification
- 🧪 Research-grade but production-ready design
- 🏗️ System Components
- 1️⃣ Packet Capture (Executable)

## External Packet Tracker

- Built as a standalone executable  
- Writes CSV-based packet metadata to disk  
- Designed to run with elevated privileges when required  

```bash
pyinstaller --onefile --console --uac-admin main.py
```

---

## Flow Daemon

- Tails live CSV metadata  
- Detects flow boundaries:
  - FIN flag  
  - Idle timeout  
  - Max duration  
- Writes per-flow artifacts  
- Indexes flows into PostgreSQL  
- Triggers inference pipeline asynchronously  

---

## ML Inference Pipeline

- CNN + Attention backbone for feature extraction  
- Confidence calibration (temperature scaling)  

### Reinforcement Learning Decision Layer

- Accept → classify  
- Route → unknown / suspicious flow handling  

- Embedding storage for clustering and later review  

---

## FastAPI Backend

- Lifecycle-managed daemon startup  
- REST endpoints for dashboard and monitoring  
- Static frontend support (optional)  
- PostgreSQL-backed persistence  

---

## Build Packet Sniffer Executable

```bash
  pyinstaller --onefile --console --uac-admin main.py
```

---

## Run Application (Local)

```bash
  uvicorn app.main:application --host 0.0.0.0 --port 8000 --reload
```

---

## Docker (Development)

```bash
  docker compose -f docker-compose.dev.yml up -d
  docker logs -f deepencryptnet_db
```

---

## Docker (Production)

```bash
  docker compose --build --no-cache
  docker compose up
```


---


## 📜 License


- Private research project.
- All rights reserved.


---


## 👤 Author


- **Name:** Praneeth Costa
- **Project:** DeepEncryptNet *(Original Work)*
- **Role:** Undergraduate Research Project
- **Contact:** [✉️ Email](mailto:praneethcosta94@gmail.com)
- **Professional:** [🔗 LinkedIn](https://lk.linkedin.com/in/praneeth-costa)


> © All work herein is original unless otherwise stated.