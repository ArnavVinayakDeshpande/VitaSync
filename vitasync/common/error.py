"""
@file errors.py
@brief Centralised exception hierarchy for the VitaSync application.

@details
All application-level exceptions in VitaSync inherit from VitaSyncError,
providing a single catch-all for any error originating within the system.
The hierarchy is organised into three branches:

  VitaSyncError
  ├── VitaSyncDatabaseError          (database layer failures)
  │   ├── VitaSyncDatabaseDisconnectedError
  │   ├── VitaSyncDatabaseTimeoutError
  │   ├── VitaSyncDatabaseUnreachableError
  │   ├── VitaSyncDuplicateEntryError
  │   ├── VitaSyncDatabaseOperationError
  │   └── VitaSyncDatabaseExecutionError
  ├── VitaSyncValidationError        (data integrity failures)
  └── VitaSyncManagerError           (business logic failures)
      ├── VitaSyncNotFoundError
      ├── VitaSyncIDGenerationError
      └── VitaSyncInvalidInputsError

Intended wrapping chain across layer boundaries:

  PyMongo exception               Repository raises                  Router converts to
  ──────────────────────────────────────────────────────────────────────────────────────
  ServerSelectionTimeoutError  →  VitaSyncDatabaseUnreachableError  →  HTTP 503
  NetworkTimeout               →  VitaSyncDatabaseTimeoutError      →  HTTP 504
  DuplicateKeyError            →  VitaSyncDuplicateEntryError       →  HTTP 409
  OperationFailure             →  VitaSyncDatabaseOperationError    →  HTTP 500
  PyMongoError (other)         →  VitaSyncDatabaseExecutionError    →  HTTP 500
  client / repo is None        →  VitaSyncDatabaseDisconnectedError →  HTTP 503
  Pydantic ValidationError     →  VitaSyncValidationError           →  HTTP 500
  Manager business rule        →  VitaSyncManagerError              →  HTTP 400/404/500

@note VitaSyncValidationError is NOT raised for inbound HTTP request bodies.
      FastAPI intercepts Pydantic ValidationError on request bodies automatically
      and returns a 422 Unprocessable Entity before the route handler runs.
      VitaSyncValidationError is only raised when reconstructing a Pydantic
      model from a raw MongoDB document inside a repository method, where
      FastAPI has no visibility.
"""


# ── Base ───────────────────────────────────────────────────────────────────────

class VitaSyncError(Exception):
    """
    @brief Base class for all VitaSync application exceptions.

    @details
    Every exception raised intentionally by VitaSync code inherits from this
    class. Catching VitaSyncError at the router layer provides a safe fallback
    that guarantees no internal exception leaks to the HTTP response as an
    unhandled 500 with a raw Python traceback.

    Driver-level exceptions (PyMongoError, Pydantic ValidationError) are always
    wrapped in a VitaSyncError subclass before crossing a layer boundary —
    raw third-party exceptions should never propagate past the repository layer.
    """
    pass


# ── Database Errors ────────────────────────────────────────────────────────────

class VitaSyncDatabaseError(VitaSyncError):
    """
    @brief Base class for all database-layer exceptions in VitaSync.

    @details
    Raised by repository methods and the database client when a Motor or
    PyMongo operation fails. Manager methods catch VitaSyncDatabaseError
    (or specific subclasses) and either handle the failure or re-raise it
    wrapped in a VitaSyncManagerError for the router to convert to an
    appropriate HTTP response.

    Never raised directly — always raise a specific subclass so that callers
    can distinguish between distinct failure modes (timeout vs unreachable
    vs duplicate vs generic execution error).
    """
    pass


class VitaSyncDatabaseDisconnectedError(VitaSyncDatabaseError):
    """
    @brief Raised when a database operation is attempted on an uninitialized
           or already-closed client or repository.

    @details
    Fired in two situations:

      1. AsyncMongoDBClient.ping(), get_database(), or get_collection() are
         called after close() has been called, setting self._client to None.

      2. A repository method is called before repository.initialize() has
         completed, i.e. self._initialized is False.

    This exception indicates a lifecycle ordering bug — the caller attempted
    to use the database before it was ready or after it was torn down.
    In production, startup ordering in the FastAPI lifespan context manager
    should prevent this from ever being raised.
    """

    def __init__(self, message: str = 'Database client is not connected or has already been closed.'):
        super().__init__(message)


class VitaSyncDatabaseTimeoutError(VitaSyncDatabaseError):
    """
    @brief Raised when a database operation times out mid-flight.

    @details
    Wraps PyMongo's NetworkTimeout, which is raised when an operation
    successfully reached Atlas but did not receive a response within the
    configured socket timeout period. This is distinct from
    VitaSyncDatabaseUnreachableError, which covers the case where Atlas
    could not be reached at all.

    Common causes: Atlas cluster under heavy load, a long-running aggregation
    pipeline exceeding the socket timeout, or transient network degradation
    after the connection was established.

    @param original_exception The original PyMongo NetworkTimeout instance,
                              stored as self.original_exception for debugging.
    """

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        super().__init__(
            f'Database operation timed out before a response was received. '
            f'The Atlas cluster may be under load or the operation exceeded '
            f'the configured socket timeout. '
            f'Original error: {str(original_exception)}'
        )


