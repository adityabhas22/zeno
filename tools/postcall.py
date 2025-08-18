"""
Post-Call Processing for Zeno

Enhanced call summary and transcript processing with Zeno-specific features.
"""

import os
import json
from datetime import datetime
from typing import Optional

from core.integrations.google.drive import DriveService
from core.integrations.google.gmail import GmailService
from config.settings import get_settings


def handle_call_end(agent_session, participant):
    """
    Handle call end processing with enhanced Zeno features.
    
    Args:
        agent_session: The agent session that ended
        participant: The participant who disconnected
    """
    print(f"Call has ended for participant {participant.identity} - performing Zeno cleanup 🤖")
    
    # Reset assistant state to ensure clean state for next connection
    try:
        if hasattr(agent_session, 'userdata') and agent_session.userdata:
            agent_session.userdata.zeno_active = False
            print("Reset Zeno assistant state for next connection")
    except Exception as e:
        print(f"Error resetting assistant state: {e}")
    
    # Extract conversation transcript
    try:
        # Use the history property instead of chat_ctx
        chat_ctx = agent_session.history
        if chat_ctx and chat_ctx.items:
            print("Extracting call transcript...")
            
            transcript = []
            conversation_text = ""
            
            for item in chat_ctx.items:
                # Only process ChatMessage items (exclude function calls, etc.)
                if hasattr(item, 'role') and hasattr(item, 'text_content'):
                    role = item.role
                    content = item.text_content or ""
                    timestamp = getattr(item, 'created_at', None)
                    
                    transcript.append({
                        "role": role,
                        "content": content,
                        "timestamp": timestamp
                    })
                    
                    # Build conversation text for AI processing
                    speaker = "User" if role == 'user' else "Zeno"
                    conversation_text += f"{speaker}: {content}\n"
            
            # Only process transcript if there were actual messages
            if transcript:
                # Print complete transcript to console
                print("\n" + "="*60)
                print(f"ZENO CALL TRANSCRIPT - Participant: {participant.identity}")
                print("="*60)
                
                for i, msg in enumerate(transcript, 1):
                    role_display = "🎤 USER" if msg['role'] == 'user' else "🤖 ZENO"
                    if msg['timestamp']:
                        timestamp_str = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')
                    else:
                        timestamp_str = "N/A"
                    print(f"\n[{i:2d}] {role_display} ({timestamp_str}):")
                    print(f"     {msg['content']}")
                
                print("\n" + "="*60)
                print(f"Total messages: {len(transcript)}")
                print("="*60 + "\n")
                
                # Save transcript to file
                save_transcript(transcript, participant.identity)
                
                # Generate post-call summary and actions if there's meaningful conversation
                if len(transcript) > 1:  # More than just initial greeting
                    print("Generating post-call summary and actions...")
                    generate_post_call_summary_and_actions(conversation_text, participant.identity)
            else:
                print("No conversation messages to transcript.")
        else:
            print("No chat history available for transcript.")
    except Exception as e:
        print(f"Error extracting transcript: {e}")
        import traceback
        traceback.print_exc()


def generate_post_call_summary_and_actions(conversation_text: str, participant_id: str):
    """Generate AI-powered summary, to-dos, and draft email after the call"""
    try:
        settings = get_settings()
        
        # Check if Google credentials exist before proceeding
        client_secrets_path = settings.credentials_dir / "client_secret.json"
        
        if not client_secrets_path.exists():
            print("⚠️  Google client_secret.json not found. Skipping Google Docs/Gmail integration.")
            print(f"   Expected at: {client_secrets_path}")
            print("   To enable post-call summaries, add your Google OAuth credentials.")
            return
        
        # Initialize services
        drive_service = DriveService()
        gmail_service = GmailService()
        
        # Initialize OpenAI client for AI generation
        import openai as openai_lib
        openai_client = openai_lib.OpenAI()
        
        # Generate summary using OpenAI
        summary_prompt = f"""
        Please analyze this phone conversation with Zeno AI assistant and provide:
        1. A concise summary of what was discussed
        2. Key outcomes or decisions made
        3. Important information exchanged
        4. Any tasks or action items mentioned
        
        Conversation:
        {conversation_text}
        
        Please be concise but capture the essential points.
        """
        
        summary_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        call_summary = summary_response.choices[0].message.content.strip()
        
        # Generate to-do items using OpenAI
        todo_prompt = f"""
        Based on this phone conversation with Zeno AI assistant, extract any action items, tasks, or follow-ups that need to be done.
        Format as a simple bulleted list. If no clear action items exist, respond with "No specific action items identified."
        
        Conversation:
        {conversation_text}
        
        Action items:
        """
        
        todo_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": todo_prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        todo_items = todo_response.choices[0].message.content.strip()
        
        # Create Google Doc with summary and to-dos using the new service
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        doc_result = drive_service.create_call_summary_doc(
            participant_id, date_str, call_summary, conversation_text
        )
        
        print(f"✅ Created Google Doc: {doc_result.get('title')} - {doc_result.get('url')}")
        
        # Get user email from environment
        user_email = os.getenv('ZENO_USER_EMAIL')  # Updated from JARVIS_USER_EMAIL
        
        if user_email:
            # Generate email content
            email_subject = f"Zeno Call Summary - {participant_id} - {datetime.now().strftime('%Y-%m-%d')}"
            email_body = f"""Hi,
            
Here's a summary of your recent call with Zeno:

CALL SUMMARY:
{call_summary}

ACTION ITEMS:
{todo_items}

I've also created a detailed Google Doc with the full transcript and notes:
{doc_result.get('url', 'Document link unavailable')}

Best regards,
Zeno AI Assistant
"""
            
            # Draft the email
            email_result = gmail_service.draft_email(
                to=[user_email], 
                subject=email_subject, 
                body=email_body
            )
            print(f"✅ Drafted email to {user_email}: {email_subject}")
            print(f"   Draft ID: {email_result.get('id')}")
            
        else:
            print("⚠️  ZENO_USER_EMAIL not found in environment variables")
            print("   Set ZENO_USER_EMAIL to enable automatic email summaries")
            
    except Exception as e:
        print(f"❌ Error generating post-call summary and actions: {e}")
        import traceback
        traceback.print_exc()


def save_transcript(transcript, participant_id):
    """Save the conversation transcript to a JSON file."""
    settings = get_settings()
    
    # Create transcripts directory
    transcripts_dir = settings.logs_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    filename = f"transcript_{participant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = transcripts_dir / filename
    
    # Save transcript with metadata
    transcript_data = {
        "participant_id": participant_id,
        "call_date": datetime.now().isoformat(),
        "agent": "Zeno",
        "version": "1.0.0",
        "messages": transcript,
        "summary": {
            "total_messages": len(transcript),
            "duration_estimate": "Unknown",  # Could be calculated from timestamps
            "topics": []  # Could be extracted with AI
        }
    }
    
    with open(filepath, 'w') as f:
        json.dump(transcript_data, f, indent=2)
    
    print(f"📝 Transcript saved to {filepath}")
