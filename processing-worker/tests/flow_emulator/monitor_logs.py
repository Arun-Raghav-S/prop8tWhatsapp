#!/usr/bin/env python3
"""
Real-time log monitor for WhatsApp Agent testing
Watches extracted_payloads.log and highlights important events
"""

import time
import os
import sys
from datetime import datetime

class LogMonitor:
    def __init__(self, log_file_path: str = "../../logs/extracted_payloads.log"):
        self.log_file_path = log_file_path
        self.last_position = 0
        
        # Color codes for terminal output
        self.colors = {
            'green': '\033[92m',
            'yellow': '\033[93m', 
            'red': '\033[91m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }
    
    def colorize(self, text: str, color: str) -> str:
        """Add color to text for terminal output"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def parse_log_line(self, line: str) -> tuple:
        """Parse log line and determine its importance and color"""
        line = line.strip()
        
        if not line:
            return None, None
            
        # Message received events
        if "MESSAGE_RECEIVED" in line:
            return "cyan", f"📥 {line}"
        
        # User messages  
        elif "USER_MESSAGE" in line:
            return "green", f"💬 {line}"
        
        # Button clicks
        elif "BUTTON_CLICK" in line:
            return "purple", f"🔘 {line}"
        
        # Property events
        elif "PROPERTY" in line and ("FOUND" in line or "SEARCH" in line):
            return "blue", f"🏠 {line}"
        
        # Know More events
        elif "KNOW_MORE" in line:
            return "yellow", f"ℹ️  {line}"
        
        # Schedule Visit events  
        elif "SCHEDULE_VISIT" in line:
            return "yellow", f"📅 {line}"
        
        # Carousel events
        elif "CAROUSEL" in line:
            return "blue", f"🎠 {line}"
        
        # Response sent events
        elif "RESPONSE_SENT" in line:
            return "green", f"📤 {line}"
        
        # Error events
        elif "ERROR" in line or "❌" in line:
            return "red", f"❌ {line}"
        
        # Agent processing
        elif "AGENT" in line or "🧠" in line:
            return "purple", f"🧠 {line}"
        
        # API calls
        elif "HTTP Request" in line:
            return "cyan", f"🌐 {line}"
        
        # Success indicators
        elif "✅" in line:
            return "green", f"✅ {line}"
        
        # Warnings
        elif "⚠️" in line or "WARNING" in line:
            return "yellow", f"⚠️  {line}"
        
        # Default - show as white
        else:
            return "white", f"   {line}"
    
    def get_file_size(self) -> int:
        """Get current file size"""
        try:
            return os.path.getsize(self.log_file_path)
        except FileNotFoundError:
            return 0
    
    def monitor(self):
        """Start monitoring the log file"""
        print(self.colorize("🔍 WhatsApp Agent Log Monitor", "bold"))
        print(self.colorize("=" * 50, "white"))
        print(f"📂 Watching: {self.log_file_path}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(self.colorize("=" * 50, "white"))
        print(self.colorize("💡 Run your tests in another terminal to see live updates!", "yellow"))
        print(self.colorize("Press Ctrl+C to stop monitoring\n", "white"))
        
        # Get initial file size
        if os.path.exists(self.log_file_path):
            self.last_position = self.get_file_size()
            print(self.colorize(f"📏 Current log size: {self.last_position} bytes", "cyan"))
        else:
            print(self.colorize(f"⚠️  Log file doesn't exist yet: {self.log_file_path}", "yellow"))
            print(self.colorize("It will be created when the first message is processed.", "white"))
        
        print()
        
        try:
            while True:
                self.check_for_updates()
                time.sleep(0.5)  # Check every 500ms
        except KeyboardInterrupt:
            print(self.colorize("\n🛑 Monitoring stopped by user", "yellow"))
        except Exception as e:
            print(self.colorize(f"\n❌ Error monitoring logs: {e}", "red"))
    
    def check_for_updates(self):
        """Check for new log entries"""
        if not os.path.exists(self.log_file_path):
            return
        
        current_size = self.get_file_size()
        
        if current_size > self.last_position:
            # File has grown, read new content
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
            
            # Process new lines
            for line in new_lines:
                color, formatted_line = self.parse_log_line(line)
                if formatted_line:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"{self.colorize(timestamp, 'white')} {self.colorize(formatted_line, color)}")
            
            self.last_position = current_size
        elif current_size < self.last_position:
            # File was truncated/recreated
            print(self.colorize("🔄 Log file was reset, starting fresh monitoring", "yellow"))
            self.last_position = 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor WhatsApp Agent logs in real-time')
    parser.add_argument('--log-file', 
                       default='../../logs/extracted_payloads.log',
                       help='Path to the log file to monitor')
    
    args = parser.parse_args()
    
    monitor = LogMonitor(args.log_file)
    monitor.monitor()

if __name__ == "__main__":
    main()
