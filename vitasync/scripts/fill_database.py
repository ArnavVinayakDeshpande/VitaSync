"""
"""

import random
import time
from datetime import datetime, date, timedelta
import asyncio
from dotenv import load_dotenv
from os import getenv
import json

from vitasync.models.patient import (
    Patient,
    MedicalCondition
)
from vitasync.models.ABHA.gender import Gender
from vitasync.database.mongodb_client import AsyncMongoDBClient
from vitasync.database.mongodb_db import AsyncMongoDBDatabase
from vitasync.managers.patient import PatientManager
from vitasync.common.converter import concatenate_name
from vitasync.exceptions.base import VitaSyncBaseError


load_dotenv()

NUM_ENTRIES = 3000

FIRST_NAMES = [
    "Priya", "Anjali", "Sunita", "Kavitha", "Meena",
    "Lakshmi", "Deepa", "Rekha", "Anitha", "Pooja",
    "Divya", "Suma", "Radha", "Geetha", "Usha",
    "Nisha", "Asha", "Latha", "Vinitha", "Saritha",
    "Mamta", "Ritu", "Seema", "Neha", "Swathi",
    "Archana", "Padma", "Savitha", "Jyothi", "Revathi",
    "Shalini", "Bindhu", "Chitra", "Dharini", "Eswari",
    "Falguni", "Gayathri", "Hema", "Indira", "Janaki",
    "Kamala", "Lalitha", "Madhuri", "Nalini", "Omana",
    "Pavithra", "Quincy", "Rani", "Shobha", "Tulasi",
    "Uma", "Vanitha", "Wahida", "Yamini", "Zareena",
    "Amrita", "Bhavana", "Chandrika", "Devaki", "Elango",
    "Fatima", "Girija", "Harini", "Ishwarya", "Jagadha",
    "Kalpana", "Leela", "Malathi", "Nanditha", "Oviya",
    "Parvathi", "Radhika", "Sangeetha", "Thenmozhi", "Urvashi",
    "Vasantha", "Yazhini", "Abitha", "Bhagyalakshmi", "Charumathi",
    "Dhanalakshmi", "Ezhilarasi", "Gowri", "Hamsa", "Ilavarasi",
    "Jayanthi", "Kousalya", "Lissy", "Manonmani", "Nirmala",
    "Padmavathi", "Rajeswari", "Saraswathi", "Thamarai", "Usharani",
    "Vennila", "Alamelu", "Balamani", "Chellammal", "Deivanai"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh",
    "Kumar", "Reddy", "Nair", "Iyer", "Pillai",
    "Joshi", "Mehta", "Shah", "Chopra", "Malhotra",
    "Rao", "Mishra", "Pandey", "Tiwari", "Chauhan",
    "Agarwal", "Bansal", "Goel", "Saxena", "Bhatia",
    "Kulkarni", "Desai", "Patil", "Naik", "Hegde",
    "Krishnan", "Menon", "Varma", "Chandra", "Bose",
    "Das", "Ghosh", "Mukherjee", "Chatterjee", "Banerjee",
    "Sengupta", "Chakraborty", "Bhattacharya", "Roy", "Dutta",
    "Sinha", "Shukla", "Dubey", "Tripathi", "Yadav",
    "Thakur", "Rathore", "Rajput", "Choudhary", "Srivastava",
    "Kapoor", "Khanna", "Mehra", "Anand", "Bajaj",
    "Sethi", "Arora", "Ahuja", "Walia", "Chawla",
    "Gill", "Sandhu", "Grewal", "Dhillon", "Sidhu",
    "Oberoi", "Taneja", "Kohli", "Jolly", "Bedi",
    "Mathur", "Rastogi", "Agarwal", "Nigam", "Srivastav",
    "Venkatesh", "Subramaniam", "Natarajan", "Sundaram", "Rajan",
    "Krishnamurthy", "Parthasarathy", "Raghavan", "Balakrishnan", "Annamalai",
    "Murugan", "Selvam", "Arumugam", "Shanmugam", "Palaniswamy",
    "Govindasamy", "Ramamurthy", "Saravanan", "Velmurugan", "Thiagarajan"
]

