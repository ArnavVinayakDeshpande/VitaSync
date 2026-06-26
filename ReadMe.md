<div align="center">

# VitaSync

**Async clinical management backend for boutique maternity & neonatal care facilities.**  
Built for India's ABDM ecosystem — ABHA, JANANI, HFR/HPR — with WhatsApp-native patient communication.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-M2%2FM5-47A248?style=flat-square&logo=mongodb&logoColor=white)
![ABDM](https://img.shields.io/badge/ABDM-JANANI%20Integrated-1565C0?style=flat-square)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)

</div>

---

## Overview

VitaSync is the backend engine for a specialized clinical management system designed for boutique maternity, gynaecological, and neonatal care facilities. It is built from the ground up as an async-first, ABDM-native system — not a generic HMS retrofitted for compliance.

The system bridges the clinic's day-to-day workflows (patient registration, antenatal visit tracking, delivery records, postnatal followup) with India's national digital health infrastructure via the **JANANI** platform, with WhatsApp as the primary patient communication channel.

---

## Core Features

- **Patient & Visit Management** — Full async CRUD for patient demographics, antenatal checkups, delivery records, postnatal and neonatal visits
- **ABDM Integration** — ABHA ID linking, HFR/HPR verification, consent management via the official NHA ABDM Wrapper microservice
- **JANANI Protocol Support** — Longitudinal maternal tracking, QR-enabled digital MCH cards, automated high-risk pregnancy screening alerts, U-WIN immunization registry triggers
- **WhatsApp Communication** — Template-based messaging, appointment reminders, delivery confirmations, and inbound webhook handling
- **Webhook Server** — Inbound ABDM gateway callbacks and WhatsApp delivery receipt handling on the same FastAPI instance
- **Role-aware API** — Endpoints designed for distinct clinic staff roles: receptionist, nurse, doctor

---

## Architecture

```
vitasync/                          ← Python package
├── main.py                        # App entrypoint, lifespan, middleware
├── common/                        # Config singleton, converters
├── database/                      # Abstract DB client + MongoDB specialization
├── repositories/                  # Per-collection async data access layer
├── models/                        # Pydantic models (patient, visit, whatsapp)
├── managers/                      # Business logic layer (router → manager → repo)
├── routers/                       # FastAPI route definitions
├── services/                      # ABDM wrapper client, JANANI service
├── communications/                # WhatsApp async client + messenger/template services
├── webhooks/                      # Inbound ABDM + WhatsApp webhook handlers
├── exceptions/                    # Typed exception hierarchy
├── middleware/                    # Auth + request logging
├── utils/                         # Date arithmetic, ABHA validation, QR generation
└── scripts/                       # Dev utilities: seed data, DB health checks
```

### Request Flow

```
HTTP Request
    │
    ▼
FastAPI Router
    │
    ▼
Manager  ──────────────────────► External Service
(business logic)                 (ABDM Wrapper :8080)
    │                            (WhatsApp API)
    ▼
Repository
    │
    ▼
MongoDB Atlas (ap-south-1)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Web Framework | FastAPI + Uvicorn |
| Data Validation | Pydantic v2 |
| Database | MongoDB Atlas (M2/M5, `ap-south-1`) |
| DB Driver | PyMongo (async) |
| ABDM Compliance | NHA ABDM Wrapper (SpringBoot microservice) |
| HTTP Client | httpx (async) |
| Containerization | Docker + Docker Compose |

---

## ABDM Compliance

VitaSync delegates all ABDM cryptographic operations — ECDH key exchange, JWE/JWS token handling, HIP/HIU flows, consent artifact management — to the official **[NHA ABDM Wrapper](https://github.com/NHA-ABDM/ABDM-wrapper)** microservice, which runs as a sidecar container. VitaSync communicates with the wrapper over the internal Docker network via a typed async HTTP client.

This ensures:
- VitaSync stays current with NHA specification updates without application-layer changes
- Cryptographic operations remain outside the Python application boundary
- Clear separation between clinical data (MongoDB Atlas) and consent/auth state (wrapper-managed)

---

## Government Integrations

| Platform | Purpose |
|---|---|
| **ABHA** | Patient unique health identity (14-digit ID + ABHA address) |
| **HFR** | Clinic's verified national facility identity |
| **HPR** | Verified practitioner identity; required on all pushed clinical records |
| **JANANI** | Maternal tracking, MCH card issuance, high-risk screening |
| **U-WIN** | Immunization registry triggers post-delivery |
| **UHI** | Unified Health Interface for service discovery |

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- Python 3.12 (for local development outside Docker)
- MongoDB Atlas cluster (`ap-south-1` recommended for data localization)
- NHA ABDM Wrapper credentials (HFR ID, client credentials)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/vitasync.git
cd vitasync

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your MongoDB URI, ABDM credentials, WhatsApp tokens

# Start the full stack (FastAPI + ABDM Wrapper)
docker compose up --build
```

The API will be available at `http://localhost:8000`.  
Interactive docs (Swagger UI) at `http://localhost:8000/docs`.  
ABDM Wrapper at `http://localhost:8080`.

### Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn vitasync.main:app --reload
```

---

## Branch Structure

| Branch | Purpose |
|---|---|
| `main` | Production-ready. Protected. Never commit directly. |
| `dev` | Integration branch. All features merge here first. |
| `feature/*` | New functionality |
| `fix/*` | Bug fixes |
| `hotfix/*` | Critical production fixes — merges into both `main` and `dev` |
| `chore/*` | Config, scripts, dependencies, documentation |

---

## Environment Variables

See `.env.example` for the full reference. Key variables:

```env
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=vitasync

# ABDM Wrapper
ABDM_WRAPPER_URL=http://abdm-wrapper:8080
ABDM_CLIENT_ID=
ABDM_CLIENT_SECRET=

# WhatsApp
WHATSAPP_API_URL=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# App
APP_ENV=development
SECRET_KEY=
```

---

## Data Localization

All patient data is stored exclusively in MongoDB Atlas clusters provisioned in the `ap-south-1` (Mumbai) region, in compliance with India's data localization requirements under the Digital Personal Data Protection Act, 2023.

---

## License

Proprietary. All rights reserved.  
Built for **Lé Nest Hospitals — Neelam Nursing Home**, under the supervision of **Dr. Mukesh Gupta**.

