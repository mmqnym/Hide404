import sqlite3
from queue import Queue
from contextlib import contextmanager
from share.types import Optional, Generator, Any
from share.var import APP_LOG


class DatabaseConnection:
    """
    Abstracted Database Connection class
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.in_use = False


class ConnectionPool:
    """
    SQLite Connection Pool class
    """

    def __init__(
        self, db_path: str, max_connections: int = 5, connection_timeout: float = 15.0
    ):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.pool: Queue = Queue(maxsize=max_connections)
        self._init_pool()

    def _init_pool(self) -> None:
        """
        Initializes the connection pool with the specified number of connections
        """
        APP_LOG.info(
            f"Initializing connection pool with {self.max_connections} connections"
        )
        for _ in range(self.max_connections):
            connection = self._create_connection()
            self.pool.put(connection)

    def _create_connection(self) -> DatabaseConnection:
        """
        Creates a new database connection

        This method creates a new SQLite connection, sets the row factory to
        sqlite3.Row, and sets the following PRAGMAs:

        - journal_mode=WAL
        - busy_timeout=5000
        - foreign_keys=ON

        The isolation level is set to "IMMEDIATE"

        Returns a DatabaseConnection object with the created connection
        """
        conn = sqlite3.connect(self.db_path, timeout=self.connection_timeout)

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.isolation_level = "IMMEDIATE"

        return DatabaseConnection(connection=conn)

    @contextmanager
    def get_connection(self) -> Generator[Any | DatabaseConnection, Any, None]:
        """
        Get a connection from the pool

        This method gets a connection from the pool, sets the in_use flag to True,
        and yields the connection to the caller.
        If an error occurs while using the connection, the connection is closed and
        a new connection is created. Then, the error is re-raised.
        """

        connection: Optional[DatabaseConnection] = None
        try:
            connection = self.pool.get()
            connection.in_use = True
            APP_LOG.debug("Acquired connection from pool")

            yield connection.connection

        except Exception as e:
            APP_LOG.error(f"Error while using connection: {e}")
            if connection:
                try:
                    connection.connection.close()
                    connection = self._create_connection()
                except Exception as close_error:
                    APP_LOG.error(f"Error while closing connection: {close_error}")
            raise

        finally:
            if connection:
                connection.in_use = False
                self.pool.put(connection)
                APP_LOG.debug("Released connection back to pool")

    def close_all(self) -> None:
        """
        Closes all connections in the pool

        This method iterates through the connection pool, retrieves each connection,
        and closes it. If an error occurs while closing a connection, it logs the error.
        """

        APP_LOG.info("Closing all connections in the pool")
        while not self.pool.empty():
            try:
                connection = self.pool.get_nowait()
                connection.connection.close()
            except Exception as e:
                APP_LOG.error(f"Error while closing connection: {e}")


class Database:
    """
    Database class
    """
    _instance: Optional[ConnectionPool] = None

    def __new__(cls, db_path: str, max_connections: int = 1):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pool = ConnectionPool(
                db_path=db_path, max_connections=max_connections
            )
        return cls._instance

    @contextmanager
    def transaction(self):
        """Context manager for database transactions

        This context manager retrieves a connection from the pool, and commits
        or rolls back the transaction based on whether an exception is raised.

        Example:

            with db.transaction() as conn:
                conn.execute("INSERT INTO table (column) VALUES (?)", ("value",))

        If an exception is raised within the context manager, the transaction
        is rolled back and the exception is re-raised.
        Otherwise, the transaction is committed.
        """

        with self.pool.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                APP_LOG.error(f"Transaction rolled back due to an error {str(e)}")
                raise