ADDRESSES = [
    ("Connaught Place", "Delhi", "110001"),
    ("Karol Bagh", "Delhi", "110005"),
    ("Lajpat Nagar", "Delhi", "110024"),
    ("Dwarka", "Delhi", "110075"),
    ("Rohini", "Delhi", "110085"),
    ("Pitampura", "Delhi", "110034"),
    ("Saket", "Delhi", "110017"),
    ("Janakpuri", "Delhi", "110058"),
    ("Vasant Kunj", "Delhi", "110070"),
    ("Mayur Vihar", "Delhi", "110091"),
    ("Andheri", "Maharashtra", "400053"),
    ("Bandra", "Maharashtra", "400050"),
    ("Pune City", "Maharashtra", "411001"),
    ("Nagpur", "Maharashtra", "440001"),
    ("Thane", "Maharashtra", "400601"),
    ("Navi Mumbai", "Maharashtra", "400706"),
    ("Aurangabad", "Maharashtra", "431001"),
    ("Nashik", "Maharashtra", "422001"),
    ("Kolhapur", "Maharashtra", "416001"),
    ("Solapur", "Maharashtra", "413001"),
    ("Whitefield", "Karnataka", "560066"),
    ("Jayanagar", "Karnataka", "560041"),
    ("Mysuru", "Karnataka", "570001"),
    ("Mangaluru", "Karnataka", "575001"),
    ("Hubli", "Karnataka", "580020"),
    ("Belgaum", "Karnataka", "590001"),
    ("Davangere", "Karnataka", "577001"),
    ("Shimoga", "Karnataka", "577201"),
    ("Tumkur", "Karnataka", "572101"),
    ("Gulbarga", "Karnataka", "585101"),
    ("Anna Nagar", "Tamil Nadu", "600040"),
    ("Adyar", "Tamil Nadu", "600020"),
    ("Coimbatore", "Tamil Nadu", "641001"),
    ("Madurai", "Tamil Nadu", "625001"),
    ("Salem", "Tamil Nadu", "636001"),
    ("Tiruchirappalli", "Tamil Nadu", "620001"),
    ("Tirunelveli", "Tamil Nadu", "627001"),
    ("Erode", "Tamil Nadu", "638001"),
    ("Vellore", "Tamil Nadu", "632001"),
    ("Thanjavur", "Tamil Nadu", "613001"),
    ("Banjara Hills", "Telangana", "500034"),
    ("Secunderabad", "Telangana", "500003"),
    ("Warangal", "Telangana", "506001"),
    ("Gachibowli", "Telangana", "500032"),
    ("Kukatpally", "Telangana", "500072"),
    ("Nizamabad", "Telangana", "503001"),
    ("Karimnagar", "Telangana", "505001"),
    ("Khammam", "Telangana", "507001"),
    ("Mahbubnagar", "Telangana", "509001"),
    ("Nalgonda", "Telangana", "508001"),
    ("Salt Lake", "West Bengal", "700064"),
    ("Howrah", "West Bengal", "711101"),
    ("Durgapur", "West Bengal", "713201"),
    ("Siliguri", "West Bengal", "734001"),
    ("Asansol", "West Bengal", "713301"),
    ("Kharagpur", "West Bengal", "721301"),
    ("Bardhaman", "West Bengal", "713101"),
    ("Haldia", "West Bengal", "721657"),
    ("Malda", "West Bengal", "732101"),
    ("Cooch Behar", "West Bengal", "736101"),
    ("Hazratganj", "Uttar Pradesh", "226001"),
    ("Gomti Nagar", "Uttar Pradesh", "226010"),
    ("Varanasi", "Uttar Pradesh", "221001"),
    ("Agra", "Uttar Pradesh", "282001"),
    ("Kanpur", "Uttar Pradesh", "208001"),
    ("Allahabad", "Uttar Pradesh", "211001"),
    ("Meerut", "Uttar Pradesh", "250001"),
    ("Bareilly", "Uttar Pradesh", "243001"),
    ("Aligarh", "Uttar Pradesh", "202001"),
    ("Moradabad", "Uttar Pradesh", "244001"),
    ("Bopal", "Gujarat", "380058"),
    ("Surat", "Gujarat", "395001"),
    ("Vadodara", "Gujarat", "390001"),
    ("Rajkot", "Gujarat", "360001"),
    ("Gandhinagar", "Gujarat", "382010"),
    ("Bhavnagar", "Gujarat", "364001"),
    ("Jamnagar", "Gujarat", "361001"),
    ("Junagadh", "Gujarat", "362001"),
    ("Anand", "Gujarat", "388001"),
    ("Navsari", "Gujarat", "396445"),
    ("Jaipur", "Rajasthan", "302001"),
    ("Jodhpur", "Rajasthan", "342001"),
    ("Udaipur", "Rajasthan", "313001"),
    ("Ajmer", "Rajasthan", "305001"),
    ("Kota", "Rajasthan", "324001"),
    ("Bikaner", "Rajasthan", "334001"),
    ("Alwar", "Rajasthan", "301001"),
    ("Bharatpur", "Rajasthan", "321001"),
    ("Sikar", "Rajasthan", "332001"),
    ("Pali", "Rajasthan", "306401"),
    ("Bhopal", "Madhya Pradesh", "462001"),
    ("Indore", "Madhya Pradesh", "452001"),
    ("Gwalior", "Madhya Pradesh", "474001"),
    ("Jabalpur", "Madhya Pradesh", "482001"),
    ("Ujjain", "Madhya Pradesh", "456001"),
    ("Raipur", "Chhattisgarh", "492001"),
    ("Bhilai", "Chhattisgarh", "490001"),
    ("Bilaspur", "Chhattisgarh", "495001"),
    ("Korba", "Chhattisgarh", "495677"),
    ("Durg", "Chhattisgarh", "491001")
]

