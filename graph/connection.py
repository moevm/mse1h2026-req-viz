import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any

from neo4j import (
    Driver,
    GraphDatabase,
    ManagedTransaction,
    Result,
    Session,
)
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

from graph.exceptions import GraphConnectionError, QueryError

logger = logging.getLogger(__name__)

_RETRYABLE_EXCEPTIONS = (
    ServiceUnavailable,
    SessionExpired,
    TransientError,
    OSError,
)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
):
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            delay = base_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except _RETRYABLE_EXCEPTIONS as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1fs…",
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            raise GraphConnectionError(
                f"All {max_attempts} attempts failed: {last_exc}"
            ) from last_exc

        return wrapper

    return decorator


class Neo4jConnection:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: float = 60.0,
        max_transaction_retry_time: float = 30.0,
        connection_timeout: float = 30.0,
    ) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Driver | None = None

        self._pool_size = max_connection_pool_size
        self._acquisition_timeout = connection_acquisition_timeout
        self._max_retry_time = max_transaction_retry_time
        self._connection_timeout = connection_timeout

    @with_retry(max_attempts=3, base_delay=2.0)
    def connect(self) -> None:
        if self._driver is not None:
            logger.debug("Driver already exists, skipping connect.")
            return

        logger.info("Connecting to Neo4j at %s …", self._uri)

        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
                max_connection_pool_size=self._pool_size,
                connection_acquisition_timeout=self._acquisition_timeout,
                max_transaction_retry_time=self._max_retry_time,
                connection_timeout=self._connection_timeout,
            )
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")

        except AuthError as exc:
            self.close()
            raise GraphConnectionError(f"Authentication failed: {exc}") from exc
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed.")

    def __enter__(self) -> "Neo4jConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            raise GraphConnectionError("Not connected. Call connect() first.")
        return self._driver

    @property
    def is_connected(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    @contextmanager
    def session(self, **kwargs: Any):
        kwargs.setdefault("database", self._database)
        session: Session = self.driver.session(**kwargs)
        try:
            yield session
        finally:
            session.close()

    @with_retry(max_attempts=3, base_delay=1.0)
    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        logger.debug("READ  %s | params=%s", query, parameters)

        def _work(tx: ManagedTransaction) -> list[dict[str, Any]]:
            result: Result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        try:
            with self.session() as session:
                return session.execute_read(_work)
        except ClientError as exc:
            raise QueryError(f"Read query failed: {exc}") from exc

    @with_retry(max_attempts=3, base_delay=1.0)
    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        logger.debug("WRITE %s | params=%s", query, parameters)

        def _work(tx: ManagedTransaction) -> list[dict[str, Any]]:
            result: Result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        try:
            with self.session() as session:
                return session.execute_write(_work)
        except ClientError as exc:
            raise QueryError(f"Write query failed: {exc}") from exc
