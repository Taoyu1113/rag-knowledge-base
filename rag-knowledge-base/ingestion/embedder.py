import dashscope
from dashscope import TextEmbedding


dashscope.api_key = "你的API_KEY"


def get_embedding(text: str):
    resp = TextEmbedding.call(
        model="text-embedding-v1",
        input=text
    )

    return resp["output"]["embeddings"][0]["embedding"]