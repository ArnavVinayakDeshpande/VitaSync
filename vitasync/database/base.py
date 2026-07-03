"""
@file base.py
@brief Abstract base classes defining the database client and database interface contracts for VitaSync.

@details
This module establishes the two foundational abstract interfaces that all
database implementations in VitaSync must satisfy:

  1. AsyncDatabaseClientBase — defines the lifecycle and connectivity contract
     for an asynchronous database connection client (connect, close, ping).

  2. DatabaseBase — defines the repository-exposure contract for a database
     instance, specifying which collection repositories the rest of the
     application can access through the database layer.

The purpose of these abstractions is to decouple the application's business
logic (managers, routers) from any specific database technology. As long as a
concrete implementation satisfies these interfaces, the rest of the VitaSync
codebase can operate without any knowledge of the underlying database driver,
connection pooling mechanism, or cloud provider.

Currently, the sole concrete implementation is AsyncMongoDBClient and
AsyncMongoDBDatabase (defined in mongodb_client.py and mongodb_db.py), which
target MongoDB Atlas via the Motor async driver. Should a future migration to
a different database be required, only a new concrete implementation of these
two base classes needs to be written — no changes are required in the manager,
router, or repository layers.

@note All methods on AsyncDatabaseClientBase are declared async since database
      operations inherently involve network I/O. Concrete implementations may
      contain synchronous internal logic (e.g. Motor's close() is sync) but
      must still be declared as async def to satisfy the abstract interface
      contract and allow callers to uniformly use await regardless of the
      underlying implementation detail.
"""

from abc import ABC, abstractmethod

from vitasync.repositories.patient import PatientRepository


class AsyncDatabaseClientBase(ABC):
    """
    @brief Abstract base class defining the async lifecycle contract for a database connection client.

    @details
    Concrete subclasses are responsible for managing the full lifecycle of a
    database connection — initialization, health verification, and graceful
    shutdown. Each method corresponds to a distinct phase of that lifecycle:

      - connect()  : Establishes or initializes the underlying connection pool.
      - ping()     : Verifies that the database is reachable and the credentials
                     are valid. Called during application startup to fail fast
                     if the database is misconfigured or unreachable.
      - close()    : Tears down the connection pool and releases all associated
                     resources. Called during application shutdown via the
                     FastAPI lifespan context manager's finally block.

    Subclasses must implement all three methods. Any method that does not
    require async behavior in the concrete implementation may still be declared
    as async def with a synchronous body — this preserves a uniform async
    calling convention for all callers without requiring them to know whether
    the underlying operation is truly async.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        @brief Establishes or initializes the database connection.

        @details
        For lazily-connecting drivers such as Motor, this method may be a no-op
        since the actual TCP connection is deferred until the first real operation.
        In that case, concrete implementations should at minimum initialize any
        internal state required before the client can be used (e.g. constructing
        the AsyncIOMotorClient instance if not done in __init__).

        For eagerly-connecting drivers, this method should establish the connection
        and raise an appropriate exception if the connection cannot be established.

        Called once during application startup, before ping().
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """
        @brief Closes the database connection and releases all pooled resources.

        @details
        Must gracefully shut down the connection pool, ensuring that all in-flight
        operations are allowed to complete (or are cancelled cleanly) before the
        pool is torn down. After this method returns, any further operations on
        the client must raise an appropriate error.

        Concrete implementations should also set any internal client reference
        to None after closing, to convert post-close misuse into an immediate
        and obvious AttributeError rather than a silent no-op or a cryptic
        driver-level error.

        Called once during application shutdown, guaranteed by the finally block
        in the FastAPI lifespan context manager.
        """
        ...

    @abstractmethod
    async def ping(self) -> None:
        """
        @brief Verifies that the database is reachable and credentials are valid.

        @details
        Sends a lightweight command to the database server and awaits a response,
        confirming that:
          - The network path to the database is open.
          - The configured credentials are accepted by the database server.
          - The database server is healthy and ready to serve requests.

        Called once during application startup, immediately after connect().
        If ping() raises, the application startup should be aborted — it is
        preferable to fail loudly at startup than to start serving requests
        with a broken database connection.

        @throws Exception An appropriate driver-specific or custom exception if
                          the database is unreachable, credentials are rejected,
                          or the ping command fails for any other reason.
        """
        ...


class DatabaseBase(ABC):
    """
    @brief Abstract base class defining the repository-exposure contract for a VitaSync database instance.

    @details
    Concrete subclasses wrap an AsyncDatabaseClientBase instance and expose
    typed repository properties for each MongoDB collection in the VitaSync
    database. The rest of the application (managers, lifespan initialization)
    accesses all database collections exclusively through these repository
    properties — never by interacting with the raw database client directly.

    This design enforces a strict layering contract:

        Router → Manager → Repository → DatabaseBase → AsyncDatabaseClientBase
                                                              ↓
                                                       Database Driver (Motor)
                                                              ↓
                                                       MongoDB Atlas

    Adding a new collection to VitaSync requires:
      1. Defining a new repository class (e.g. VisitRepository).
      2. Adding a corresponding abstract property to this base class.
      3. Implementing the property in the concrete database class (AsyncMongoDBDatabase).

    No changes are required in the manager or router layers when a new
    collection is added, since they access repositories through this interface.
    """

    @property
    @abstractmethod
    def patient_repository(self) -> PatientRepository:
        """
        @brief Exposes the PatientRepository for the patients collection.

        @details
        Returns the initialized PatientRepository instance bound to the
        underlying patients collection in the VitaSync database. The repository
        is responsible for all CRUD and query operations on patient documents.

        Concrete implementations must ensure the returned repository is fully
        initialized (i.e. PatientRepository.initialize() has been called and
        indexes have been created) before this property is accessed by the
        application's manager layer.

        @return The initialized PatientRepository instance for the patients collection.
        """
        ...
        