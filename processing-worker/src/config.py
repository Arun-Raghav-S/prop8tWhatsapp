import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Centralized configuration management"""
    
    # Server Configuration
    PORT = int(os.getenv("PORT", 8080))
    HOST = "0.0.0.0"
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # AiSensy Configuration
    AISENSY_BASE_URL = "https://backend.aisensy.com"
    AISENSY_ACCESS_TOKEN = os.getenv("AISENSY_ACCESS_TOKEN")
    
    # WhatsApp Configuration
    WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "your_verify_token")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    # Google Cloud Configuration
    GCP_PROJECT = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    PUBSUB_SUBSCRIPTION = os.getenv("PUBSUB_SUBSCRIPTION", "prop8t-message-processing-sub")
    
    # Memory Management
    MAX_AGENTS_PER_USER = 1
    CLEANUP_INTERVAL_MINUTES = 30
    AGENT_TIMEOUT_MINUTES = 60
    MAX_TOTAL_AGENTS = 100
    MEMORY_CLEANUP_THRESHOLD_MB = 512
    
    # Chat History
    MAX_CHAT_HISTORY_LENGTH = 50

    # Name Collection
    NAME_COLLECTION_QUESTION_THRESHOLD = 2  # Ask for name after this many questions
    
    # Rate Limiting
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1
    
    # Debugging
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Global config instance
config = Config()