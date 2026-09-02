# init_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

client = QdrantClient(host="127.0.0.1", port=6333)
collection_name = "urban_global_geoms"

# Delete the old 384 dimension collection if it exists
if client.collection_exists(collection_name):
    print(f"Dropping mismatched collection: {collection_name}...")
    client.delete_collection(collection_name=collection_name)

print(f"Creating collection with correct layout (dim=1024)...")
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)
print("✅ Qdrant Collection dimension aligned successfully.")
