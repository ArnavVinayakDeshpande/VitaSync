"""
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

# Load the environment files
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Initialize mongodb client

    # Load the uri
    mongodb_uri = getenv('MONGODB_URI')

    if mongodb_uri is None:
        raise RuntimeError('Failed to load environment variable MONGODB_URI from .env.')

    # Create the client
    mongodb_client = AsyncMongoDBClient(mongodb_uri)
    
    # Ping the client to ensure everything is working
    await mongodb_client.ping()

    # Create the mongodb database
    mongodb_db = AsyncMongoDBDatabase(mongodb_client)

    # Initialize the patient repository
    await mongodb_db.patient_repository.initialize()
    # TODO Push this in database.init

    # Initialize managers
    PM.patient_manager = PM.PatientManager(mongodb_db.patient_repository)

    yield

    # Close the client
    await mongodb_db.client.close()

app = FastAPI(
    title='VitaSync Backend',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# include routers
app.include_router(patient_router)

@app.get('/')
def root():
    return {
        'status': 'VitaSync Backend is up and running.'
    }
