from pydantic import BaseModel
from share.types import Optional


class LearnModel(BaseModel):
    collection_name: str
    tag: Optional[str] = ""
    author: Optional[str] = ""
    re: Optional[bool] = False

class ChatModel(BaseModel):
    collection_name: str
    query: str

class ForgetModel(BaseModel):
    collection_name: str