class VitaSyncDatabaseUnreachableError(VitaSyncDatabaseError):
    """
    @brief Raised when the MongoDB Atlas cluster cannot be reached at all.

    @details
    Wraps PyMongo's ServerSelectionTimeoutError, which fires when the driver
    exhausts all attempts to find a suitable server within the configured
    serverSelectionTimeoutMS window.

    Common causes:
      - Incorrect cluster hostname in MONGODB_URI
      - Client IP not whitelisted in Atlas Network Access settings
      - Atlas cluster is paused or deleted
      - DNS resolution failure for the SRV record

    This exception is most commonly raised during the startup ping() call
    in the FastAPI lifespan context manager. If raised there, the application
    startup should be aborted immediately rather than attempting to serve
    requests with a broken database connection.

    @param original_exception The original ServerSelectionTimeoutError instance,
                              stored as self.original_exception for debugging.
    """

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        super().__init__(
            f'Could not reach the MongoDB Atlas cluster. '
            f'Verify that the cluster hostname in MONGODB_URI is correct, '
            f'the cluster is running and not paused, and the server IP is '
            f'whitelisted in Atlas Network Access. '
            f'Original error: {str(original_exception)}'
        )


class VitaSyncDuplicateEntryError(VitaSyncDatabaseError):
    """
    @brief Raised when a write operation violates a unique index constraint.

    @details
    Wraps PyMongo's DuplicateKeyError, which is raised by MongoDB when an
    insert or update would produce a duplicate value on a field covered by
    a unique index.

    In VitaSync, unique indexes exist on the following fields:
      - patients.pid              (always unique)
      - patients.mobile_number    (always unique)
      - patients.abha_kyc.abha_number   (sparse unique)
      - patients.abha_kyc.abha_address  (sparse unique)
      - patients.abha_kyc.demographic_data.mobile_number (sparse unique)
      - visits.vid                (always unique)

    The field attribute identifies which index was violated, extracted from
    the DuplicateKeyError message by the repository layer. The manager layer
    uses this to decide whether to retry (pid collision — regenerate and retry)
    or surface the error (mobile number collision — genuine duplicate patient).

    @param field               The name of the field whose unique constraint
                               was violated (e.g. 'pid', 'mobile_number').
    @param original_exception  The original DuplicateKeyError instance.
    """

    def __init__(self, field: str, original_exception: Exception):
        self.field = field
        self.original_exception = original_exception
        super().__init__(
            f'A record with this value for "{field}" already exists. '
            f'Duplicate values are not permitted on this field.'
        )


class VitaSyncDatabaseOperationError(VitaSyncDatabaseError):
    """
    @brief Raised when the MongoDB server explicitly rejects an operation.

    @details
    Wraps PyMongo's OperationFailure, which is raised when the Atlas server
    receives and processes a command but returns an error response. This is
    distinct from network-level failures (timeout, unreachable) — the server
    was reached but refused or failed to execute the operation.

    Common causes:
      - Authentication failure (wrong database user credentials)
      - Insufficient role permissions for the operation
      - Write concern not satisfiable (e.g. w:majority on a single-node cluster)
      - Malformed aggregation pipeline rejected by the server
      - Transaction commit failure

    @param original_exception The original OperationFailure instance,
                              stored as self.original_exception for debugging.
    """

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        super().__init__(
            f'The database server rejected the operation. '
            f'This may indicate an authentication failure, insufficient '
            f'permissions for the database user, or a malformed operation. '
            f'Original error: {str(original_exception)}'
        )


class VitaSyncDatabaseExecutionError(VitaSyncDatabaseError):
    """
    @brief Catch-all for any PyMongoError not covered by a more specific subclass.

    @details
    Wraps the base PyMongoError and serves as the fallback in repository
    except blocks, ensuring that no raw Motor or PyMongo exception escapes
    the repository layer even in unanticipated failure scenarios.

    Repository methods should always catch specific PyMongo exceptions first
    (DuplicateKeyError, ServerSelectionTimeoutError, NetworkTimeout,
    OperationFailure) and only fall through to catching the base PyMongoError
    for this wrapper as a last resort.

    @param original_exception The original PyMongoError instance,
                              stored as self.original_exception for debugging.
    """

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        super().__init__(
            f'An unexpected database error occurred. '
            f'Original error: {str(original_exception)}'
        )


# ── Validation Errors ──────────────────────────────────────────────────────────

