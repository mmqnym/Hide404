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
        """載入並分割文件"""
        all_documents = []

        try:
            # 遍歷所有支援的文件類型

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

            # 統一使用 RecursiveCharacterTextSplitter 進行分割
            split_documents = self.text_splitter.split_documents(all_documents)
            APP_LOG.info(f"Split into {len(split_documents)} chunks")

            return split_documents

        except Exception as e:
            APP_LOG.error(f"Error in load_documents: {str(e)}")
            raise

    def get_collection_info(self, collection_name: str) -> dict:
        """獲取集合的詳細信息"""
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
                "document_count": collection.count(),
                "persist_directory": self.db_dir,
            }
        except Exception as e:
            APP_LOG.error(f"Error getting collection info: {str(e)}")
            return {"status": "error", "name": collection_name, "error": str(e)}

    def query(self, collection_name: str, user_query: str) -> Tuple[str, str]:
        """處理用戶查詢"""
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
    ) -> str:
        """
        更新指定集合的向量資料庫
        Args:
            collection_name (str): 要更新的集合名稱
            rebuild (bool): 是否強制重新載入所有文檔
        Returns:
            str: 更新狀態訊息
        """
        try:
            if collection_name not in self.vector_stores:
                return f"Error: Collection '{collection_name}' not found"

            # 重建集合
            metadata = (
                self.get_collection_metadata(collection_name)
                if collection_metadata is None
                else collection_metadata
            )
            # 刪除現有集合
            self.delete_collection(collection_name)
            # 重新創建集合
            documents = self.load_documents(documents_dir)
            self.vector_stores[collection_name] = Chroma.from_documents(
                client=self.chroma_client,
                documents=documents,
                embedding=self.embeddings,
                collection_name=collection_name,
                collection_metadata=metadata,
            )

            return f"Collection '{collection_name}' completely rebuilt"

        except Exception as e:
            return f"Error updating vector store: {str(e)}"

    def modify_collection(
        self, collection_name: str, new_name: str, new_metadata: dict
    ) -> str:
        """更新指定集合的元數據"""
        if collection_name not in self.vector_stores:
            return f"Error: Collection '{collection_name}' not found in memory"

        collection: Collection = self.chroma_client.get_collection(collection_name)

        if not collection:
            return f"Error: Collection '{collection_name}' not found in database"

        collection.modify(new_name, new_metadata)
        del self.vector_stores[collection_name]

        self.vector_stores[new_name] = Chroma(
            client=self.chroma_client,
            collection_name=new_name,
        )

        return f"Collection '{collection_name}' modified to '{new_name}'"

    def get_collections(self) -> List[str]:
        """獲取所有可用的集合名稱"""
        # 只返回已載入到記憶體的集合
        return list(self.vector_stores.keys())

    def get_collection_metadata(self, collection_name: str) -> dict:
        """獲取指定集合的元資料"""
        collection: Collection = self.chroma_client.get_collection(collection_name)

        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found")

        return collection.metadata

    def delete_collection(self, collection_name: str) -> Tuple[bool, str]:
        """刪除指定集合"""
        if collection_name in self.vector_stores:
            try:
                self.chroma_client.delete_collection(collection_name)
                del self.vector_stores[collection_name]
            except Exception as e:
                return False, f"Error deleting collection: {str(e)}"

        return True, f"Collection `{collection_name}` has been forgotten"
