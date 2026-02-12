"""Handler for function call events"""

import json
from typing import Dict, Any
from .base_handler import BaseEventHandler


class FunctionEventHandler(BaseEventHandler):
    """Handles function/tool call events"""
    
    def can_handle(self, event_type: str) -> bool:
        """Handle function call events"""
        return "function_call" in event_type.lower()
    
    async def handle(self, event: Dict[str, Any]):
        """Process function call events"""
        event_type = event.get("type")
        
        # Debug: Log all function call related events
        print(f"🔧 [DEBUG] Function/Tool event: {event_type}")
        print(f"🔧 [DEBUG] Event data: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        if event_type == "response.function_call_arguments.done":
            await self._handle_function_call_arguments_done(event)
        elif event_type == "response.function_call.done":
            await self._handle_function_call_done(event)
    
    async def _handle_function_call_arguments_done(self, event: Dict[str, Any]):
        """Handle function call with complete arguments"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        websocket = self.get_from_context("websocket")
        
        # Extract function call info
        function_call = event.get("function_call", {})
        if not function_call:
            function_call = event.get("function_call_arguments", {})
        if not function_call:
            function_call = event
        
        function_name = function_call.get("name", "")
        print(f"🔧 [DEBUG] Function name extracted: '{function_name}'")
        
        call_id = (
            function_call.get("call_id")
            or function_call.get("id")
            or event.get("call_id")
            or event.get("id")
        )
        
        # Track function call for tracing
        session.track_function_call(
            function_name=function_name,
            event_type=event.get("type"),
            arguments=function_call.get("arguments", {})
        )
        
        # Handle specific function calls
        if function_name == "trigger_assessment":
            await self._handle_trigger_assessment(event, call_id, websocket, assessment_state)
        else:
            print(f"🔧 [DEBUG] Function '{function_name}' called (not handled)")
    
    async def _handle_trigger_assessment(self, event: Dict[str, Any], call_id: str, 
                                        websocket, assessment_state):
        """Handle trigger_assessment function call"""
        function_call = event.get("function_call", {})
        if not function_call:
            function_call = event
        
        # Extract reason from arguments
        arguments = function_call.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (json.JSONDecodeError, ValueError):
                arguments = {}
        reason = arguments.get("reason", "Linguistic ceiling reached") if isinstance(arguments, dict) else "Linguistic ceiling reached"
        
        # Trigger assessment state machine
        if assessment_state.trigger_assessment(reason):
            # Clear any buffered user audio to prevent interference
            print("🔇 Clearing user audio buffer to prevent interference...")
            await websocket.send(json.dumps({"type": "input_audio_buffer.clear"}))
            
            # Send tool output with instruction for AI to immediately acknowledge
            print("\n💬 Sending tool output with acknowledgment instruction...")
            await self._send_tool_output(
                websocket, 
                call_id, 
                "Assessment triggered successfully. Please IMMEDIATELY tell the user in Korean: '평가를 준비하고 있습니다. 잠시만 기다려 주세요.' (Your assessment is being prepared. Please wait a moment.)"
            )
            
            print("💡 Assessment will generate AFTER acknowledgment audio completes.")
        else:
            print("⚠️ Assessment already triggered, ignoring duplicate call")
    
    async def _handle_function_call_done(self, event: Dict[str, Any]):
        """Handle function call completion (backup check)"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        
        print(f"🔧 [DEBUG] Function call done event received")
        print(f"🔧 [DEBUG] Full event: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        function_call = event.get("function_call", {})
        if not function_call:
            function_call = event.get("function_call_result", {})
        if not function_call:
            function_call = event
        
        function_name = function_call.get("name", "")
        print(f"🔧 [DEBUG] Function name extracted: '{function_name}'")
        
        # Track function call completion for tracing
        if function_name:
            session.track_function_call(
                function_name=function_name,
                event_type=event.get("type"),
                status="completed"
            )
        
        # Note: trigger_assessment is fully handled in response.function_call_arguments.done
        # This is just a backup check in case that event was missed
        if function_name == "trigger_assessment" and assessment_state.current_state.name == "INACTIVE":
            print("\n⚠️ Backup: trigger_assessment detected in function_call.done event")
    
    async def _send_tool_output(self, websocket, call_id: str, output_text: str):
        """Send tool output back to the Realtime API."""
        if not call_id:
            print("⚠️ Missing call_id for tool output")
            return
        
        tool_output_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output_text
            }
        }
        await websocket.send(json.dumps(tool_output_event))
        
        # Request a follow-up response after tool output
        await websocket.send(json.dumps({
            "type": "response.create",
            "response": {"modalities": ["text", "audio"]}
        }))
