"""Chat history service for maintaining conversation context."""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

from core.config import settings


class ChatHistory:
    """Manages chat history for maintaining conversation context."""
    
    def __init__(self):
        self.history_dir = Path("./chat_history")
        self.history_dir.mkdir(exist_ok=True)
        self.chat_histories: Dict[str, List[Dict[str, Any]]] = {}  # {session_id: [{"question": str, "answer": str, "timestamp": datetime}]}
        self.history_limit = 10  # Keep last 10 Q&A pairs
        self.history_duration_hours = 24  # Keep history for 24 hours
        print(f"🔧 ChatHistory initialized. History directory: {self.history_dir}")
    
    def add_conversation(self, session_id: str, question: str, answer: str) -> None:
        """Add a question-answer pair to the chat history."""
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = []
        
        # Add new conversation
        conversation = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.now()
        }
        
        self.chat_histories[session_id].append(conversation)
        
        # Keep only the last N conversations
        if len(self.chat_histories[session_id]) > self.history_limit:
            self.chat_histories[session_id] = self.chat_histories[session_id][-self.history_limit:]
        
        # Save to file
        self._save_history_to_file(session_id)
        print(f"🔧 Added conversation to history for session: {session_id}")
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        self._load_history_from_file(session_id)
        
        if session_id not in self.chat_histories:
            return []
        
        # Filter out expired conversations
        now = datetime.now()
        valid_conversations = []
        
        for conv in self.chat_histories[session_id]:
            if now - conv["timestamp"] < timedelta(hours=self.history_duration_hours):
                valid_conversations.append(conv)
        
        # Update the history with only valid conversations
        self.chat_histories[session_id] = valid_conversations
        
        return self.chat_histories[session_id]
    
    def get_recent_context(self, session_id: str, max_conversations: int = 3) -> str:
        """Get recent conversation context as a formatted string."""
        history = self.get_chat_history(session_id)
        
        if not history:
            return ""
        
        # Get the most recent conversations
        recent_conversations = history[-max_conversations:]
        
        context_parts = []
        for i, conv in enumerate(recent_conversations, 1):
            context_parts.append(f"Previous Q{i}: {conv['question']}")
            context_parts.append(f"Previous A{i}: {conv['answer'][:200]}{'...' if len(conv['answer']) > 200 else ''}")
        
        return "\n".join(context_parts)
    
    def clear_session_history(self, session_id: str) -> None:
        """Clear chat history for a specific session."""
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]
        
        # Delete history file
        history_file = self.history_dir / f"{session_id}_history.json"
        if history_file.exists():
            history_file.unlink()
        
        print(f"🔧 Cleared chat history for session: {session_id}")
    
    def cleanup_expired_history(self) -> None:
        """Remove expired chat history entries."""
        now = datetime.now()
        
        for session_id, conversations in list(self.chat_histories.items()):
            valid_conversations = []
            for conv in conversations:
                if now - conv["timestamp"] < timedelta(hours=self.history_duration_hours):
                    valid_conversations.append(conv)
            
            if valid_conversations:
                self.chat_histories[session_id] = valid_conversations
            else:
                del self.chat_histories[session_id]
                # Delete empty history file
                history_file = self.history_dir / f"{session_id}_history.json"
                if history_file.exists():
                    history_file.unlink()
        
        print(f"🔧 Cleaned up expired chat history entries.")
    
    def _save_history_to_file(self, session_id: str) -> None:
        """Save chat history to a JSON file."""
        history_file = self.history_dir / f"{session_id}_history.json"
        
        try:
            # Convert datetime objects to strings for JSON serialization
            history_data = []
            for conv in self.chat_histories[session_id]:
                conv_copy = conv.copy()
                conv_copy["timestamp"] = conv["timestamp"].isoformat()
                history_data.append(conv_copy)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ Failed to save chat history for session {session_id}: {e}")
    
    def _load_history_from_file(self, session_id: str) -> None:
        """Load chat history from a JSON file."""
        history_file = self.history_dir / f"{session_id}_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # Convert timestamp strings back to datetime objects
                conversations = []
                for conv in history_data:
                    conv_copy = conv.copy()
                    conv_copy["timestamp"] = datetime.fromisoformat(conv["timestamp"])
                    conversations.append(conv_copy)
                
                self.chat_histories[session_id] = conversations
                print(f"🔧 Loaded chat history for session {session_id} from file.")
                
            except Exception as e:
                print(f"⚠️ Failed to load chat history for session {session_id}: {e}")
                # Delete corrupted file
                history_file.unlink(missing_ok=True)
