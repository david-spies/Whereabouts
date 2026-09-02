# seed_vector.py
import os
import torch
import torchvision.transforms as T
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "urban_global_geoms"
VECTOR_DIMENSION = 1024


def seed_qdrant_with_real_images():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Re-create collection
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        client.delete_collection(collection_name=COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE)
    )

    print("Loading DINOv2 model for reference vector generation...")
    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14')
    model.eval()

    transform = T.Compose([
        T.Resize(224, interpolation=T.InterpolationMode.BICUBIC),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Reference image path (Point this to your target image or visual reference dataset)
    image_path = "/home/alien/Videos/DSC04375.JPG"

    if os.path.exists(image_path):
        img = Image.open(image_path).convert('RGB')
        tensor = transform(img).unsqueeze(0)
        
        with torch.no_grad():
            vec = model(tensor).squeeze().tolist()

        point = PointStruct(
            id=1,
            vector=vec,
            payload={
                "lat": 47.436018,
                "lon": -121.77858,
                "region_string": "Snoqualmie / North Bend Region",
                "style_tags": ["Subalpine Evergreen Meadows", "Pacific Northwest Timber Frame"]
            }
        )

        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        print(f"Successfully seeded visual vector for '{image_path}' into Qdrant.")
    else:
        print(f"Reference image not found at {image_path}. Please update path.")


if __name__ == "__main__":
    seed_qdrant_with_real_images()
