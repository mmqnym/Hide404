from db_manager.db_manager import Database
from share.types import EventMetadata, List
from utils import common


class EventManager(Database):
    """
    Event DB Controller
    """

    def __init__(self, db_path: str, max_connections: int = 1) -> None:
        super().__new__(self.__class__, db_path, max_connections)

    def new_event_type(self, event_type: str) -> None:
        """
        Creates a new event type table in the database.

        This method uses a transaction to execute a SQL command that creates a
        table with the specified name `event_type`.

        **Note**: The table is created with the following columns:
            - `event_id`: A unique identifier for each event.
            - `status`: The status of the event.
            - `detail`: The detail of the event.
            - `added_at`: The timestamp when the event was added.

        Args:
            event_type (str): The name of the event type table to be created.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {event_type} (
                        event_id CHAR(26) PRIMARY KEY,
                        status VARCHAR(16) NOT NULL,
                        detail TEXT,
                        added_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """
            )

    def list_event_types(self) -> List[str]:
        """
        List all event types in the database.

        This method executes a SQL command to retrieve all table names from the
        database and returns them as a list.

        Returns:
            List[str]: A list of event type names.
        """

        with self.transaction() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]

    def add_event(self, event_type: str, metadata: EventMetadata) -> None:
        """
        Add an event to the event table.

        This method executes a SQL command to insert an event into the specified
        event type table.

        Args:
            event_type (str): The name of the event type table to add the event to.
            metadata (EventMetadata): The metadata of the event to be added.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(
                f"""
                    INSERT INTO {event_type} (
                        event_id, status, detail
                    ) VALUES (
                        ?, ?, ?
                    )
                """,
                (
                    metadata.event_id,
                    metadata.status,
                    common.marshall_json(metadata.detail),
                ),
            )

    def update_event(self, event_type: str, metadata: EventMetadata) -> None:
        """
        Update an event in the specified event type table.

        This method executes a SQL command to update the specified event in the
        specified event type table.

        Args:
            event_type (str): The name of the event type table to update the event in.
            metadata (EventMetadata): The metadata of the event to be updated.

        Returns:
            None
        """
        with self.transaction() as conn:
            conn.execute(
                f"""
                    UPDATE {event_type}
                    SET status = ?, detail = ?
                    WHERE event_id = ?
                """,
                (
                    metadata.status,
                    common.marshall_json(metadata.detail),
                    metadata.event_id,
                ),
            )

    def get_event_list(self, event_type: str) -> List[dict]:
        """
        Get a list of events in the specified event type table.

        This method executes a SQL command to retrieve all events from the
        specified event type table and returns them as a list.

        Args:
            event_type (str): The name of the event type table to retrieve events from.

        Returns:
            List[dict]: A list of dictionaries where each dictionary represents an event.
        """

        with self.transaction() as conn:
            cursor = conn.execute(f"SELECT * FROM {event_type}")
            result = [dict(row) for row in cursor.fetchall()]
            for row in result:
                row["detail"] = common.unmarshall_json(row["detail"])

            return result

    def get_event(self, event_type: str, event_id: str) -> dict:
        """
        Get an event by its event_id from the specified event type table.

        This method executes a SQL command to retrieve an event from the
        specified event type table and returns it as a dictionary.

        Args:
            event_type (str): The name of the event type table to retrieve the
                event from.
            event_id (str): The event_id of the event to retrieve.

        Returns:
            dict: A dictionary representing the event, or None if the event does
                not exist.
        """
        with self.transaction() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {event_type} WHERE event_id = ?", (event_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["detail"] = common.unmarshall_json(result["detail"])
                return result

            return None

    def delete_event(self, event_type: str, event_id: str) -> None:
        """
        Delete an event by its event_id from the specified event type table.

        Args:
            event_type (str): The name of the event type table to delete the event from.
            event_id (str): The event_id of the event to delete.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(f"DELETE FROM {event_type} WHERE file_id = ?", (event_id,))

    def clean_expired_events(self, event_type: str, max_age: int) -> None:
        """
        Clean expired events from the specified event type table.

        This method deletes all events from the specified event type table that
        are older than the specified max_age.

        Args:
            event_type (str): The name of the event type table to clean.
            max_age (int): The maximum age of events in seconds. All events that
                are older than this will be deleted.

        Returns:
            None
        """
        with self.transaction() as conn:
            conn.execute(
                f"""
                    DELETE FROM events 
                    WHERE event_type = ?
                    AND added_at < strftime('%s', 'now') - ?
                """,
                (event_type, max_age),
            )
