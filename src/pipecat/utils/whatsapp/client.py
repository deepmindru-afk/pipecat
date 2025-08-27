#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""WhatsApp API.

API to communicate with WhatsApp Cloud API.
"""

import asyncio
import aiohttp
from loguru import logger
from pipecat.transports.network.webrtc_connection import IceServer, SmallWebRTCConnection
from pipecat.utils.whatsapp.api import (
    WhatsAppApi,
    WhatsAppConnectCall,
    WhatsAppConnectCallValue,
    WhatsAppTerminateCall,
    WhatsAppTerminateCallValue,
    WhatsAppWebhookRequest,
)
from typing import Dict


ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    )
]

class WhatsAppClient:

    def __init__(
        self, whatsapp_token: str, phone_number_id: str, session: aiohttp.ClientSession
    ) -> None:
        self._whatsapp_api = WhatsAppApi(
            whatsapp_token=whatsapp_token, phone_number_id=phone_number_id, session=session
        )
        self._ongoing_calls_map: Dict[str, SmallWebRTCConnection] = {}

    async def terminate_all_calls(self):
        """Terminate all ongoing WhatsApp calls."""
        logger.info("Will terminate all ongoing WhatsApp calls")

        if not self._ongoing_calls_map:
            logger.info("No ongoing calls to terminate")
            return

        logger.info(f"Terminating {len(self._ongoing_calls_map)} ongoing calls")

        # Terminate each call via WhatsApp API
        termination_tasks = []
        for call_id, pipecat_connection in self._ongoing_calls_map.items():
            logger.info(f"Terminating call {call_id}")
            # Call WhatsApp API to terminate the call
            if self._whatsapp_api:
                termination_tasks.append(self._whatsapp_api.terminate_call_to_whatsapp(call_id))
            # Disconnect the pipecat connection
            termination_tasks.append(pipecat_connection.disconnect())

        # Execute all terminations concurrently
        await asyncio.gather(*termination_tasks, return_exceptions=True)

        # Clear the ongoing calls map
        self._ongoing_calls_map.clear()
        logger.info("All calls terminated successfully")

    async def handle_webhook_request(self, request: WhatsAppWebhookRequest):
        """Handle a webhook request from WhatsApp."""
        for entry in request.entry:
            for change in entry.changes:
                # Handle connect events
                if isinstance(change.value, WhatsAppConnectCallValue):
                    for call in change.value.calls:
                        if call.event == "connect":
                            return await self._handle_connect_event(call)

                # Handle terminate events
                elif isinstance(change.value, WhatsAppTerminateCallValue):
                    for call in change.value.calls:
                        if call.event == "terminate":
                            return await self._handle_terminate_event(call)

        raise NotImplementedError("No supported event found")

    def _filter_sdp_for_whatsapp(self, sdp: str) -> str:
        lines = sdp.splitlines()
        filtered = []
        for line in lines:
            if line.startswith("a=fingerprint:") and not line.startswith("a=fingerprint:sha-256"):
                continue  # drop sha-384 / sha-512
            filtered.append(line)
        return "\r\n".join(filtered) + "\r\n"

    async def _handle_connect_event(self, call: WhatsAppConnectCall):
        """Handle a CONNECT event: pre-accept and accept the call."""
        logger.info(f"Incoming call from {call.from_}, call_id: {call.id}")

        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=call.session.sdp, type=call.session.sdp_type)
        sdp_answer = pipecat_connection.get_answer().get("sdp")
        sdp_answer = self._filter_sdp_for_whatsapp(sdp_answer)

        logger.info(f"SDP answer: {sdp_answer}")

        pre_accept_resp = await self._whatsapp_api.answer_call_to_whatsapp(
            call.id, "pre_accept", sdp_answer, call.from_
        )
        if not pre_accept_resp.get("success", False):
            logger.error(f"Failed to pre-accept call: {pre_accept_resp}")
            await pipecat_connection.disconnect()
            raise Exception("Failed to pre-accept call")

        logger.info("Pre-accept response:", pre_accept_resp)

        accept_resp = await self._whatsapp_api.answer_call_to_whatsapp(
            call.id, "accept", sdp_answer, call.from_
        )
        if not accept_resp.get("success", False):
            logger.error(f"Failed to accept call: {accept_resp}")
            await pipecat_connection.disconnect()
            raise Exception("Failed to to accept call")

        logger.info("Accept response:", accept_resp)

        # Storing the connection so we can disconnect later
        self._ongoing_calls_map[call.id] = pipecat_connection

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Peer has disconnected: {webrtc_connection.pc_id}")

        return pipecat_connection

    async def _handle_terminate_event(self, call: WhatsAppTerminateCall):
        """Handle a TERMINATE event: clean up resources and log call completion."""
        logger.info(f"Call terminated from {call.from_}, call_id: {call.id}")
        logger.info(f"Call status: {call.status}")
        if call.duration:
            logger.info(f"Call duration: {call.duration} seconds")

        if call.id in self._ongoing_calls_map:
            pipecat_connection = self._ongoing_calls_map[call.id]
            logger.info(f"Finishing peer connection: {call.id}")
            await pipecat_connection.disconnect()
            self._ongoing_calls_map.pop(call.id, None)

        return {"status": "success", "message": "Call termination handled"}
