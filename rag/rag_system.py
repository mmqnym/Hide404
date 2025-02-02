import nltk
import torch

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)

import os
import chromadb
from chromadb import Collection
from chromadb.config import Settings
from langchain_community.document_loaders import (
    DirectoryLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    # PDFMinerLoader,
    # UnstructuredWordDocumentLoader,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI
from share.types import List, Dict, Type, Tuple
from share.var import APP_LOG


class RAGSystem:
    def __init__(self, openai_api_key: str, db_dir: str):
        self.openai_api_key = openai_api_key
        self.db_dir = db_dir

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        )

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openai_api_key,
        )

        self.chroma_client = chromadb.PersistentClient(
            path=db_dir, settings=Settings(anonymized_telemetry=False)
        )
        self.vector_stores: Dict[str, Chroma] = {}

        self.supported_loaders: Dict[str, Type] = {
            ".markdown": UnstructuredMarkdownLoader,
            ".txt": TextLoader,
            # ".pdf": PDFMinerLoader,
            # ".docx": UnstructuredWordDocumentLoader,
            # ".doc": UnstructuredWordDocumentLoader,
        }

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )

    def init_vector_store(self) -> None:
        """
        Initialize the vector store from the database.

        This method loads all existing collections from the database and stores them in the vector_stores attribute.

        Args:
            None

        Returns:
            None
        """
        existing_collections = self.chroma_client.list_collections()

        if not existing_collections:
            APP_LOG.info("No collections found in DB. Skipping initialization...")
            return

        for col in existing_collections:
            self.vector_stores[col.name] = Chroma(
                client=self.chroma_client,
                collection_name=col.name,
                collection_metadata=col.metadata,
                embedding_function=self.embeddings,
            )
            APP_LOG.info(f"Loaded collection: {col.name}")

        APP_LOG.info(f"Done. Loaded {len(self.vector_stores)} collections from DB.")

    def create_collection(
        self,
        collection_name: str,
        collection_metadata: dict = None,
        documents_dir=os.path.join("upload", "default"),
    ) -> Tuple[dict | None, str]:
        """
        Create a new collection or overwrite an existing one.

        This function loads documents from the specified directory, creates a new
        vector store collection, and adds it to the internal vector stores dictionary.
        If a collection with the specified name already exists, it will be deleted
        and overwritten with the new collection.

        Args:
            collection_name (str): The name of the collection to create or overwrite.
            collection_metadata (dict, optional): Metadata for the collection.
                Defaults to None.
            documents_dir (str, optional): The directory containing documents to load.
                Defaults to "upload/default".

        Returns:
            Tuple[dict | None, str]: A tuple containing the collection information
            if successful, or None if an error occurred, and a status message
            indicating the result of the operation.
        """

        is_overwrite = False

        try:
            documents = self.load_documents(documents_dir)

            if not documents:
                raise ValueError(f"No documents found in directory: {documents_dir}")

            if collection_name in self.vector_stores:
                is_overwrite = True
                APP_LOG.warning(
                    f"Collection `{collection_name}` already exists, it will be overwritten"
                )
                self.delete_collection(collection_name)

            self.vector_stores[collection_name] = Chroma.from_documents(
                client=self.chroma_client,
                documents=documents,
                embedding=self.embeddings,
                collection_name=collection_name,
                collection_metadata=collection_metadata,
            )

            return (
                self.get_collection_info(collection_name),
                (
                    "Collection relearned successfully"
                    if is_overwrite
                    else "Collection created successfully"
                ),
            )
        except Exception as e:
            err_msg = f"Error creating collection: {str(e)}"
            APP_LOG.error(err_msg)
            return (None, err_msg)

    def load_documents(
        self, documents_dir: str = os.path.join("upload", "default")
    ) -> List:
        """
        Load documents from a specified directory and split them into chunks.

        This function iterates through all supported file extensions, loads
        documents from the specified directory using the appropriate loader
        class, and splits the documents into chunks using the configured
        text splitter.

        Args:
            documents_dir (str, optional): The directory containing documents to
                load. Defaults to "upload/default".

        Returns:
            List: A list of chunked documents, or an empty list if no documents
                were loaded. If an error occurs, an exception is raised.
        """
        all_documents = []

        try:
            for file_extension, loader_class in self.supported_loaders.items():
                try:
                    loader = DirectoryLoader(
                        documents_dir,
                        glob=f"**/*{file_extension}",
                        loader_cls=loader_class,
                    )

                    documents = loader.load()
                    if documents:
                        APP_LOG.info(f"Loaded {len(documents)} {file_extension} files")
                        all_documents.extend(documents)

                except Exception as e:
                    APP_LOG.error(f"Error loading {file_extension} files: {str(e)}")
                    continue

            if not all_documents:
                APP_LOG.warning("No documents were loaded")
                return []

            split_documents = self.text_splitter.split_documents(all_documents)
            APP_LOG.info(f"Split into {len(split_documents)} chunks")

            return split_documents

        except Exception as e:
            APP_LOG.error(f"Error in load_documents: {str(e)}")
            raise

    def get_collection_info(self, collection_name: str) -> dict:
        """
        Get the collection information for a given collection name.

        Args:
            collection_name (str): The name of the collection to get information for.

        Returns:
            dict: A dictionary containing the collection information. The dictionary
            contains the following keys:

            - `status` (str): The status of the collection. Can be "active", "not_found",
                or "error".
            - `name` (str): The name of the collection.
            - `metadata` (dict): The metadata associated with the collection.
            - `chunk_count` (int): The number of chunks in the collection.
            - `persist_directory` (str): The directory where the collection is stored.

            on error, returns a dictionary with the following keys:

            - `status` (str): The status of the collection. Can be "error".
            - `name` (str): The name of the collection.
            - `error` (str): The error message.
        """

        try:
            if collection_name not in self.vector_stores:
                return {
                    "status": "not_found",
                    "name": collection_name,
                    "error": "Collection not found",
                }

            collection: Collection = self.chroma_client.get_collection(collection_name)

            if not collection:
                return {
                    "status": "not_found",
                    "name": collection_name,
                    "error": "Collection not found",
                }

            return {
                "status": "active",
                "name": collection_name,
                "metadata": collection.metadata,
                "chunk_count": collection.count(),
                "persist_directory": self.db_dir,
            }
        except Exception as e:
            APP_LOG.error(f"Error getting collection info: {str(e)}")
            return {"status": "error", "name": collection_name, "error": str(e)}

    def query(self, collection_name: str, user_query: str) -> Tuple[str, str]:
        """
        Query the collection with a given user query, and return the response.

        The query result is based on the similarity search result of the given user query
        in the collection. If the collection is not found, it will try to use the default collection.

        Args:
            collection_name (str): The name of the collection to query.
            user_query (str): The user query to search in the collection.

        Returns:
            Tuple[str, str]: A tuple containing the response content and a status message.
        """
        try:
            if collection_name not in self.vector_stores:
                APP_LOG.warning(
                    f"Collection {collection_name} not found, try to use default collection"
                )
                collection_name = "default"

            if collection_name == "default" and "default" not in self.vector_stores:
                raise Exception(
                    "the collection not found and the `default` collection not exist, please create collection first"
                )

            vector_store = self.vector_stores[collection_name]
            relevant_docs = vector_store.similarity_search(user_query, k=3)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])

            system_prompt = (
                "Please answer the question primarily based on the provided context,"
                "but you may supplement with your knowledge when appropriate. "
                "Always prioritize context information when there are conflicts. "
                "Also, make sure the answer is in language that the user uses."
                f"\n\n{context}"
            )

            response = self.client.chat.completions.create(
                model="anthropic/claude-3-sonnet",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.7,
            )
            return (response.choices[0].message.content, "Get response successfully")
        except Exception as e:
            APP_LOG.error(f"Error in query: {str(e)}")
            return (("", {str(e)}),)

    def update_collection(
        self,
        collection_name: str,
        collection_metadata: dict = None,
        documents_dir: str = os.path.join("upload", "default"),
    ) -> Tuple[str, str]:
        """
        Update the vector store of a specific collection by rebuilding it.

        Args:
            collection_name (str): The name of the collection to update.
            collection_metadata (dict, optional): Metadata for the collection.
                Defaults to None, in which case existing metadata is used.
            documents_dir (str, optional): The directory containing documents to
                load. Defaults to "upload/default".

        Returns:
            Tuple[str, str]: A tuple containing a boolean indicating success or
            failure, and a message detailing the result of the operation.
        """

        try:
            if collection_name not in self.vector_stores:
                return f"Error: Collection `{collection_name}` not found"

            metadata = (
                self.get_collection_metadata(collection_name)
                if collection_metadata is None
                else collection_metadata
            )

            self.delete_collection(collection_name)

            documents = self.load_documents(documents_dir)
            self.vector_stores[collection_name] = Chroma.from_documents(
                client=self.chroma_client,
                documents=documents,
                embedding=self.embeddings,
                collection_name=collection_name,
                collection_metadata=metadata,
            )

            return (True, f"Collection `{collection_name}` completely rebuilt")

        except Exception as e:
            return (False, f"Error updating vector store: {str(e)}")

    def modify_collection(
        self, collection_name: str, new_name: str, new_metadata: dict
    ) -> Tuple[str, str]:
        """
        Modify the name and metadata of an existing collection.

        This function updates the name and metadata of a specified collection in both
        the in-memory vector stores and the database. If the collection is not found
        in either the in-memory store or the database, an error message is returned.

        Args:
            collection_name (str): The current name of the collection to modify.
            new_name (str): The new name for the collection.
            new_metadata (dict): The new metadata to associate with the collection.

        Returns:
            str: A message indicating the result of the modification, or an error message
            if the collection was not found.
        """

        if collection_name not in self.vector_stores:
            return (False, f"Collection `{collection_name}` not found in memory")

        collection: Collection = self.chroma_client.get_collection(collection_name)

        if not collection:
            return (False, f"Collection `{collection_name}` not found in database")

        collection.modify(new_name, new_metadata)
        del self.vector_stores[collection_name]

        self.vector_stores[new_name] = Chroma(
            client=self.chroma_client,
            collection_name=new_name,
        )

        return (True, f"Collection `{collection_name}` modified to `{new_name}`")

    def get_collections(self) -> List[str]:
        """Get a list of all available(initialized) collection names

        Returns:
            List[str]: A list of collection names
        """
        return list(self.vector_stores.keys())

    def get_collection_metadata(self, collection_name: str) -> dict:
        """Get the metadata of a specific collection

        Args:
            collection_name (str): The name of the collection to get metadata for

        Returns:
            dict: The metadata of the collection as a dictionary

        Raises:
            ValueError: If the collection is not found
        """
        collection: Collection = self.chroma_client.get_collection(collection_name)

        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found")

        return collection.metadata

    def delete_collection(self, collection_name: str) -> Tuple[bool, str]:
        """Delete a specific collection

        Args:
            collection_name (str): The name of the collection to delete

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the collection was deleted successfully, and a status message
        """

        if collection_name in self.vector_stores:
            try:
                self.chroma_client.delete_collection(collection_name)
                del self.vector_stores[collection_name]
            except Exception as e:
                return (False, f"Error deleting collection: {str(e)}")

        return (True, f"Collection `{collection_name}` has been forgotten")
