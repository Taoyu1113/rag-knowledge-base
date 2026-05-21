import dashscope
from dashscope import TextEmbedding


dashscope.api_key = "sk-f06b8ed05f264e6c83aa0df48d1bbb30"


def get_embedding(text: str):
    resp = TextEmbedding.call(
        model="text-embedding-v1",
        input=text
    )

    return resp["output"]["embeddings"][0]["embedding"]