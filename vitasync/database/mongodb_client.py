"""
@file mongodb_client.py
@brief Concrete MongoDB implementation of the VitaSync async database client interface.

@details
This module provides AsyncMongoDBClient, the MongoDB Atlas-specific implementation
of AsyncDatabaseClientBase. It wraps Motor's AsyncIOMotorClient to provide:

  - Lazy connection initialization: Motor does not establish a TCP connection
    at client construction time. The connection pool is opened on the first
    real database operation (typically the ping() call during startup).

  - Lifecycle management: explicit close() and ping() methods that integrate
    with FastAPI's lifespan context manager for clean startup and shutdown.

  - Collection and database access: typed accessor methods for retrieving
    Motor database and collection references, with is_connected guards to
    prevent use-after-close errors.

  - Exception translation: PyMongoError exceptions from the Motor driver are
    caught and re-raised as VitaSync-specific database exceptions, ensuring
    that no Motor or PyMongo types leak into the manager or router layers.

@note AsyncMongoDBClient does not manage individual collection indexes.
      Index creation is the responsibility of each repository's initialize()
      method, called explicitly during application startup in main.py.

@note Motor's close() method is synchronous in the installed version of Motor
      used by VitaSync (verified at development time by inspecting the return
      type of close(), which is NoneType rather than a coroutine). The close()
      method on this class is declared async to satisfy the AsyncDatabaseClientBase
      abstract interface, but the underlying self._client.close() call is made
      without await. If Motor is upgraded and close() becomes async in a future
      version, an await must be added here.
"""

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection
)
from pymongo.errors import PyMongoError

from vitasync.exceptions.database import (
    VitaSyncDatabaseDisconnectedError,
    VitaSyncDatabaseExecutionError
)
from vitasync.database.base import AsyncDatabaseClientBase