class VitaSyncValidationError(VitaSyncError):
    """
    @brief Raised when a Pydantic model fails to construct from a MongoDB document.

    @details
    Wraps Pydantic's ValidationError for the specific case where a raw
    MongoDB document (returned by Motor as a plain dict) cannot be validated
    into the expected Pydantic model in a repository get() or getall() method.

    This exception is NOT raised for inbound HTTP request body validation.
    FastAPI intercepts Pydantic ValidationError on request bodies automatically
    before the route handler runs and returns a 422 Unprocessable Entity
    response with structured field-level error details.

    VitaSyncValidationError is only raised in the repository layer, where
    FastAPI has no visibility, when reconstructing models like Patient or Visit
    from raw MongoDB documents. If this exception is raised in production, it
    typically indicates a schema mismatch between the stored document and the
    current Pydantic model definition — most commonly caused by a model change
    that was not reflected in existing database documents.

    @param original_exception The original Pydantic ValidationError instance,
                              stored as self.original_exception for debugging.
    """

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        super().__init__(
            f'A database document failed Pydantic validation. '
            f'This may indicate a schema mismatch between the stored document '
            f'and the current model definition. '
            f'Original error: {str(original_exception)}'
        )


# ── Manager Errors ─────────────────────────────────────────────────────────────

class VitaSyncManagerError(VitaSyncError):
    """
    @brief Base class for all manager-layer exceptions in VitaSync.

    @details
    Raised by manager methods when a business logic rule is violated, or when
    a database-layer exception is caught and needs to be re-raised with
    additional context for the router layer to convert to an HTTP response.

    Router methods catch VitaSyncManagerError (or specific subclasses) and
    map them to appropriate HTTP status codes and response detail messages.
    """
    pass


class VitaSyncNotFoundError(VitaSyncManagerError):
    """
    @brief Raised when an operation targets a document that does not exist.

    @details
    Raised by manager methods when a get(), update(), or delete() operation
    is performed with an identifier that does not match any document in the
    collection. The repository layer surfaces this via a deleted_count or
    matched_count of zero on update/delete operations, or a None return
    value on find operations.

    Carries the entity type and the identifier that was not found, allowing
    the router to construct a precise and actionable 404 error message.

    @param entity     The type of entity that was not found (e.g. 'Patient', 'Visit').
    @param identifier The identifier value that was searched for
                      (e.g. 'PAT-260702-K7M2X9').
    """

    def __init__(self, entity: str, identifier: str):
        self.entity = entity
        self.identifier = identifier
        super().__init__(
            f'{entity} with identifier "{identifier}" does not exist. '
            f'Verify the identifier and try again.'
        )


class VitaSyncIDGenerationError(VitaSyncManagerError):
    """
    @brief Raised when a unique ID cannot be generated within the retry limit.

    @details
    Raised by PatientManager.create() and VisitManager.create() when all
    attempts to generate a unique ID result in a VitaSyncDuplicateEntryError
    on the ID field specifically, exhausting the configured max_retries limit.

    In practice this should be extremely rare given the random suffix space
    (31^6 ≈ 887 million combinations per date for a 6-character suffix).
    If this exception is raised in production, it most likely indicates an
    unusually high volume of registrations on a single date, a bug in the
    ID generation logic, or a corrupted unique index.

    @param entity      The entity type for which ID generation failed
                       (e.g. 'Patient', 'Visit').
    @param max_retries The number of generation attempts that were made
                       before giving up.
    """

    def __init__(self, entity: str, max_retries: int):
        self.entity = entity
        self.max_retries = max_retries
        super().__init__(
            f'Failed to generate a unique ID for {entity} after {max_retries} '
            f'attempts. All generated IDs collided with existing records. '
            f'This is highly unlikely under normal conditions and may indicate '
            f'an issue with the ID generation logic or unique index.'
        )


class VitaSyncInvalidInputsError(VitaSyncManagerError):
    """
    @brief Raised when manager-layer inputs pass Pydantic validation but
           violate a business rule that cannot be expressed as a field constraint.

    @details
    This exception covers the gap between Pydantic validation (which enforces
    type correctness and field-level constraints) and true business logic
    validation (which may involve cross-field rules, domain-specific invariants,
    or contextual constraints that depend on runtime state).

    Examples of conditions that trigger this exception:

      - A getall() call receives age < 0, which is structurally a valid int
        but semantically meaningless as an age filter.
      - An update() call is made where every optional field is None, producing
        an empty $set payload that MongoDB would reject.
      - A conditions update receives an empty set after the caller explicitly
        provided one (distinct from a missing field, which Pydantic catches).
      - A date range filter where the start date is after the end date.

    Carries a list of the offending input field names and a human-readable
    message describing the violated rule, so the router can construct a
    precise 400 Bad Request response without needing to parse the exception
    message string.

    @param fields  A list of the input field names that violated the business
                   rule (e.g. ['age'], ['start_date', 'end_date']). Used by
                   the router to identify which part of the request was invalid.
    @param message A human-readable description of the violated rule, written
                   from the caller's perspective (e.g. 'Age filter must be
                   greater than zero.').
    """

    def __init__(self, fields: list[str], message: str):
        self.fields = fields
        super().__init__(
            f'Invalid input{"s" if len(fields) != 1 else ""} '
            f'for field{"s" if len(fields) != 1 else ""} '
            f'[{", ".join(f"{chr(34)}{f}{chr(34)}" for f in fields)}]: '
            f'{message}'
        )
