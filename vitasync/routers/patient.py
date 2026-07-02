"""
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query
)

import vitasync.managers.patient as PM
from vitasync.models.patient import (
    Patient,
    MedicalCondition,
    PatientCreate
)


router = APIRouter(
    prefix='/patients',
    tags=['Patients']
)

@router.post('')
def create():
    pass

@router.delete('')
def delete():
    pass

@router.patch('')
def update():
    pass

@router.get('')
def getpid():
    pass

@router.get('')
def get():
    pass

@router.get('')
def getall_partial():
    pass

@router.post('')
def getall():
    pass

@router.post('')
def getfields():
    pass
