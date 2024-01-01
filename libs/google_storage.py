import json
import logging
from logging import Logger
from typing import Optional

from google.cloud import storage
from slack_sdk.errors import SlackClientConfigurationError
from slack_sdk.oauth.installation_store.async_installation_store import AsyncInstallationStore
from slack_sdk.oauth.installation_store.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation

class GCPStorageInstallationStore(InstallationStore, AsyncInstallationStore):
    def __init__(
        self,
        *,
        bucket_name: str,
        client_id: str,
        historical_data_enabled: bool = True,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.bucket_name = bucket_name
        self.historical_data_enabled = historical_data_enabled
        self.client_id = client_id
        self.storage_client = storage.Client()
        self._logger = logger

        @property
        def logger(self) -> Logger:
            if self._logger is None:
                self._logger = logging.getLogger(__name__)
            return self._logger
        

    async def async_save(self, installation: Installation):
        return self.save(installation)

    async def async_save_bot(self, bot: Bot):
        return self.save_bot(bot)

    def save(self, installation: Installation):
        none = "none"
        e_id = installation.enterprise_id or none
        t_id = installation.team_id or none
        workspace_path = f"{self.client_id}/{e_id}-{t_id}"

        self.save_bot(installation.to_bot())

        if self.historical_data_enabled:
            history_version: str = str(installation.installed_at)

            # per workspace
            entity: str = json.dumps(installation.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/installer-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # per workspace per user
            u_id = installation.user_id or none
            entity: str = json.dumps(installation.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/installer-{u_id}-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # ... (similar blocks for other paths)

        else:
            # per workspace
            entity: str = json.dumps(installation.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/installer-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # per workspace per user
            u_id = installation.user_id or none
            entity: str = json.dumps(installation.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/installer-{u_id}-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # ... (similar blocks for other paths)

    def save_bot(self, bot: Bot):
        none = "none"
        e_id = bot.enterprise_id or none
        t_id = bot.team_id or none
        workspace_path = f"{self.client_id}/{e_id}-{t_id}"

        if self.historical_data_enabled:
            history_version: str = str(bot.installed_at)
            entity: str = json.dumps(bot.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/bot-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # ... (similar blocks for other paths)

        else:
            entity: str = json.dumps(bot.__dict__)
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/bot-latest")
            blob.upload_from_string(entity)
            self._logger.debug(f"Google Cloud Storage upload response: {blob}")

            # ... (similar blocks for other paths)

    async def async_find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        return self.find_bot(
            enterprise_id=enterprise_id,
            team_id=team_id,
            is_enterprise_install=is_enterprise_install,
        )

    def find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        none = "none"
        e_id = enterprise_id or none
        t_id = team_id or none
        if is_enterprise_install:
            t_id = none
        workspace_path = f"{self.client_id}/{e_id}-{t_id}"
        try:
            blob = self.storage_client.bucket(self.bucket_name).blob(f"{workspace_path}/bot-latest")
            content = blob.download_as_text()
            data = json.loads(content)
            return Bot(**data)
        except Exception as e:  # skipcq: PYL-W0703
            message = f"Failed to find bot installation data for enterprise: {e_id}, team: {t_id}: {e}"
            self._logger.warning(message)
            return None

    # Implement other methods similarly

# Usage example:
bucket_name = "your-gcs-bucket"
client_id = "your-slack-client-id"
gcp_storage_store = GCPStorageInstallationStore(bucket_name=bucket_name, client_id=client_id)