class AsyncMongoDBClient(AsyncDatabaseClientBase):
    """
    @brief Async MongoDB Atlas client implementing the VitaSync database client interface.

    @details
    Wraps an AsyncIOMotorClient instance and exposes lifecycle management
    (connect, ping, close) and collection/database accessors used by the
    VitaSync database layer. This class is instantiated once during application
    startup in the FastAPI lifespan context manager and held as a module-level
    reference in database.mongodb_db for the duration of the server's lifetime.

    Internally, the Motor client manages a connection pool automatically.
    The pool is opened lazily on the first network operation and torn down
    when close() is called. The is_connected property reflects whether the
    client object is still alive (i.e. close() has not yet been called),
    not whether an active TCP connection currently exists — Motor manages
    the latter transparently.
    """

    def __init__(self, uri: str) -> None:
        """
        @brief Initializes the MongoDB client with the given Atlas connection URI.

        @details
        Constructs the AsyncIOMotorClient from the provided URI. This operation
        is synchronous and does not establish a network connection — Motor defers
        the actual TCP connection to the first operation that requires it.

        The URI should be a valid MongoDB Atlas SRV connection string in the format:
            mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?<options>

        Special characters in the username or password must be URL-encoded
        (e.g. '@' → '%40') to avoid being misinterpreted as URI delimiters.

        @param uri The MongoDB Atlas SRV connection string. Loaded from the
                   MONGODB_URI environment variable via dotenv in main.py.
        """
        self._uri = uri
        self._client: AsyncIOMotorClient | None = AsyncIOMotorClient(self._uri)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def uri(self) -> str:
        """
        @brief Returns the MongoDB Atlas connection URI used to initialize this client.

        @details
        The URI is stored as provided and never modified. Note that this includes
        the embedded credentials — this property should never be logged in full
        in production. Use uri.split('@')[-1] to log only the cluster hostname.

        @return The raw MongoDB SRV connection string URI.
        """
        return self._uri

    @property
    def client(self) -> AsyncIOMotorClient | None:
        """
        @brief Returns the underlying AsyncIOMotorClient instance, or None if closed.

        @details
        Exposes the raw Motor client for use by AsyncMongoDBDatabase when
        constructing database and collection references. Returns None if
        close() has already been called, which is used by get_database()
        and get_collection() to detect and reject use-after-close access.

        @return The AsyncIOMotorClient instance, or None if the client has been closed.
        """
        return self._client

    @property
    def is_connected(self) -> bool:
        """
        @brief Returns whether the client is in an open (non-closed) state.

        @details
        Returns True if the AsyncIOMotorClient instance is still alive (i.e.
        close() has not been called), and False if close() has been called and
        self._client has been set to None.

        Note that this property reflects the client object's lifecycle state,
        not the real-time status of the underlying TCP connection to Atlas.
        Motor manages connection pool health internally — a True value here
        does not guarantee that the next database operation will succeed
        (e.g. if the network is temporarily unavailable). Use ping() to
        verify actual database reachability.

        @return True if the client has not been closed, False otherwise.
        """
        return self._client is not None

    # ── Lifecycle ───────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """
        @brief No-op connect implementation for the Motor async driver.

        @details
        Motor uses a lazy connection model — the TCP connection to Atlas is
        established automatically on the first real database operation, not
        at client construction time. There is no explicit "connect" step
        required or available in the Motor API.

        This method satisfies the AsyncDatabaseClientBase abstract interface
        contract. Callers should follow connect() with ping() during startup
        to eagerly verify connectivity rather than relying on the first real
        operation to surface connection failures.
        """
        pass

    async def close(self) -> None:
        """
        @brief Closes the Motor connection pool and releases all associated resources.

        @details
        Calls Motor's synchronous close() method on the underlying client,
        which signals the connection pool to stop accepting new operations
        and release all pooled TCP connections to Atlas.

        After close() returns, self._client is set to None. Any subsequent
        calls to get_database(), get_collection(), or ping() will raise
        VitaSyncDatabaseDisconnectedError, converting use-after-close bugs
        into immediate, obvious failures rather than cryptic driver errors.

        Calling close() on an already-closed client (self._client is None)
        is a safe no-op — the method returns immediately without raising.

        @note Motor's close() returns None (not a coroutine) in the version of
              Motor used by VitaSync. This method is declared async to satisfy
              the abstract interface, but close() is called without await.
              See module-level docstring for details.
        """
        if self._client is None:
            return

        self._client.close()
        self._client = None

    async def ping(self) -> None:
        """
        @brief Sends a ping command to MongoDB Atlas to verify connectivity and credentials.

        @details
        Issues the MongoDB 'ping' administrative command against the admin database.
        This is the lightest-weight operation available for verifying that:
          1. The network path to the Atlas cluster is open.
          2. The credentials embedded in the URI are accepted by Atlas.
          3. The Atlas cluster is healthy and responding to commands.

        Called once during application startup (in main.py's lifespan context
        manager) before the server begins accepting HTTP requests. If ping()
        raises, the startup is aborted — it is preferable to fail loudly and
        immediately at startup rather than to begin serving patient data requests
        with a broken or misconfigured database connection.

        @throws VitaSyncDatabaseDisconnectedError If the client has already been
                closed (self._client is None) before ping() is called.
        @throws VitaSyncDatabaseExecutionError If the ping command fails due to
                network unavailability, authentication failure, Atlas cluster
                unavailability, or any other PyMongo/Motor-level error. The
                original PyMongoError is attached as the __cause__ for debugging.
        """
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            await self._client.admin.command('ping')

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    # ── Accessors ───────────────────────────────────────────────────────────────

    def get_database(self, database: str) -> AsyncIOMotorDatabase:
        """
        @brief Returns a Motor database reference for the given database name.

        @details
        Accesses the named database on the connected Atlas cluster via Motor's
        bracket notation. This operation is synchronous and does not perform
        a network round trip — Motor returns a lightweight reference object
        that defers all actual I/O to subsequent collection operations.

        The returned AsyncIOMotorDatabase object is used by AsyncMongoDBDatabase
        to construct collection references for each repository.

        @param database The name of the MongoDB database to access
                        (e.g. 'vitasync' for the main application database).

        @return An AsyncIOMotorDatabase reference for the named database.

        @throws VitaSyncDatabaseDisconnectedError If the client has been closed
                prior to this call.
        @throws VitaSyncDatabaseExecutionError If Motor raises a PyMongoError
                while accessing the database reference (rare for this sync operation,
                but caught defensively for interface consistency).
        """
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            return self._client[database]

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    def get_collection(
        self,
        database: str,
        collection: str
    ) -> AsyncIOMotorCollection:
        """
        @brief Returns a Motor collection reference for the given database and collection names.

        @details
        Accesses the named collection within the named database on the connected
        Atlas cluster via Motor's nested bracket notation. Like get_database(),
        this operation is synchronous and returns a lightweight reference object
        without performing any network I/O.

        The returned AsyncIOMotorCollection is passed directly to repository
        constructors (e.g. PatientRepository, VisitRepository) during application
        startup, where it is stored as self._collection for use in all subsequent
        async CRUD operations.

        @param database   The name of the MongoDB database containing the collection
                          (e.g. 'vitasync').
        @param collection The name of the collection to access within the database
                          (e.g. 'patients', 'visits').

        @return An AsyncIOMotorCollection reference for the named collection.

        @throws VitaSyncDatabaseDisconnectedError If the client has been closed
                prior to this call.
        @throws VitaSyncDatabaseExecutionError If Motor raises a PyMongoError
                while accessing the collection reference.
        """
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            return self._client[database][collection]

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
            