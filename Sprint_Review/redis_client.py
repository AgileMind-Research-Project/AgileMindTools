"""
Redis client for Sprint Review Lambda function.
Connects to cloud Redis to find project channels and post messages.
"""

import redis
import json
import uuid
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class RedisClient:
    """Redis client for channel messaging, matching the backend key patterns."""

    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'redis-12930.crce182.ap-south-1-1.ec2.cloud.redislabs.com')
        self.port = int(os.getenv('REDIS_PORT', 12930))
        self.password = os.getenv('REDIS_PASSWORD', '')
        self.username = os.getenv('REDIS_USERNAME', 'default')
        self._client = None

    def _get_client(self):
        """Get or create Redis connection."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                username=self.username,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
        return self._client

    def get_project_channel(self, tenant_name, project_id):
        """
        Find the channel associated with a project by scanning tenant channels.

        Args:
            tenant_name: Tenant name (e.g., 'sliit')
            project_id: Project ID to find channel for

        Returns:
            Channel ID string if found, None otherwise
        """
        try:
            client = self._get_client()
            channels_key = f"tenant:{tenant_name}:channels"

            # Get all channel IDs for the tenant
            channel_ids = client.smembers(channels_key)

            if not channel_ids:
                logger.info(f"No channels found for tenant {tenant_name}")
                return None

            # Check each channel for matching project_id
            for channel_id in channel_ids:
                channel_key = f"channel:{channel_id}"
                channel_data = client.hgetall(channel_key)

                if channel_data and str(channel_data.get('project_id', '')) == str(project_id):
                    logger.info(f"Found channel {channel_id} for project {project_id}")
                    return channel_id

            logger.info(f"No channel found for project {project_id} in tenant {tenant_name}")
            return None

        except Exception as e:
            logger.error(f"Error finding project channel: {str(e)}")
            return None

    def send_message(self, channel_id, content, username="Sprint Review Bot", user_id="system"):
        """
        Send a message to a channel (push to list + publish to pubsub).

        Args:
            channel_id: Channel ID to send message to
            content: Message content string
            username: Display name for the sender
            user_id: User ID for the sender

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            client = self._get_client()

            message_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            message_data = {
                "id": message_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "username": username,
                "content": content,
                "type": "text",
                "created_at": now,
                "updated_at": now,
                "edited": False,
                "deleted": False
            }

            message_json = json.dumps(message_data)
            messages_key = f"messages:{channel_id}"

            # Push to messages list
            client.rpush(messages_key, message_json)

            # Publish to channel for real-time subscribers
            client.publish(f"channel:{channel_id}", message_json)

            logger.info(f"Successfully sent message to channel {channel_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending message to channel {channel_id}: {str(e)}")
            return False

    def close(self):
        """Close the Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
