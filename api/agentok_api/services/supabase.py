import asyncio
from typing import Dict, List, Literal, Optional
import logging
import os

import requests
from dotenv import load_dotenv
from fastapi import HTTPException, status
from gotrue import User
from supabase import Client, create_client
from termcolor import colored

from ..models import (
    ApiKey,
    ApiKeyCreate,
    Chat,
    ChatCreate,
    LogCreate,
    Log,
    Message,
    MessageCreate,
    Tool,
)

logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env


class SupabaseClient:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.supabase_url = os.environ.get("SUPABASE_URL")
            self.supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
            if not self.supabase_url or not self.supabase_service_key:
                raise Exception("Supabase URL or key not found in environment variables")
            self.supabase: Client = create_client(
                self.supabase_url, self.supabase_service_key
            )
            self.user_id = None
            self._initialized = True

    @classmethod
    def reset(cls):
        """Reset the singleton instance"""
        if cls._instance is not None:
            if hasattr(cls._instance, 'supabase'):
                # Close any active connections if possible
                try:
                    if hasattr(cls._instance.supabase, 'client'):
                        cls._instance.supabase.client.close()
                except:
                    pass
            cls._instance = None
            cls._initialized = False

    def __del__(self):
        """Destructor to ensure resources are cleaned up"""
        try:
            if hasattr(self, 'supabase') and hasattr(self.supabase, 'client'):
                self.supabase.client.close()
        except:
            pass

    def get_user(self) -> User:
        try:
            user = self.supabase.auth.admin.get_user_by_id(self.user_id)
            return {
                "id": user.user.id,
                "email": user.user.email,
                "app_metadata": user.user.app_metadata,
                "user_metadata": user.user.user_metadata,
            }
        except Exception as e:
            print(f"Failed to fetch user info: {e}")
            return None

    # Load the user from the cookie. This is for the situation where the user is already logged in on client side.
    # The request should be called with credentials: 'include'
    def authenticate_with_tokens(self, access_token: str) -> User:
        try:
            if not self.supabase_url or not self.supabase_service_key:
                raise Exception("Supabase URL or key not found in environment variables")

            temp_supabase = create_client(self.supabase_url, self.supabase_service_key)
            
            # Decode and verify the JWT token
            decoded = temp_supabase.auth.get_user(access_token)
            if decoded and decoded.user:
                self.user_id = decoded.user.id
                return decoded.user

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to authenticate"
            )

        except Exception as exc:
            logger.error(f"Authentication error: {exc}")
            raise

    def authenticate_with_apikey(self, apikey: str) -> User:
        try:
            # First, get the user_id from the api_keys table
            api_key_response = (
                self.supabase.table("api_keys")
                .select("user_id")
                .eq("key", apikey)
                .single()
                .execute()
            )

            if not api_key_response.data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to authenticate with apikey",
                )

            self.user_id = api_key_response.data["user_id"]

            user = self.get_user()
            return user

        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="An error occurred during authentication",
            )

    def save_apikey(self, key_to_create: ApiKeyCreate) -> ApiKey:
        try:
            # Create a new instance with the user_id
            key_data = key_to_create.model_dump()
            key_data["user_id"] = self.user_id
            response = self.supabase.table("api_keys").insert(key_data).execute()
            if response.data:
                return ApiKey(**response.data[0])
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create API key",
                )
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create API key",
            )

    def fetch_apikeys(self) -> List[ApiKey]:
        try:
            response = (
                self.supabase.table("api_keys")
                .select("*")
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return [ApiKey(**item) for item in response.data]
            else:
                return []
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve API keys",
            )

    def fetch_apikey(self, apikey_id: str) -> Optional[ApiKey]:
        try:
            response = (
                self.supabase.table("api_keys")
                .select("*")
                .eq("id", apikey_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return ApiKey(**response.data[0])
            else:
                return None
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve API key",
            )

    def delete_apikey(self, apikey_id: str) -> Dict:
        try:
            response = (
                self.supabase.table("api_keys")
                .delete()
                .eq("id", apikey_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return {"message": f"Successfully deleted {apikey_id}"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to delete API key",
                )
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete API key",
            )

    # Fetch the user settings -> general settings
    def fetch_general_settings(self) -> Dict:
        try:
            response = (
                self.supabase.table("user_settings")
                .select("general")
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return response.data[0]
            else:
                return {}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while fetching user settings (general): {exc}",
            )

    # Fetch the user settings -> general settings
    def fetch_tool_settings(self) -> Dict:
        try:
            response = (
                self.supabase.table("user_settings")
                .select("tools")
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return response.data[0]["tools"]
            else:
                return {}
        except Exception as exc:
            print(colored(f"An error occurred: {exc}", "red"))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while fetching user settings (tools): {exc}",
            )

    def fetch_chats(self) -> List[Chat]:
        try:
            response = (
                self.supabase.table("chats")
                .select("*")
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return [Chat(**item) for item in response.data]
            else:
                return []
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get chats for user {self.user_id}: {exc}",
            )

    def fetch_chat(self, chat_id: str) -> Chat:
        try:
            response = (
                self.supabase.table("chats")
                .select("*")
                .eq("id", chat_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return Chat(**response.data[0])
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat not found: {exc}",
            )

    def create_chat(self, chat_to_create: ChatCreate) -> Chat:
        try:
            # Create a new instance with the user_id
            chat_data = chat_to_create.model_dump(exclude={"id"})
            chat_data["user_id"] = self.user_id
            response = self.supabase.table("chats").insert(chat_data).execute()

            if response.data:
                return Chat(**response.data[0])
            else:
                print(colored(f"Insertion failed: {response}", "red"))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create chat",
                )
        except Exception as exc:
            print(colored(f"Failed to create chat: {exc}", "red"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create chat: {exc}",
            )

    def fetch_tools(self, tool_ids: Optional[List[int]] = None) -> List[Tool]:
        try:
            if not self.user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User ID not found",
                )
            if not tool_ids or len(tool_ids) == 0:
                return []

            query = (
                self.supabase.table("tools")
                .select("*")
                .or_(f"user_id.eq.{self.user_id},is_public.eq.true")
            )

            # Add tool_ids filter if provided
            if tool_ids and len(tool_ids) > 0:
                query = query.in_("id", tool_ids)

            response = query.execute()

            if response.data:
                return response.data
            else:
                return []
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed fetching tools: {exc}",
            )

    def create_tool(self, tool_to_create: Tool) -> Tool:
        try:
            tool_data = tool_to_create.model_dump(exclude={"id"})
            tool_data["user_id"] = self.user_id
            response = self.supabase.table("tools").insert(tool_data).execute()
            if response.data:
                return Tool(**response.data[0])
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create tool",
                )
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create tool: {exc}",
            )

    def fetch_tool(self, tool_id: str) -> Tool:
        try:
            response = (
                self.supabase.table("tools")
                .select("*")
                .eq("id", tool_id)
                # .eq("user_id", self.user_id) # This is not so needed as the tool_id is unique and public tools can be fetched
                .execute()
            )
            if response.data:
                return Tool(**response.data[0])
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found"
                )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {exc}",
            )

    def update_tool(self, tool_to_update: Tool) -> Tool:
        tool_data = tool_to_update.model_dump()
        tool_id = tool_data.pop("id")
        if not tool_id:
            raise Exception("Invalid tool_id")
        response = (
            self.supabase.table("tools").update(tool_data).eq("id", tool_id).execute()
        )
        if response.data:
            return response.data[0]
        else:
            raise Exception("Tool not found")

    def delete_tool(self, tool_id: str) -> Dict:
        response = (
            self.supabase.table("tools")
            .delete()
            .eq("id", tool_id)
            .eq("user_id", self.user_id)
            .execute()
        )
        if response.data:
            return {"message": f"Tool {tool_id} deleted successfully"}
        else:
            raise Exception(f"Error deleting tool {tool_id}")

    def fetch_messages(self, chat_id: str) -> List[Message]:
        try:
            response = (
                self.supabase.table("chat_messages")
                .select("*")
                .eq("chat_id", int(chat_id))
                .execute()
            )
            if response.data:
                return [Message(**item) for item in response.data]
            else:
                return []
        except Exception as exc:
            logger.error(f"An error occurred: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed fetching messages: {exc}",
            )

    def add_message(self, message: MessageCreate, chat_id: str) -> Message:
        try:
            # Convert the message to a dictionary while excluding the 'id' field
            message_dict = message.model_dump(exclude={"id"})
            message_dict["user_id"] = self.user_id
            message_dict["chat_id"] = int(chat_id)
            print(colored(f"Adding message: {message_dict}", "green"))
            response = (
                self.supabase.table("chat_messages").insert(message_dict).execute()
            )
            if response.data:
                return Message(**response.data[0])
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Adding message failed without response data",
                )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to add message: {exc}",
            )

    async def add_log(self, log: LogCreate):
        """Add a log entry to the database.
        
        Args:
            log: The log entry to add
            
        Returns:
            dict: The raw response data from the database, or None if the operation failed
        """
        try:
            # Convert to dict and ensure chat_id is an integer
            log_data = {
                "message": log.message,
                "level": log.level,
                "metadata": log.metadata,
                "chat_id": int(log.chat_id) if isinstance(log.chat_id, str) else log.chat_id
            }
            
            # Use asyncio.to_thread since supabase-py doesn't have async support
            response = await asyncio.to_thread(
                lambda: self.supabase.table("chat_logs").insert(log_data).execute()
            )
            
            if response and response.data:
                print(colored(f"Added log for chat {log_data['chat_id']}", "green"))
                return response.data[0]
            
            print(colored(f"No response data from log insertion", "yellow"))
            return None
            
        except Exception as exc:
            logger.error(f"Failed to add log: {exc}")
            logger.error(f"Attempted log data: {log_data}")
            return None

    def fetch_source_metadata(self, chat_id: str) -> Dict:
        try:
            response = (
                self.supabase.table("chats")
                .select("*")
                .eq("id", int(chat_id))
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                chat = response.data[0]

                if chat["from_type"] == "project":
                    response = (
                        self.supabase.table("projects")
                        .select("*")
                        .eq("id", chat["from_project"])
                        .execute()
                    )
                    if response.data:
                        return response.data[0]
                elif chat["from_type"] == "template":
                    response = (
                        self.supabase.table("templates")
                        .select("*")
                        .eq("id", chat["from_template"])
                        .execute()
                    )
                    if response.data:
                        return response.data[0].get("project", {})
            return {}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source metadata not found: {exc}",
            )

    def set_chat_status(
        self,
        chat_id: str,
        chat_status: Literal[
            "ready", "running", "wait_for_human_input", "completed", "aborted", "failed"
        ],
    ):
        try:
            response = (
                self.supabase.table("chats")
                .update({"status": chat_status})
                .eq("id", chat_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if response.data:
                return response.data
            else:
                return None
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to set chat status: {exc}",
            )

    def upload_image(self, iamge_path, image_data):
        try:
            if not iamge_path:
                raise HTTPException(status_code=400, detail="Invalid iamge_path")
            print(colored(f"Uploading document to dataset {iamge_path}", "light_blue"))
            # Read the file content
            file_extension = iamge_path.split(".")[-1]
            # Check if the file already exists
            existing_files = self.supabase.storage.from_("documents").list(
                path=iamge_path
            )
            # TODO: This can be optimized to avoid multiple uploads of the same file
            if any(file["name"] == iamge_path for file in existing_files):
                # Delete the existing file
                print(colored(f"Deleting existing document: {iamge_path}", "yellow"))
                self.supabase.storage.from_("documents").remove([iamge_path])
            res = self.supabase.storage.from_("assets").upload(iamge_path, image_data)
            print(colored(f"Uploaded document: {iamge_path}", "green"))
            return res
        except Exception as e:
            logger.error(f"An error occurred during uploading document: {e}")
            raise

    def search_chunks(self, dataset_id, query_vector, top_k):
        result = self.supabase.rpc(
            "search_chunks_by_dataset",
            {
                "p_dataset_id": dataset_id,
                "p_query_vector": query_vector,
                "p_limit": top_k,
            },
        ).execute()
        print("search_chunks", result)
        return result.data


def create_supabase_client():
    return SupabaseClient()
