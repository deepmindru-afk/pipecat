#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""HeyGen API.

API to communicate with HeyGen Streaming API.
"""

from typing import Any, Dict, List, Optional, Union

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field


# ----------------------------
# Pydantic Models for WhatsApp
# ----------------------------
class WhatsAppSession(BaseModel):
    sdp: str
    sdp_type: str


class WhatsAppError(BaseModel):
    code: int
    message: str
    href: str
    error_data: Dict[str, Any]


class WhatsAppConnectCall(BaseModel):
    id: str
    from_: str = Field(..., alias="from")
    to: str
    event: str  # "connect"
    timestamp: str
    direction: Optional[str]
    session: WhatsAppSession


class WhatsAppTerminateCall(BaseModel):
    id: str
    from_: str = Field(..., alias="from")
    to: str
    event: str  # "terminate"
    timestamp: str
    direction: Optional[str]
    biz_opaque_callback_data: Optional[str] = None
    status: Optional[str] = None  # "FAILED" or "COMPLETED"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[int] = None


class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WhatsAppConnectCallValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: List[WhatsAppContact]
    calls: List[WhatsAppConnectCall]


class WhatsAppTerminateCallValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    calls: List[WhatsAppTerminateCall]
    errors: Optional[List[WhatsAppError]] = None


class WhatsAppChange(BaseModel):
    value: Union[WhatsAppConnectCallValue, WhatsAppTerminateCallValue]
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookRequest(BaseModel):
    object: str
    entry: List[WhatsAppEntry]


class WhatsAppApi:
    BASE_URL = f"https://graph.facebook.com/v23.0/"

    def __init__(
        self, whatsapp_token: str, phone_number_id: str, session: aiohttp.ClientSession
    ) -> None:
        self.phone_number_id = phone_number_id
        self.session = session
        self.whatsapp_url = f"{self.BASE_URL}{phone_number_id}/calls"
        self.whatsapp_token = whatsapp_token

    async def answer_call_to_whatsapp(self, call_id: str, action: str, sdp: str, from_: str):
        logger.debug(f"Answering call {call_id} to WhatsApp, action:{action}")
        async with self.session.post(
            self.whatsapp_url,
            headers={
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": from_,
                "action": action,
                "call_id": call_id,
                "session": {"sdp": sdp, "sdp_type": "answer"},
            },
        ) as response:
            return await response.json()
