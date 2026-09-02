# trigger_test.py
import uuid
from app.workers.tasks import execute_full_analysis

# 1. Generate a mock enterprise tracking context
mock_tracking_id = str(uuid.uuid4())

# 2. Provide a path to a real test image file on your machine
# (Make sure to put an actual image at this path before running!)
test_image_path = "/home/alien/Whereabouts/test_sample.jpg"

print(f"🚀 Dispatching test scan task to RabbitMQ...")
print(f"Tracking ID: {mock_tracking_id}")

# .delay() sends the task asynchronously to the Celery queue
result = execute_full_analysis.delay(mock_tracking_id, test_image_path)

print(f"✨ Task successfully enqueued! Task ID: {result.id}")
print("👉 Keep an eye on your Celery worker terminal window to watch it execute.")
