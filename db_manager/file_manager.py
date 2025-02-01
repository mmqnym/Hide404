import sqlite3
from db_manager.db_manager import Database
from share.types import FileMetadata, Tuple, List


class FileManager(Database):
    """
    File DB Controller
    """

    def __init__(self, db_path: str, max_connections: int = 1) -> None:
        super().__new__(self.__class__, db_path, max_connections)

    def new_collection(self, collection_name: str) -> None:
        """
        Create a new collection in the database

        **Note**: The collection will have the following columns:
            - `file_id`: A unique identifier for the file
            - `file_hash`: The hash of the file content
            - `file_path`: The path to the file
            - `file_name`: The original name of the file
            - `file_size`: The size of the file(in bytes)
            - `upload_id`: An event ID associated with the upload record of this file
            - `added_at`: The timestamp when the event was added.

        Args:
            collection_name (str): The name of the collection

        Returns:
            None
        """
        with self.transaction() as conn:
            conn.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {collection_name} (
                        file_id CHAR(26) PRIMARY KEY,
                        file_hash TEXT,
                        file_path TEXT,
                        file_name TEXT,
                        file_size INTEGER,
                        upload_id CHAR(26),
                        added_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """
            )

    def drop_collection(self, collection_name: str) -> None:
        """
        Drop a collection from the database.

        This method removes the specified collection (table) if it exists
        in the database. If the collection does not exist, no errors are raised.

        Args:
            collection_name (str): The name of the collection to be dropped.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {collection_name}")

    def list_collections(self) -> List[str]:
        """
        List all collections in the database.

        This method executes a SQL command to retrieve all table names from the
        database and returns them as a list.

        Returns:
            List[str]: A list of collection names.
        """

        with self.transaction() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]

    def add_file(self, collection_name: str, metadata: FileMetadata):
        """
        Add a file to the specified collection.

        This method executes a SQL command to insert a file into the specified
        collection table.

        Args:
            collection_name (str): The name of the collection to add the file to.
            metadata (FileMetadata): The metadata of the file to be added.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(
                f"""
                    INSERT INTO {collection_name} (
                        file_id, file_hash, file_path, file_name, file_size, upload_id
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?
                    )
                """,
                (
                    metadata.file_id,
                    metadata.file_hash,
                    metadata.file_path,
                    metadata.file_name,
                    metadata.file_size,
                    metadata.upload_id,
                ),
            )

    def get_file_list(
        self, collection_name: str, show_simple: bool = False
    ) -> Tuple[list, str]:
        """
        Retrieve the list of files from a specified collection.

        This method executes a SQL command to retrieve all files from the
        specified collection and returns them as a list of dictionaries.

        Args:
            collection_name (str): The name of the collection whose files are to be retrieved.
            show_simple (bool, optional): If True, only the file_id and file_name
                                        of each file are returned. Defaults to False.

        Returns:
            Tuple[list, str]: A tuple containing the list of files and a status message.
                            If the collection is found, the list of files is returned;
                            otherwise, None is returned with an error message.
        """

        with self.transaction() as conn:
            try:
                cursor = conn.execute(f"SELECT * FROM {collection_name}")
                result = [dict(row) for row in cursor.fetchall()]

                # only keep id and name
                if show_simple:
                    result = [
                        {"file_id": row["file_id"], "file_name": row["file_name"]}
                        for row in result
                    ]

                return (result, "Found the collection")
            except sqlite3.OperationalError as e:
                if "no such table" in e.args[0]:
                    return (None, "Collection not found")
                else:
                    raise

    def get_file_metadata(self, collection_name: str, file_id: str) -> Tuple[dict, str]:
        """
        Retrieve the metadata of a file from a specified collection.

        This method executes a SQL command to retrieve the metadata of a file
        from the specified collection and returns it as a dictionary.

        Args:
            collection_name (str): The name of the collection whose file metadata is to be retrieved.
            file_id (str): The id of the file whose metadata is to be retrieved.

        Returns:
            Tuple[dict, str]: A tuple containing the metadata of the file as a dictionary
                              and a status message. If the file is found, its metadata is returned;
                              otherwise, None is returned with an error message.
        """
        with self.transaction() as conn:
            try:
                cursor = conn.execute(
                    f"SELECT * FROM {collection_name} WHERE file_id = ?", (file_id,)
                )
                row = cursor.fetchone()

                if row:
                    return (dict(row), "Found the file")
                return None, "File not found"
            except sqlite3.OperationalError as e:
                if "no such table" in e.args[0]:
                    return (None, "Collection not found")
                raise

    def delete_file(self, collection_name: str, file_id: str) -> None:
        """
        Delete a file record from a specified collection.

        This method executes a SQL command to delete a file from the
        specified collection based on the file_id.

        Args:
            collection_name (str): The name of the collection from which the file is to be deleted.
            file_id (str): The id of the file to be deleted.

        Returns:
            None
        """

        with self.transaction() as conn:
            conn.execute(f"DELETE FROM {collection_name} WHERE file_id = ?", (file_id,))
