#!/usr/bin/env python3
"""Example client script demonstrating gRPC service usage."""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.client import ResourceServiceClient
from src.generated.resource_service_pb2 import ResourceType
from src.utils.logging import configure_logging, get_logger


async def demonstrate_crud_operations():
    """Demonstrate CRUD operations using the resource service client."""
    logger = get_logger(__name__)
    
    async with ResourceServiceClient("localhost", 50051) as client:
        logger.info("Connected to resource service")
        
        # Create some resources
        logger.info("Creating resources...")
        resources = []
        
        for i in range(3):
            resource = await client.create_resource(
                name=f"example-resource-{i}",
                description=f"Example resource number {i}",
                resource_type=ResourceType.RESOURCE_TYPE_COMPUTE,
                metadata={
                    "environment": "demo",
                    "index": str(i),
                    "created_by": "example_client"
                }
            )
            resources.append(resource)
            logger.info(f"Created resource: {resource.id} ({resource.name})")
        
        # List all resources
        logger.info("Listing all resources...")
        all_resources, next_token, total_count = await client.list_resources()
        logger.info(f"Total resources: {total_count}")
        for resource in all_resources:
            logger.info(f"  - {resource.id}: {resource.name} ({resource.type})")
        
        # Get a specific resource
        if resources:
            first_resource = resources[0]
            logger.info(f"Retrieving resource: {first_resource.id}")
            retrieved = await client.get_resource(first_resource.id)
            logger.info(f"Retrieved: {retrieved.name} (status: {retrieved.status})")
        
        # Update a resource
        if resources:
            resource_to_update = resources[0]
            logger.info(f"Updating resource: {resource_to_update.id}")
            updated = await client.update_resource(
                resource_to_update.id,
                name=f"updated-{resource_to_update.name}",
                description="This resource has been updated!",
                metadata={"updated": "true", "timestamp": "2024-01-01"}
            )
            logger.info(f"Updated resource: {updated.name}")
        
        # Delete resources
        logger.info("Deleting resources...")
        for resource in resources:
            success = await client.delete_resource(resource.id)
            if success:
                logger.info(f"Deleted resource: {resource.id}")
            else:
                logger.error(f"Failed to delete resource: {resource.id}")
        
        logger.info("Demo completed successfully!")


async def demonstrate_streaming():
    """Demonstrate the streaming watch functionality."""
    logger = get_logger(__name__)
    
    async with ResourceServiceClient("localhost", 50051) as client:
        logger.info("Starting resource watch demo...")
        
        # Start watching for changes in a background task
        async def watch_resources():
            logger.info("Starting to watch for resource changes...")
            try:
                async for event in client.watch_resources():
                    logger.info(
                        f"Resource event: {event.type} - "
                        f"{event.resource.name} ({event.resource.id})"
                    )
            except Exception as e:
                logger.error(f"Watch error: {e}")
        
        # Start the watcher
        watch_task = asyncio.create_task(watch_resources())
        
        # Give the watcher a moment to start
        await asyncio.sleep(1)
        
        # Create a few resources to trigger events
        logger.info("Creating resources to trigger watch events...")
        created_ids = []
        
        for i in range(2):
            resource = await client.create_resource(
                name=f"watch-demo-{i}",
                description=f"Resource for watch demo {i}",
                resource_type=ResourceType.RESOURCE_TYPE_STORAGE,
                metadata={"demo": "watch"}
            )
            created_ids.append(resource.id)
            await asyncio.sleep(0.5)  # Small delay to see events
        
        # Update one resource
        if created_ids:
            await client.update_resource(
                created_ids[0],
                name="updated-watch-demo",
                description="Updated for watch demo"
            )
        
        # Delete resources
        for resource_id in created_ids:
            await client.delete_resource(resource_id)
            await asyncio.sleep(0.5)
        
        # Stop watching
        await asyncio.sleep(2)  # Let any remaining events process
        watch_task.cancel()
        
        try:
            await watch_task
        except asyncio.CancelledError:
            logger.info("Watch task cancelled")
        
        logger.info("Streaming demo completed!")


async def main():
    """Main function to run the client examples."""
    configure_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting gRPC client examples...")
    
    try:
        # Run CRUD operations demo
        logger.info("=== CRUD Operations Demo ===")
        await demonstrate_crud_operations()
        
        # Small break between demos
        await asyncio.sleep(2)
        
        # Run streaming demo
        logger.info("=== Streaming Watch Demo ===")
        await demonstrate_streaming()
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    logger.info("All demos completed successfully!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)