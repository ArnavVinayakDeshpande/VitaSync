"""
@file main.py

@brief Application entry point for the VitaSync backend.

@details
Configures and starts the VitaSync FastAPI application.

This module is responsible for:

- loading application configuration from environment variables;
- initializing the MongoDB client and database;
- initializing all repositories and managers;
- configuring middleware;
- registering API routers;
- managing the application's startup and shutdown lifecycle.

The application's resource initialization is performed using FastAPI's
lifespan context manager to ensure that all shared resources are created
before the application begins accepting requests and are released
gracefully during shutdown.
"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from os import getenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vitasync.database.mongodb_client import AsyncMongoDBClient
from vitasync.database.mongodb_db import AsyncMongoDBDatabase
import vitasync.managers.patient as PM
from vitasync.routers.patient import router as patient_router


# -----------------------------------------------------------------------------
# Load application configuration from the environment.
# -----------------------------------------------------------------------------

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    @brief Manages the application's startup and shutdown lifecycle.

    @details
    Performs all initialization required before the API begins accepting
    requests and ensures that allocated resources are released during
    application shutdown.

    During startup this function:

    - loads the MongoDB connection URI;
    - establishes a connection to the MongoDB server;
    - verifies database connectivity;
    - creates the application's database abstraction;
    - initializes all repositories;
    - initializes the application's managers.

    During shutdown, the MongoDB client connection is closed gracefully.

    @param app
        The FastAPI application instance.

    @throws RuntimeError
        If the required application configuration could not be loaded.

    @throws VitaSyncDatabaseDisconnectedError
        If the MongoDB server cannot be reached.

    @throws VitaSyncDatabaseExecutionError
        If repository initialization fails.
    """

    # -------------------------------------------------------------------------
    # Startup
    # -------------------------------------------------------------------------

    # Retrieve the MongoDB connection string from the application's
    # environment configuration.
    mongodb_uri = getenv('MONGODB_URI')

    if mongodb_uri is None:
        raise RuntimeError(
            'Required environment variable "MONGODB_URI" could not be loaded. '
            'Ensure that a valid .env file exists and defines the '
            'MongoDB connection URI before starting the application.'
        )

    # Create the application's asynchronous MongoDB client.
    mongodb_client = AsyncMongoDBClient(mongodb_uri)

    # Verify connectivity with the MongoDB server before continuing.
    await mongodb_client.ping()

    # Create the application's database abstraction.
    mongodb_db = AsyncMongoDBDatabase(mongodb_client)

    # Initialize the patient repository and create all required indexes.
    await mongodb_db.patient_repository.initialize()

    # TODO Move repository initialization into AsyncMongoDBDatabase.

    # Initialize all application managers.
    PM.patient_manager = PM.PatientManager(
        mongodb_db.patient_repository
    )

    yield

    # -------------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------------

    # Gracefully close the MongoDB connection.
    await mongodb_db.client.close()


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

app = FastAPI(
    title='VitaSync Backend',
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) for frontend access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# Register application routers.
app.include_router(patient_router)


@app.get('/')
def root():
    """
    @brief Returns the application's health status.

    @details
    Provides a lightweight endpoint that can be used to verify that the
    VitaSync backend is running and capable of accepting incoming HTTP
    requests.

    @return
        A simple status object indicating that the backend is operational.
    """
    return {
        'status': 'VitaSync Backend is up and running.'
    }
    