def random_datetime(
    start: date,
    end: date
) -> datetime:
    delta = end - start
    random_date = start + timedelta(days=random.randint(0, delta.days))
    return datetime.combine(random_date, datetime.min.time())

def gen_name() -> str:
    first_name = random.choice(FIRST_NAMES)
    middle_name = None
    last_name = None

    middle_name_odds = random.randint(1, 11)

    if middle_name_odds >= 5:
        middle_name = random.choice(FIRST_NAMES)

    last_name_odds = random.randint(1, 11)

    if last_name_odds >= 3:
        last_name = random.choice(LAST_NAMES)

    return concatenate_name(first_name=first_name, middle_name=middle_name, last_name=last_name)

def gen_phone_number() -> str:
    prefix = random.choice(['+91', '0'])
    # Indian mobile: starts with 6-9, followed by 9 random digits
    return prefix + random.choice('6789') + ''.join(
        [str(random.randint(0, 9)) for _ in range(9)]
    )

def gen_dob() -> datetime:
    return random_datetime(
        start=date(1980, 1, 1),
        end=date(2006, 12, 31)
    )

def gen_conditions(num: int=1) -> set[MedicalCondition]:
    return set(random.sample(list(MedicalCondition), k=num))

def gen_address() -> tuple[str | None, str, str, str]:
    addr = random.choice(ADDRESSES)
    address = (
        ' '.join(addr)
    ) if random.randint(1, 6) <= 2 else None
    return (
        address,
        addr[0],
        addr[1],
        addr[2]
    )

def gen_abha_kyc(
    name: str,
    dob: datetime | None = None,
    mobile_number: str | None = None
) -> dict:
    delimiters = name.split(' ')

    first_name = delimiters[0]
    middle_name = delimiters[1] if len(delimiters) > 1 else None
    last_name = delimiters[2] if len(delimiters) > 2 else None
    address = gen_address()

    if len(delimiters) == 1:
        if random.randint(1, 4) == 1:
            middle_name = random.choice(FIRST_NAMES)

        if random.randint(0, 2) == 1:
            last_name = random.choice(LAST_NAMES)

    return {
        'abha_number': None,
        'abha_address': None,
        'abha_status': None,
        'demographic_data': {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'date_of_birth': dob if dob is not None else gen_dob(),
            'gender': random.choice(list(Gender)),
            'mobile_number': mobile_number if mobile_number else gen_phone_number()
        },
        'structural_address': {
            'raw_address': address[0],
            'district': address[1],
            'state': address[2],
            'pincode': address[3]
        }
    }

def gen_patient() -> dict:
    name = gen_name()
    mobile_number = gen_phone_number()
    dob = gen_dob()
    conditions = gen_conditions(num=random.randint(1, 11))
    is_active = bool(random.randint(0, 2))
    abha_kyc = None

    if random.randint(1, 4) == 1:
        abha_kyc = gen_abha_kyc(
            name=name,
            dob=(dob if random.randint(0, 1) else None),
            mobile_number=(mobile_number if random.randint(1, 4) == 1 else None)
        )

    return {
        'name': name,
        'mobile_number': mobile_number,
        'date_of_birth': dob,
        'conditions': conditions,
        'is_active': is_active,
        'abha_kyc': abha_kyc
    }

async def main():
    print('Starting script...')
    start_time = time.perf_counter()

    mongodb_uri = getenv('MONGODB_URI')

    if mongodb_uri is None:
        raise RuntimeError('Failed to load environment variable MONGODB_URI from .env.')

    mongodb_client = AsyncMongoDBClient(mongodb_uri)

    await mongodb_client.ping()

    mongodb_db = AsyncMongoDBDatabase(mongodb_client)

    await mongodb_db.patient_repository.initialize()

    patient_manager = PatientManager(mongodb_db.patient_repository) 
    # Here we don't initialize the module level patient_manager in PatientManager, as 
    # this is a standalone script and that patient manager should just not be used.

    failed_reasons = []
    responses = []

    for _ in range(NUM_ENTRIES):
        try:
            pd = gen_patient()
            response = await patient_manager.create(pd)
            responses.append(response.model_dump_json())

        except VitaSyncBaseError as exc:
            failed_reasons.append(str(exc))

    failed = len(failed_reasons)

    print(f'Number of attempted tries: {NUM_ENTRIES}')
    print(f'\033[32m Entries Succesfully Created: {NUM_ENTRIES - failed} \033[0m')
    print(f'\033[31m Entries Failed: {failed} \033[0m')

    with open('fill_database.output.log.json', 'w') as f:
        json.dump(
            {
                'responses': responses,
                'exceptions': failed_reasons
            },
            f,
            indent=4
        )

    end_time = time.perf_counter()
    elapsed = end_time - start_time
    print(f'The operation took {elapsed:.4f}s')
    print('Script ended')
    await mongodb_client.close()

if __name__ == '__main__':
    asyncio.run(main())

else:
    raise ImportError('Script should be only be invoked directly from the command line, and should not be imported into another module.')
