from fastapi import FastAPI
import asyncio
import json
from .routes import router, controller

# Mock Kafka Consumer class to simulate exactly how real Kafka behaves
class MockKafkaConsumer:
    async def listen_for_crashes(self):
        # In a real environment, this connects to the Kafka 'app.unhealthy' topic.
        print("[Kafka Listener] Connected to broker topic 'app.unhealthy'. Listening for events...")
        while True:
            await asyncio.sleep(45) # Simulate an app crash randomly every 45 seconds
            
            # Simulate receiving an event from the App Health Checker
            fake_kafka_message = {
                "event_type": "app.unhealthy",
                "app_id": "email-classifier",
                "version": "1.0.0",
                "reason": "Failed 3 consecutive /health probes."
            }
            
            print(f"\n🚨 [Kafka Event Received from Health Checker]: App '{fake_kafka_message['app_id']}' is UNHEALTHY!")
            print("🤖 [Auto-Pilot Triggered]: Lifecycle Manager is taking action...")
            
            # Auto-restarting the application without human intervention!
            controller.restart(fake_kafka_message["app_id"], fake_kafka_message["version"])
            print("✅ [Auto-Pilot Finished]: App successfully restarted.\n")


# Setup a lifespan context manager to run the background task
async def start_kafka_listener(app: FastAPI):
    consumer = MockKafkaConsumer()
    # Create the background task
    task = asyncio.create_task(consumer.listen_for_crashes())
    yield
    # Clean up when the server stops
    task.cancel()

app = FastAPI(
    title="AetherAgents Lifecycle Manager",
    description="Controls the start, stop, restart, scale, and rollback states of deployed apps",
    version="1.0.0",
    lifespan=start_kafka_listener
)

# Prefixing the routes with /apps means endpoints will look like /apps/{app_id}/start
app.include_router(router, prefix="/apps", tags=["Lifecycle"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "lifecycle_manager"}
