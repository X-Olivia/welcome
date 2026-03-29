<p align="center">
  <img src="img/example.png" alt="UNNC Open Day AI Guide" width="720" />
</p>

<h1 align="center">UNNC Open Day AI Guide</h1>

<p align="center">
  <strong>AI-powered Campus Guide — NLU · Route Planning · Voice · Robotic Arm</strong>
</p>

<p align="center">
  <a href="./README.md">🇨🇳 中文</a> | <a href="./README_EN.md">🌐 English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-React_+_Vite-61DAFB?style=flat-square&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/NLU-OpenAI_GPT-412991?style=flat-square&logo=openai" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Robot-SO--ARM101-FF6F00?style=flat-square" alt="SO-ARM101" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="MIT" />
</p>

<p align="center">
  A visitor says what they need, the system plans a route, the screen draws it,<br/>the robotic arm points the way, and a QR code puts it in their pocket.
</p>

<p align="center">
  <a href="https://youtu.be/x3Toh6sFrDE">View Demo</a> · <a href="#-screenshots">Screenshots</a> · <a href="#-quick-start">Quick Start</a>
</p>

---

## 📖 Table of Contents

- [About The Project](#-about-the-project)
- [Screenshots](#-screenshots)
- [Key Features](#-key-features)
- [Product Flow](#-product-flow)
- [Repository Structure](#-repository-structure)
- [Quick Start](#-quick-start)
- [System Modules](#-system-modules)
- [Expansion Potential](#-expansion-potential)
- [Related Documentation](#-related-documentation)

---

## 🤔 About The Project

This is an AI guide system designed for the **University of Nottingham Ningbo China Open Day**.

It is not a FAQ chatbot, nor a static map page — it is a complete pipeline from **natural language → intent understanding → path planning → map visualization → mobile handoff → voice narration → physical arm pointing**.

Visitors can say things like:

```
"How do I get to the library?"
"I want to explore the engineering area"
"I'm interested in AI and robotics"
"It's my first time here, how should I visit?"
```

The system understands the intent, plans a real walkable route, highlights it on the campus map, narrates the result via voice, while a SO-ARM101 robotic arm beside the screen physically points in the starting direction — then generates a QR code so the visitor can continue navigating on their phone.

---

## 📸 Screenshots

<p align="center">
  <strong>🗺️ Route Map — Real walkable path + Point-of-interest cards</strong>
</p>

<p align="center">
  <img src="img/map.png" alt="Route Map" width="720" />
</p>

<p align="center">
  <strong>📋 Guide Result — Route summary + Mobile handoff QR code</strong>
</p>

<p align="center">
  <img src="img/outcome.png" alt="Guide Result" width="720" />
</p>

---

## ✨ Key Features

| | Feature | Description |
|---|---|---|
| 🧠 | **Natural-Language Guidance** | LLM structured output supporting single-point routing / themed tours / recommended tours / clarification; automatic fallback when no API key |
| 🗺️ | **Real Path Planning** | Campus centerline network + **A\*** algorithm producing actual walkable pixel-level polylines |
| 📱 | **Desktop ↔ Mobile Loop** | QR codes encode waypoint state, not just a homepage link; scan to rebuild the full route on any device |
| 🎙️ | **Voice Interaction** | AssemblyAI (STT) + Cartesia (TTS) with greeting, transition, result narration, and fallback phrase pools |
| 🦾 | **Robotic-Arm Integration** | SO-ARM101 face tracking + 8-direction pointing + expressive gestures; the arm points as soon as a route is generated |
| 🔌 | **Modular Engineering** | Frontend / backend / NLU / routing / voice / arm cleanly decoupled; swap knowledge base and map per scenario |

---

## 🚀 Product Flow

```text
  Visitor input (text / voice)
          │
          ▼
  ┌─────────────────────┐
  │  Frontend Layer      │  Desktop kiosk / Mobile page
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │  FastAPI Backend     │  Routing · Sessions · Voice proxy
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │  NLU Understanding   │  LLM structured output + fallback
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │  Intent Dispatch     │  route │ tour │ recommend_tour │ clarification
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │  A* Path Planning    │  Centerline network + multi-stop stitching
  └────────┬────────────┘
           ▼
  ┌────────┴───────────────────────────────────┐
  │              │              │              │
  ▼              ▼              ▼              ▼
 Map render    QR handoff    Voice narration  Arm action
```

---

## 🏗️ Repository Structure

```text
welcome/
├── backend/                       # FastAPI backend
│   ├── app/api/                   #   Route handlers
│   ├── app/services/              #   NLU · Path planning · Orchestration · Voice proxy · Arm
│   ├── app/models/                #   Schemas & data structures
│   ├── app/data/                  #   Campus knowledge base · Theme config (campus.yaml)
│   └── map/                       #   Base map · Points · Centerlines
├── frontend/                      # Vite + React + TypeScript
│   ├── src/pages/                 #   Desktop guide page · Mobile continuation page
│   ├── src/components/            #   Reusable UI components
│   └── src/voice/                 #   Voice state machine · Phrase pools
├── arm_driver/                    # SO-ARM101 robotic arm driver
│   ├── record_leader_poses.py     #   Leader interactive recording
│   ├── replay_leader_poses.py     #   Follower batch replay
│   ├── arm_daemon.py              #   HTTP playback service
│   ├── face_track_follower.py     #   Multi-joint face tracking
│   ├── replay_engine.py           #   Shared replay engine
│   └── test_so101_motion.py       #   Smoke test
├── README.md                      # 中文文档
└── README_EN.md                   # English documentation (this file)
```

---

## ⚡ Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # Add OPENAI_API_KEY (optional — fallback NLU works without it)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Or use the helper script: `chmod +x backend/run_dev.sh && ./backend/run_dev.sh`

<details>
<summary>API overview</summary>

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/guide` | Main guide endpoint |
| `GET`  | `/api/session/{token}` | Restore a guide session |
| `POST` | `/api/route` | Single waypoint route |
| `POST` | `/api/route/multi` | Multi-stop stitched route |
| `POST` | `/api/voice/transcribe` | Speech-to-text (AssemblyAI) |
| `POST` | `/api/voice/speak` | Text-to-speech (Cartesia) |
| `GET`  | `/api/health` | Health check |

</details>

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

- In local dev, Vite proxies `/api` to `http://127.0.0.1:8000`
- For production, configure `VITE_API_BASE` in `frontend/.env.production`

### Robotic Arm (optional)

The arm features require SO-ARM101 hardware and a [LeRobot](https://huggingface.co/docs/lerobot) environment. See [arm_driver/so101-arm-driver.md](arm_driver/so101-arm-driver.md) for full setup.

```bash
conda activate lerobot
python arm_driver/arm_daemon.py   # Start HTTP daemon; the backend connects automatically
```

---

## 🔍 System Modules

<details>
<summary><strong>1. Guide Orchestration</strong></summary>

The main application entry point: receives text or speech transcription → invokes NLU → dispatches into `route` / `tour` / `recommend_tour` / `clarification` → assembles route output, summaries, QR links, and session state.

📍 `backend/app/api/` · `backend/app/services/decision.py`
</details>

<details>
<summary><strong>2. Natural Language Understanding (NLU)</strong></summary>

LLM-based structured intent parsing with place / theme / waypoint normalization. Falls back to local heuristics when the external model is unavailable.

📍 `backend/app/services/nlu.py` · `backend/app/services/campus_data.py` · `backend/app/data/campus.yaml`
</details>

<details>
<summary><strong>3. Spatial Routing</strong></summary>

Reads base map and centerlines → maps waypoints onto the walkable network → computes routes with A\* → returns `route_polyline`, distance data, and multi-stop stitched paths.

📍 `backend/app/services/route_planner.py`
</details>

<details>
<summary><strong>4. Presentation & Experience</strong></summary>

Desktop guide homepage · Route map with point markers · Voice interaction entry · QR code display · Mobile continuation page.

📍 `frontend/src/`
</details>

<details>
<summary><strong>5. Voice Interaction</strong></summary>

STT via AssemblyAI · TTS via Cartesia · Frontend voice state machine · Backend proxy to protect service credentials from browser exposure.

📍 `frontend/src/voice/` · `backend/app/services/assemblyai.py` · `backend/app/services/cartesia.py`
</details>

<details>
<summary><strong>6. Multi-Device Continuation</strong></summary>

Generates shareable links with encoded waypoint parameters → QR code creation → Mobile URL parsing triggers backend route rebuild → Cross-device, cross-session state recovery.

📍 `backend/app/services/decision.py` · `frontend/src/pages/MobilePage.tsx`
</details>

<details>
<summary><strong>7. Embodied Interaction</strong></summary>

SO-ARM101 Leader recording · Follower replay · HTTP daemon · OpenCV face tracking · Route direction → arm `action_key` mapping.

📍 `arm_driver/` · `backend/app/services/route_arm_direction.py` · `backend/app/services/arm_daemon_client.py`
</details>

---

## 🌍 Expansion Potential

The project starts with a campus open day, but the underlying framework transfers naturally to other venues:

| Scenario | What to Replace |
|----------|----------------|
| 🎓 University admissions / International campus tours | Knowledge base + map |
| 🏛️ Museums / Science centers | Knowledge base + map + themes |
| 🏥 Hospitals / Large campuses | Map + walkable network + waypoints |
| 🏢 Corporate parks / Visitor reception | Knowledge base + interaction policy |
| 🎪 Exhibitions / Convention centers / Event venues | Fully customizable per scenario |

From a product perspective, it can serve as: **a deployable spatial guidance system** · **a multimodal reception solution** (kiosk + mobile + voice + robotics) · **a reusable platform where knowledge, maps, and interaction strategies are swappable**.

---

## 📚 Related Documentation

- 🦾 Robotic arm driver guide: [arm_driver/so101-arm-driver.md](arm_driver/so101-arm-driver.md)
