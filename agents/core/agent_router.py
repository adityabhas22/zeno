"""
Agent Router - Smart Routing for Zeno Agents

Routes requests to the appropriate agent based on connection type and context:
- MainZenoAgent: For non-telephony interactions (always active)
- PhoneTelephonyAgent: For telephony calls (activation required)
"""

import json
from typing import Optional, Tuple, Any, Dict
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.plugins import noise_cancellation

from agents.core.main_zeno_agent import MainZenoAgent, MainZenoState
from agents.core.phone_telephony_agent import PhoneTelephonyAgent, PhoneTelephonyState


class AgentRouter:
    """
    Smart router that determines which agent to use based on connection context.
    """
    
    def __init__(self):
        self.main_agent = MainZenoAgent()
        self.phone_agent = PhoneTelephonyAgent()
    
    def detect_connection_type(self, ctx: agents.JobContext) -> Tuple[str, Dict[str, Any]]:
        """
        Detect the type of connection and extract metadata.
        
        Returns:
            Tuple of (connection_type, metadata)
            connection_type: "telephony", "web", "api", or "unknown"
        """
        metadata = {}
        connection_type = "unknown"
        
        # Check for telephony indicators
        try:
            if ctx.job.metadata:
                job_metadata = json.loads(ctx.job.metadata)
                
                # Check for phone number (indicates outbound telephony call)
                phone_number = job_metadata.get("phone_number")
                if phone_number:
                    connection_type = "telephony"
                    metadata.update(job_metadata)
                    return connection_type, metadata
                
                # Check for other telephony indicators
                call_purpose = job_metadata.get("purpose")
                if call_purpose in ["briefing", "reminder", "phone_call"]:
                    connection_type = "telephony"
                    metadata.update(job_metadata)
                    return connection_type, metadata
                    
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        
        # Check room name patterns that might indicate telephony
        room_name = ctx.room.name or ""
        if any(pattern in room_name.lower() for pattern in ["call-", "phone-", "sip-", "trunk-"]):
            connection_type = "telephony"
            metadata["room_name"] = room_name
            return connection_type, metadata
        
        # Check for SIP/telephony participants (heuristic)
        for participant in ctx.room.remote_participants.values():
            identity = participant.identity or ""
            if any(pattern in identity.lower() for pattern in ["sip:", "phone:", "trunk:", "+1", "tel:"]):
                connection_type = "telephony"
                metadata["participant_identity"] = identity
                return connection_type, metadata
        
        # Check room metadata for telephony indicators
        try:
            room_metadata = getattr(ctx.room, 'metadata', None)
            if room_metadata:
                room_meta_dict = json.loads(room_metadata)
                if room_meta_dict.get("connection_type") == "telephony":
                    connection_type = "telephony"
                    metadata.update(room_meta_dict)
                    return connection_type, metadata
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Default to web/api connection if no telephony indicators
        # This includes web interfaces, API calls, direct connections, etc.
        connection_type = "web"
        return connection_type, metadata
    
    def get_agent_for_connection(self, connection_type: str, metadata: Dict[str, Any]) -> Tuple[Agent, Any, RoomInputOptions]:
        """
        Get the appropriate agent, state, and room options for the connection type.
        
        Returns:
            Tuple of (agent, userdata_state, room_input_options)
        """
        if connection_type == "telephony":
            # Use phone agent with activation features for telephony
            userdata = PhoneTelephonyState()
            room_options = RoomInputOptions(
                # Enhanced noise cancellation for telephony
                noise_cancellation=noise_cancellation.BVCTelephony(),
            )
            return self.phone_agent, userdata, room_options
        
        else:
            # Use main agent (always active) for non-telephony connections
            userdata = MainZenoState()
            room_options = RoomInputOptions(
                # Standard noise cancellation for web/api - use same as telephony for consistency
                noise_cancellation=noise_cancellation.BVCTelephony(),
            )
            return self.main_agent, userdata, room_options
    
    def get_greeting_for_connection(self, connection_type: str, metadata: Dict[str, Any]) -> str:
        """
        Get appropriate greeting instructions based on connection type and metadata.
        """
        phone_number = metadata.get("phone_number")
        call_purpose = metadata.get("purpose", "general")
        
        if connection_type == "telephony":
            if phone_number is None:
                # Inbound telephony call
                return "Greet the user as Zeno, your daily planning assistant. Let them know you're ready to help and they can say 'Hey Zeno' or 'Come in' to activate you."
            else:
                # Outbound telephony call - purpose-specific greeting
                if call_purpose == "briefing":
                    return "Greet the user warmly and let them know you're calling to provide their daily briefing. Ask if now is a good time."
                elif call_purpose == "reminder":
                    return "Greet the user and mention you're calling with a scheduled reminder or update."
                else:
                    return "Greet the user and let them know you're calling to check in on their day."
        
        else:
            # Non-telephony connection - always active
            return "Greet the user as Zeno, your daily planning assistant, and offer your assistance. You're ready to help immediately."


# Singleton instance for reuse
router = AgentRouter()


def get_agent_router() -> AgentRouter:
    """Get the singleton agent router instance."""
    return router
