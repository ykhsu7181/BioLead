"""Conversation API routes."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends

from scholarlead_agent.agent.conversation import (
    ConversationMessage,
    conversation_message_to_dict,
    utc_now_iso,
)
from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.conversation import (
    AddConversationMessageRequest,
    CreateConversationRequest,
)
from scholarlead_agent.database import (
    fetch_conversation_messages,
    fetch_one,
    insert_conversation,
    insert_conversation_message,
)


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("")
def create_conversation(
    request: CreateConversationRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    conversation_id = request.conversation_id or f"conversation-{uuid4()}"
    insert_conversation(
        connection,
        conversation_id=conversation_id,
        title=request.title,
    )
    return api_success({"conversation_id": conversation_id, "status": "active"})


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(
        connection,
        "SELECT * FROM conversations WHERE conversation_id = ?",
        (conversation_id,),
    )
    if row is None:
        raise ApiError("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    return api_success(dict(row))


@router.post("/{conversation_id}/messages")
def add_message(
    conversation_id: str,
    request: AddConversationMessageRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    if (
        fetch_one(
            connection,
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
        is None
    ):
        raise ApiError("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    message = ConversationMessage(
        message_id=f"message-{uuid4()}",
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        created_at=utc_now_iso(),
        metadata=dict(request.metadata),
    )
    insert_conversation_message(connection, message)
    return api_success(conversation_message_to_dict(message))


@router.get("/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    limit: int = 20,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    messages = fetch_conversation_messages(connection, conversation_id, limit=limit)
    return api_success(
        {
            "items": [conversation_message_to_dict(message) for message in messages],
            "page": 1,
            "page_size": limit,
            "total": len(messages),
        }
    )
