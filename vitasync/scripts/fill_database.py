"""
@file fill_database.py
@brief Seed script for populating the VitaSync MongoDB Atlas cluster with synthetic patient data.

@details
This script generates randomized but realistic Indian patient records and inserts them
into the VitaSync MongoDB Atlas cluster via the PatientManager layer, ensuring all data
passes through the full Pydantic validation and repository pipeline exactly as production
data would. It is intended exclusively for development and testing purposes.

The script generates patients with randomized:
- Names (Indian first, middle, last names)
- Mobile numbers (valid Indian format)
- Dates of birth
- Medical conditions (from the MedicalCondition enum)
- ABHA KYC data (for a random subset of patients)
- Structural addresses (Indian districts, states, pincodes)

@note This script must be run directly from the command line using:
      python -m vitasync.scripts.fill_database
      It should never be imported as a module.

@warning This script writes real data to whichever MongoDB Atlas cluster is configured
         in the .env file. Ensure the correct environment is loaded before running.
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
from vitasync.models.ABHA.status import ABHAStatus
from vitasync.database.mongodb_client import AsyncMongoDBClient
from vitasync.database.mongodb_db import AsyncMongoDBDatabase
from vitasync.managers.patient import PatientManager
from vitasync.common.converter import concatenate_name
from vitasync.exceptions.base import VitaSyncBaseError


load_dotenv()

NUM_ENTRIES = 3000

# ── Terminal Color Constants ────────────────────────────────────────────────────

class Color:
    RESET   = "\033[0m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BOLD    = "\033[1m"

# ── Seed Data ──────────────────────────────────────────────────────────────────

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

# ── Generator Functions ────────────────────────────────────────────────────────

def random_datetime(start: date, end: date) -> datetime:
    """
    @brief Generates a random datetime between two dates, normalized to midnight.

    @details
    Selects a uniformly random date within the inclusive range [start, end]
    and returns it as a datetime object at 00:00:00 (midnight), consistent
    with VitaSync's date-as-datetime storage convention.

    @param start The earliest possible date (inclusive).
    @param end   The latest possible date (inclusive).

    @return A datetime object representing a random date at midnight (00:00:00).
    """
    delta = end - start
    random_date = start + timedelta(days=random.randint(0, delta.days))
    return datetime.combine(random_date, datetime.min.time())


def gen_name() -> str:
    """
    @brief Generates a randomized full Indian name.

    @details
    Always generates a first name. Randomly assigns a middle name (probability ~6/11)
    and a last name (probability ~9/11), then concatenates the parts with spaces,
    filtering out any None values.

    @return A title-cased full name string (e.g. "Priya Kumari Sharma").
    """
    first_name = random.choice(FIRST_NAMES)
    middle_name = None
    last_name = None

    if random.randint(1, 11) >= 5:
        middle_name = random.choice(FIRST_NAMES)

    if random.randint(1, 11) >= 3:
        last_name = random.choice(LAST_NAMES)

    return concatenate_name(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name
    )


def gen_phone_number() -> str:
    """
    @brief Generates a random valid Indian mobile phone number.

    @details
    Produces a 10-digit Indian mobile number prefixed with either '+91' or '0'.
    The first digit after the prefix is always in the range 6-9 as required
    by Indian mobile numbering conventions, followed by 9 random digits.

    @return A phone number string in the format '+91XXXXXXXXXX' or '0XXXXXXXXXX'.
    """
    prefix = random.choice(['+91', '0'])
    return prefix + random.choice('6789') + ''.join(
        [str(random.randint(0, 9)) for _ in range(9)]
    )


def gen_dob() -> datetime:
    """
    @brief Generates a random date of birth for a patient of reproductive age.

    @details
    Returns a datetime at midnight representing a date of birth between
    1st January 1980 and 31st December 2006, covering an approximate
    age range of 18-44 years, appropriate for a maternity and gynaecological
    care clinic patient population.

    @return A datetime object at midnight representing the date of birth.
    """
    return random_datetime(
        start=date(1980, 1, 1),
        end=date(2006, 12, 31)
    )


def gen_conditions(num: int = 1) -> set[MedicalCondition]:
    """
    @brief Generates a random set of distinct medical conditions.

    @details
    Samples without replacement from the full MedicalCondition enum,
    ensuring no duplicate conditions in the result. The count is capped
    at the total number of available conditions to prevent a ValueError
    from random.sample if num exceeds the enum size.

    @param num The desired number of distinct conditions to generate.
               Defaults to 1. Will be capped at len(MedicalCondition).

    @return A set of MedicalCondition enum members of size min(num, len(MedicalCondition)).
    """
    all_conditions = list(MedicalCondition)
    k = min(num, len(all_conditions))
    return set(random.sample(all_conditions, k=k))


def gen_address() -> tuple[str | None, str, str, str]:
    """
    @brief Generates a random Indian structural address tuple.

    @details
    Selects a random entry from the ADDRESSES seed list. The raw address string
    (a concatenation of district, state, and pincode) is only populated with
    a probability of approximately 2/6 (~33%); otherwise it is set to None,
    simulating real-world cases where a raw unstructured address is absent.

    @return A 4-tuple of (raw_address, district, state, pincode) where:
            - raw_address is either a concatenated string or None
            - district is the locality/area name (str)
            - state is the Indian state name (str)
            - pincode is the 6-digit postal code string (str)
    """
    addr = random.choice(ADDRESSES)
    raw_address = ' '.join(addr) if random.randint(1, 6) <= 2 else None
    return (raw_address, addr[0], addr[1], addr[2])


def gen_abha_number() -> str:
    """
    @brief Generates a syntactically valid random ABHA number.

    @details
    Produces a hyphen-delimited ABHA number in the format XX-XXXX-XXXX-XXXX,
    where the first segment is a 2-digit number and the remaining three segments
    are 4-digit numbers, consistent with the National Health Authority's ABHA
    number format specification.

    @return A string ABHA number in the format 'XX-XXXX-XXXX-XXXX'.
    """
    num2 = lambda: random.randint(10, 99)
    num4 = lambda: random.randint(1000, 9999)
    return f'{num2()}-{num4()}-{num4()}-{num4()}'


def gen_abha_kyc(
    name: str,
    dob: datetime | None = None,
    mobile_number: str | None = None
) -> dict:
    """
    @brief Generates a randomized ABHA KYC data dictionary for a patient.

    @details
    Constructs a complete ABHA KYC payload including demographic data and
    structural address. The name is parsed from the provided full name string
    to extract first, middle, and last name components. If the name contains
    only a single part, there is a random chance of generating an additional
    middle or last name.

    The ABHA address is derived from the parsed name in the format:
    'FirstName MiddleName LastName@abdm'.

    If dob or mobile_number are not provided, they are independently generated.

    @param name          The full patient name string used to derive demographic
                         name components (e.g. 'Priya Kumari Sharma').
    @param dob           Optional datetime representing the patient's date of birth.
                         If None, a random DOB is generated via gen_dob().
    @param mobile_number Optional mobile number string to associate with the ABHA KYC
                         demographic data. If None, a new number is generated via
                         gen_phone_number().

    @return A dict representing the ABHA KYC payload, structured to match the
            ABHAKYC Pydantic model's expected input format.
    """
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
        'abha_number': gen_abha_number(),
        'abha_address': concatenate_name(first_name, middle_name, last_name) + '@abdm',
        'abha_status': random.choice(list(ABHAStatus)),
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
    """
    @brief Generates a complete randomized patient data dictionary.

    @details
    Constructs a patient payload suitable for passing to PatientManager.create().
    The generated patient has:
    - A randomized full Indian name
    - A valid Indian mobile number
    - A date of birth (randomly None 50% of the time, in which case it will be
      fetched from ABHA KYC if present, or generated as a fallback)
    - A random set of 1-11 distinct medical conditions
    - A random active/inactive status (True ~67%, False ~33%)
    - ABHA KYC data with a probability of ~25% (1 in 4 patients)

    When ABHA KYC is generated, there is a 25% chance the patient's own
    mobile number is reused as the ABHA-linked number; otherwise a separate
    number is generated.

    If both dob and abha_kyc are None (meaning DOB cannot be derived from
    KYC either), a DOB is explicitly generated to ensure the Patient model
    validator does not fail on a missing date of birth.

    @return A dict representing the patient payload, structured to match the
            Patient Pydantic model's expected input format (excluding pid,
            which is generated by PatientManager).
    """
    name = gen_name()
    mobile_number = gen_phone_number()
    dob = gen_dob() if random.choice([True, False]) else None
    conditions = gen_conditions(num=random.randint(1, 11))
    is_active = bool(random.randint(0, 2))
    abha_kyc = None

    if random.randint(1, 4) == 1:
        abha_kyc = gen_abha_kyc(
            name=name,
            dob=dob,
            mobile_number=(mobile_number if random.randint(1, 4) == 1 else None)
        )

    if dob is None and abha_kyc is None:
        dob = gen_dob()

    return {
        'name': name,
        'mobile_number': mobile_number,
        'date_of_birth': dob,
        'conditions': conditions,
        'is_active': is_active,
        'abha_kyc': abha_kyc
    }


# ── Entry Point ────────────────────────────────────────────────────────────────

async def main():
    """
    @brief Async entry point for the database seeding script.

    @details
    Orchestrates the full seeding pipeline:
    1. Loads environment variables from .env
    2. Establishes and verifies a connection to MongoDB Atlas
    3. Initializes the patient repository (creates indexes if absent)
    4. Generates NUM_ENTRIES synthetic patient records via gen_patient()
    5. Inserts each record through PatientManager.create(), which runs
       full Pydantic validation and handles pid generation with collision retry
    6. Writes a structured JSON log of all successful responses and failure
       reasons to fill_database.output.log.json
    7. Guarantees MongoDB connection closure via a finally block regardless
       of success or failure

    @note Failures per entry are caught and logged individually — a single
          entry failure does not abort the rest of the seeding run.

    @throws RuntimeError If the MONGODB_URI environment variable is not found
                         in the loaded .env file.
    @throws VitaSyncBaseError Propagated per-entry failures are caught and
                              accumulated in failed_reasons rather than raised.
    """
    mongodb_client = None

    try:
        run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f'{Color.BOLD}{Color.CYAN}╔══════════════════════════════════════════╗{Color.RESET}')
        print(f'{Color.BOLD}{Color.CYAN}║       VitaSync — Database Seed Script    ║{Color.RESET}')
        print(f'{Color.BOLD}{Color.CYAN}╚══════════════════════════════════════════╝{Color.RESET}')
        print(f'{Color.CYAN}  Run timestamp : {run_timestamp}{Color.RESET}')
        print(f'{Color.CYAN}  Target entries: {NUM_ENTRIES}{Color.RESET}')
        print()

        start_time = time.perf_counter()

        # ── Load Environment ───────────────────────────────────────────────────

        mongodb_uri = getenv('MONGODB_URI')

        if mongodb_uri is None:
            raise RuntimeError(
                'MONGODB_URI environment variable not found. '
                'Ensure a valid .env file exists at the project root '
                'and contains the MONGODB_URI key.'
            )

        print(f'{Color.YELLOW}[ENV]{Color.RESET} MongoDB URI loaded successfully.')
        print(f'{Color.YELLOW}[ENV]{Color.RESET} Cluster: {mongodb_uri.split("@")[-1].split("/")[0]}')
        print()

        # ── Connect to MongoDB ─────────────────────────────────────────────────

        print(f'{Color.YELLOW}[DB]{Color.RESET} Connecting to MongoDB Atlas...')
        mongodb_client = AsyncMongoDBClient(mongodb_uri)
        await mongodb_client.ping()
        print(f'{Color.GREEN}[DB]{Color.RESET} Connection established and verified via ping.')
        print()

        # ── Initialize Repository ──────────────────────────────────────────────

        print(f'{Color.YELLOW}[DB]{Color.RESET} Initializing patient repository and ensuring indexes...')
        mongodb_db = AsyncMongoDBDatabase(mongodb_client)
        await mongodb_db.patient_repository.initialize()
        print(f'{Color.GREEN}[DB]{Color.RESET} Patient repository initialized. Indexes verified.')
        print()

        # ── Instantiate Manager ────────────────────────────────────────────────

        patient_manager = PatientManager(mongodb_db.patient_repository)
        # Note: PatientManager is instantiated directly here rather than using
        # the module-level singleton, since this is a standalone script context.

        # ── Seed Loop ─────────────────────────────────────────────────────────

        print(f'{Color.YELLOW}[SEED]{Color.RESET} Beginning patient record generation and insertion...')
        print(f'{Color.YELLOW}[SEED]{Color.RESET} {"─" * 50}')

        failed_reasons = []
        responses = []

        for i in range(NUM_ENTRIES):
            entry_label = f'Entry {i + 1}/{NUM_ENTRIES}'
            try:
                pd = gen_patient()
                response = await patient_manager.create(pd)
                responses.append(response.model_dump_json())
                print(
                    f'{Color.GREEN}[SEED]{Color.RESET} '
                    f'{entry_label} — Inserted successfully. '
                    f'PID: {Color.BOLD}{response.pid}{Color.RESET} | '
                    f'Name: {response.name} | '
                    f'ABHA KYC: {"Yes" if response.abha_kyc else "No"}'
                )

            except VitaSyncBaseError as exc:
                failed_reasons.append(str(exc))
                print(
                    f'{Color.RED}[SEED]{Color.RESET} '
                    f'{entry_label} — Failed. '
                    f'Reason: {str(exc)[:120]}{"..." if len(str(exc)) > 120 else ""}'
                )

        # ── Summary ───────────────────────────────────────────────────────────

        failed = len(failed_reasons)
        succeeded = NUM_ENTRIES - failed
        elapsed = time.perf_counter() - start_time

        print()
        print(f'{Color.YELLOW}[SEED]{Color.RESET} {"─" * 50}')
        print(f'{Color.BOLD}[SUMMARY]{Color.RESET}')
        print(f'  Total attempted : {NUM_ENTRIES}')
        print(f'  {Color.GREEN}Succeeded       : {succeeded}{Color.RESET}')
        print(f'  {Color.RED}Failed          : {failed}{Color.RESET}')
        print(f'  Success rate    : {(succeeded / NUM_ENTRIES * 100):.1f}%')
        print(f'  Time elapsed    : {elapsed:.4f}s')
        print(f'  Avg per entry   : {(elapsed / NUM_ENTRIES * 1000):.2f}ms')
        print()

        # ── Write Log ─────────────────────────────────────────────────────────

        log_path = 'fill_database.output.log.json'
        with open(log_path, 'w') as f:
            json.dump(
                {
                    'meta': {
                        'run_timestamp': run_timestamp,
                        'num_entries_attempted': NUM_ENTRIES,
                        'num_succeeded': succeeded,
                        'num_failed': failed,
                        'elapsed_seconds': round(elapsed, 4)
                    },
                    'responses': responses,
                    'exceptions': failed_reasons
                },
                f,
                indent=4
            )

        print(f'{Color.GREEN}[LOG]{Color.RESET} Output log written to: {Color.BOLD}{log_path}{Color.RESET}')
        print()
        print(f'{Color.BOLD}{Color.CYAN}Script completed.{Color.RESET}')

    finally:
        if mongodb_client is not None:
            await mongodb_client.close()
            print(f'{Color.YELLOW}[DB]{Color.RESET} MongoDB connection closed.')


if __name__ == '__main__':
    asyncio.run(main())