"""
@file mongodb_db.py
@brief MongoDB-backed implementation of the VitaSync database abstraction.

@details
This module provides AsyncMongoDBDatabase, the concrete MongoDB implementation
of the DatabaseBase interface. It acts as the central database access layer
for the application by:

  - Holding a shared AsyncMongoDBClient instance for the application's
    lifetime.

  - Creating and storing references to the MongoDB database and all required
    collections.

  - Constructing repository instances using those collection references.

  - Providing a single access point for repositories through typed property
    accessors, preventing higher application layers from interacting directly
    with MongoDB collections.

Unlike AsyncMongoDBClient, this class does not establish or manage network
connections. Its responsibility is to organize the application's database
structure once a connected client has been provided.

@note Repository initialization (such as index creation) should be performed
      explicitly during application startup. This class is responsible only
      for constructing and exposing repository instances.
"""

from vitasync.database.base import DatabaseBase
from vitasync.database.mongodb_client import AsyncMongoDBClient
from vitasync.repositories.patient import PatientRepository


class AsyncMongoDBDatabase(DatabaseBase):
    """
    @brief Concrete MongoDB implementation of the VitaSync database abstraction.

    @details
    Wraps an AsyncMongoDBClient instance and constructs references to the
    application's MongoDB database, collections, and repositories.

    A single instance of this class is typically created during FastAPI
    application startup after the database client has been successfully
    initialized and its connectivity verified.

    The object serves as a lightweight dependency container, allowing
    managers and other higher-level application components to access
    repositories without requiring knowledge of MongoDB collection names
    or the underlying Motor driver.
    """

    def __init__(self, client: AsyncMongoDBClient):
        """
        @brief Initializes the MongoDB database abstraction.

        @details
        Stores the provided MongoDB client, retrieves references to the
        application's database and collections, and constructs repository
        instances using those collection references.

        Database and collection retrieval are lightweight operations that
        simply create Motor reference objects. No database operations or
        network requests are performed during initialization.

        @param client
            The shared AsyncMongoDBClient instance used to access the
            MongoDB Atlas cluster.
        """

        # Shared MongoDB client used throughout the application's lifetime.
        self._client = client

        # Reference to the application's primary MongoDB database.
        self._hospital_database = self._client.get_database('hospital_db')

        # Collection references.
        self._patient_collections = self._hospital_database['patients']

        # Repository instances.
        self._patient_repository = PatientRepository(self._patient_collections)

        # Indicates whether repository initialization has completed.
        self._is_initialized = False

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def client(self) -> AsyncMongoDBClient:
        """
        @brief Returns the underlying MongoDB client.

        @details
        Exposes the shared AsyncMongoDBClient instance used to communicate
        with the MongoDB Atlas cluster.

        This property primarily exists for components responsible for
        database lifecycle management or initialization.

        @return
            The shared AsyncMongoDBClient instance.
        """
        return self._client

    @property
    def is_initialized(self) -> bool:
        """
        @brief Returns whether the database has been fully initialized.

        @details
        Indicates whether any application-specific initialization tasks
        (such as repository index creation) have completed successfully.

        The flag is intended to prevent application components from
        accessing repositories before startup initialization has finished.

        @return
            True if initialization has completed, otherwise False.
        """
        return self._is_initialized

    @property
    def hospital_db(self):
        """
        @brief Returns the MongoDB database reference.

        @details
        Provides access to the application's primary MongoDB database.
        This is a lightweight Motor database reference and does not
        represent an active network connection.

        @return
            The Motor database object representing the hospital database.
        """
        return self._hospital_database

    @property
    def patient_collections(self):
        """
        @brief Returns the patients collection reference.

        @details
        Exposes the MongoDB collection used for storing patient documents.

        Repository classes use this collection to perform CRUD operations.

        @return
            The Motor collection representing the patients collection.
        """
        return self._patient_collections

    @property
    def patient_repository(self) -> PatientRepository:
        """
        @brief Returns the patient repository instance.

        @details
        Provides access to the application's PatientRepository, which
        encapsulates all patient-related database operations.

        Higher application layers should interact with patients through
        this repository rather than directly accessing MongoDB collections.

        @return
            The application's PatientRepository instance.
        """
        return self._patient_repository
        