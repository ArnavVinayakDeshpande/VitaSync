<div align="center">

# VitaSync

**An asynchronous, ABDM-ready backend for boutique maternity, gynaecological, and neonatal healthcare facilities.**

Designed with a layered architecture, strong data validation, and MongoDB-first persistence, VitaSync aims to provide a modern clinical management platform that integrates seamlessly with India's digital health ecosystem.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square&logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square)
![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)

</div>

---

# Overview

VitaSync is an asynchronous backend for a specialized Hospital Management System (HMS) developed specifically for boutique maternity, gynaecological, and neonatal care facilities.

Unlike traditional hospital management systems that are later adapted for government compliance, VitaSync is being designed from the ground up to operate within India's **Ayushman Bharat Digital Mission (ABDM)** ecosystem.

The project emphasizes:

- clean layered architecture
- strongly typed business models
- comprehensive validation
- asynchronous database operations
- modular service-oriented design
- future integration with ABDM services and WhatsApp-based patient communication

---

# Current Project Status

VitaSync is currently in active development.

### Implemented

- ✅ Async FastAPI backend
- ✅ MongoDB integration
- ✅ Repository pattern
- ✅ Business logic layer (Managers)
- ✅ Comprehensive Patient Management
    - Create
    - Read
    - Update
    - Delete
    - Advanced filtering
    - Field projection
    - Patient ID lookup
- ✅ Strong validation using Pydantic v2
- ✅ Typed exception hierarchy
- ✅ Automatic MongoDB index creation
- ✅ ABHA data models
- ✅ Extensive inline documentation (Doxygen)

### In Progress

- 🚧 Visit management
- 🚧 Router expansion
- 🚧 Authentication & authorization
- 🚧 Additional repository modules

### Planned

- ABDM Wrapper integration
- JANANI integration
- WhatsApp communication
- Appointment management
- Clinical visit workflows
- Practitioner management
- Facility management
- Audit logging
- Role-based access control

---

# Architecture

VitaSync follows a layered architecture where every layer has a single, well-defined responsibility.

```
                HTTP Request
                     │
                     ▼
             FastAPI Router
                     │
                     ▼
             Business Manager
          (Business Logic Layer)
                     │
                     ▼
              Repository Layer
         (Database Abstraction)
                     │
                     ▼
                 MongoDB
```

This separation ensures that:

- routers only handle HTTP concerns
- managers implement business rules
- repositories perform database operations
- models validate and normalize data
- the database remains an implementation detail

---

# Project Structure

```
vitasync/
│
├── main.py                 # Application entry point
│
├── common/                 # Shared utilities and helpers
│
├── database/
│   ├── base.py
│   ├── mongodb_client.py
│   └── mongodb_db.py
│
├── exceptions/             # Typed application exception hierarchy
│
├── managers/               # Business logic layer
│
├── models/                 # Pydantic domain models
│
├── repositories/           # MongoDB repositories
│
├── routers/                # FastAPI route definitions
│
└── ...
```

---

# Design Principles

The project follows several architectural principles throughout the codebase.

## Layered Architecture

Every layer has a single responsibility.

| Layer | Responsibility |
|--------|---------------|
| Router | HTTP request/response handling |
| Manager | Business logic |
| Repository | Database operations |
| Model | Validation & normalization |
| Database | Persistent storage |

---

## Strong Typing

Instead of passing raw dictionaries throughout the application, VitaSync models every business operation using strongly typed Pydantic models.

Examples include:

- Patient
- PatientCreate
- UpdateArgs
- ConditionUpdateArgs
- ABHAKYCUpdateArgs
- ConditionGetAllArgs
- ABHAKYCGetAllArgs
- GetFieldsResult

This improves readability, validation, maintainability, and IDE support.

---

## Validation Strategy

Validation occurs at multiple layers.

### Models

Responsible for validating:

- names
- mobile numbers
- dates
- ABHA consistency
- patient invariants

### Managers

Responsible for:

- patient ID validation
- retry logic
- orchestration
- business workflows

### Repositories

Responsible only for:

- persistence
- querying
- MongoDB operations

---

## Exception Hierarchy

The backend uses a strongly typed exception hierarchy.

```
Exception
    │
    ▼
VitaSyncBaseError
    │
    ├── Database Errors
    ├── Manager Errors
    └── Generic Errors
```

This allows infrastructure, business, and validation errors to remain clearly separated.

---

# Current Features

## Patient Management

The backend currently supports complete asynchronous patient management, including:

- patient creation
- patient updates
- patient deletion
- patient retrieval
- advanced filtering
- selective field retrieval
- patient identifier lookup

Patient information is validated before persistence, ensuring that records remain internally consistent.

---

## ABHA Support

The project already includes comprehensive models representing ABHA information, including:

- demographic data
- structural address
- ABHA status
- KYC information

Patient records may optionally reference verified ABHA information, allowing automatic synchronization of demographic fields where appropriate.

---

# Technology Stack

| Component | Technology |
|------------|------------|
| Language | Python 3.12 |
| Web Framework | FastAPI |
| Validation | Pydantic v2 |
| Database | MongoDB |
| Database Driver | Motor |
| ASGI Server | Uvicorn |
| Environment Configuration | python-dotenv |

---

# Getting Started

## Prerequisites

- Python 3.12+
- MongoDB instance
- Git

---

## Installation

Clone the repository.

```bash
git clone "https://github.com/ArnavVinayakDeshpande/VitaSync"
cd vitasync
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate it.

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file.

```env
MONGODB_URI=<your-mongodb-connection-string>
```

Run the application.

```bash
uvicorn vitasync.main:app --reload
```

The API will be available at

```
http://localhost:8000
```

Interactive documentation

```
http://localhost:8000/docs
```

---

# Roadmap

The long-term vision for VitaSync includes:

- ABDM Wrapper integration
- ABHA authentication workflows
- JANANI support
- WhatsApp messaging
- Visit management
- Appointment scheduling
- Clinical documentation
- Digital MCH card support
- Practitioner and facility management
- Consent workflows
- Role-based authentication
- Audit logging
- Analytics & reporting

---

# License

This project is proprietary software.

All rights reserved.

Developed for **Lé Nest Hospitals – Neelam Nursing Home** under the supervision of **Dr. Mukesh Gupta**.
