import streamlit as st
import asyncio
import os
import sys
import json
import tempfile
import re
import shutil
import atexit
from datetime import datetime
from pathlib import Path
import time

# Add src directory to path
sys.path.append("src")
sys.path.append("src/agent")
sys.path.append("src/crawl")

# Initialize temp directory and register cleanup
@atexit.register
def cleanup_temp_dir():
    """Clean up temporary directory on exit"""
    if hasattr(st.session_state, 'temp_dir') and os.path.exists(st.session_state.temp_dir):
        try:
            shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
        except:
            pass  # Ignore cleanup errors

from agent.workflow import Summary
from crawl.crawling import bns_crawler

# Page config
st.set_page_config(
    page_title="Story Summary AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat-like UI
st.markdown("""
<style>
    .stApp > header {
        background-color: transparent;
    }
    
    .main-content {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .chat-message {
        padding: 15px;
        margin: 10px 0;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-message {
        border-left-color: #ff7f0e;
        background-color: #fff3e0;
    }
    
    .system-message {
        border-left-color: #2ca02c;
        background-color: #f3fff3;
    }
    
    .error-message {
        border-left-color: #d62728;
        background-color: #fff3f3;
    }
    
    .sidebar-section {
        background-color: white;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'crawl_history' not in st.session_state:
        st.session_state.crawl_history = load_crawl_history()
    if 'current_operation' not in st.session_state:
        st.session_state.current_operation = None
    if 'operation_status' not in st.session_state:
        st.session_state.operation_status = "ready"
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp(prefix="story_crawler_")

def load_crawl_history():
    """Load crawl history from JSON file"""
    history_file = "crawl_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading history: {e}")
            return []
    return []

def save_crawl_history(history):
    """Save crawl history to JSON file"""
    try:
        with open("crawl_history.json", 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving history: {e}")

def add_chat_message(message_type, content, timestamp=None):
    """Add message to chat history"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S")
    
    st.session_state.chat_history.append({
        "type": message_type,
        "content": content,
        "timestamp": timestamp
    })

def display_chat_history():
    """Display chat messages"""
    for msg in st.session_state.chat_history:
        css_class = "chat-message"
        if msg["type"] == "user":
            css_class += " user-message"
        elif msg["type"] == "system":
            css_class += " system-message"
        elif msg["type"] == "error":
            css_class += " error-message"
        
        st.markdown(f"""
        <div class="{css_class}">
            <small>{msg["timestamp"]} - {msg["type"].title()}</small><br>
            {msg["content"]}
        </div>
        """, unsafe_allow_html=True)

def create_safe_folder_name(story_name):
    """Create a safe folder name from story name by removing/replacing special characters"""
    # Remove Vietnamese diacritics and special characters
    safe_name = re.sub(r'[^\w\s-]', '', story_name)  # Remove special chars except word chars, spaces, hyphens
    safe_name = re.sub(r'[-\s]+', '_', safe_name)     # Replace spaces and hyphens with underscores
    safe_name = safe_name.strip('_')                   # Remove leading/trailing underscores
    
    # Limit length to avoid filesystem issues
    if len(safe_name) > 50:
        safe_name = safe_name[:50].rstrip('_')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return safe_name

async def crawl_story(url, username, password, temp_dir):
    """Crawl story from website"""
    try:
        add_chat_message("system", f"🕷️ Starting to crawl story from: {url}")
        
        crawler = bns_crawler(url, temp_dir, headless=True, wait_s=12)
        
        # Extract story content
        crawler.extract_content(username, password)
        
        # Get the actual story name from the website
        from selenium.webdriver.common.by import By
        crawler.driver.get(url)
        crawler._ready()
        actual_story_name = crawler.driver.find_element(By.ID, "truyen-title").text
        crawler.driver.quit()  # Close the driver
        
        # Create safe folder name
        safe_folder_name = create_safe_folder_name(actual_story_name)
        
        add_chat_message("system", f"✅ Successfully crawled story: {actual_story_name}")
        add_chat_message("system", f"📁 Stored in safe folder name: {safe_folder_name}")
        
        # Add to history
        history_entry = {
            "name": actual_story_name,
            "safe_folder_name": safe_folder_name,
            "url": url,
            "crawl_date": datetime.now().isoformat(),
            "temp_path": os.path.join(temp_dir, actual_story_name),
            "summary_data": {
                "short_summaries": [],
                "long_summaries": [],
                "characters": "",
                "last_chapter": 0
            }
        }
        
        st.session_state.crawl_history.append(history_entry)
        save_crawl_history(st.session_state.crawl_history)
        
        return safe_folder_name, actual_story_name
        
    except Exception as e:
        add_chat_message("error", f"❌ Error crawling story: {str(e)}")
        return None, None

async def generate_summary(safe_folder_name, temp_dir, start_chapter, max_chapters, gather_chapters, 
                         big_summary_interval, quota_per_minute, summary_time_per_chapter,
                         short_summaries=None, long_summaries=None, characters=""):
    """Generate story summary"""
    try:
        add_chat_message("system", f"🤖 Starting summary generation for: {safe_folder_name}")
        add_chat_message("system", f"📊 Parameters: Chapters {start_chapter}-{start_chapter + max_chapters}, Gather: {gather_chapters}")
        
        # Set environment variable for API key
        if 'google_api_key' in st.session_state:
            os.environ['GOOGLE_API_KEY'] = st.session_state.google_api_key
        
        # Find the story files in temp directory
        story_files = []
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                # Look for .txt files in this directory
                txt_files = [f for f in os.listdir(item_path) if f.endswith('.txt')]
                if txt_files:
                    story_files = [os.path.join(item_path, f) for f in sorted(txt_files)]
                    break
        
        if not story_files:
            raise Exception("No story files found in temporary directory")
        
        # Use the custom Summary function that works with file paths
        from agent.workflow import BookSummary
        
        w = BookSummary(
            story_files[start_chapter:], 
            big_summary_interval=big_summary_interval, 
            max_chapters=max_chapters, 
            gather_chapters=gather_chapters,
            quota_per_minute=quota_per_minute,
            initial_short_summaries=short_summaries or [],
            initial_long_summaries=long_summaries or [],
            initial_characters=characters,
        )
        
        result = await w.run(
            timeout=max_chapters//gather_chapters*summary_time_per_chapter,
        )
        
        add_chat_message("system", f"✅ Summary generation completed!")
        add_chat_message("system", f"📝 Generated summary length: {len(str(result))} characters")
        
        # Save the result
        summary_dir = "summary"
        os.makedirs(summary_dir, exist_ok=True)
        with open(os.path.join(summary_dir, f"{safe_folder_name}_summary.txt"), "w", encoding="utf-8") as f:
            f.write(str(result).strip())
        
        return str(result)
        
    except Exception as e:
        add_chat_message("error", f"❌ Error generating summary: {str(e)}")
        return None

def main():
    init_session_state()
    
    st.title("📚 Story Summary AI")
    st.markdown("*Automated story crawling and AI-powered summarization*")
    
    # Sidebar for settings and history
    with st.sidebar:
        st.header("🔧 Settings")
        
        # API Configuration
        with st.expander("🔑 API Configuration", expanded=True):
            google_api_key = st.text_input("Google Gemini API Key", type="password", 
                                         help="Enter your Google Gemini API key")
            if google_api_key:
                st.session_state.google_api_key = google_api_key
                os.environ['GOOGLE_API_KEY'] = google_api_key
        
        # Website Credentials
        with st.expander("🌐 Website Credentials", expanded=True):
            username = st.text_input("Username", help="Website login username")
            password = st.text_input("Password", type="password", help="Website login password")
        
        st.divider()
        
        # Story History
        st.header("📖 Story History")
        
        if st.session_state.crawl_history:
            for i, story in enumerate(st.session_state.crawl_history):
                with st.expander(f"📚 {story['name']}", expanded=False):
                    st.write(f"**URL:** {story['url']}")
                    st.write(f"**Crawled:** {story['crawl_date'][:10]}")
                    st.write(f"**Safe Folder Name:** {story.get('safe_folder_name', 'N/A')}")
                    st.write(f"**Last Chapter:** {story['summary_data']['last_chapter']}")
                    
                    if st.button(f"Continue Summary", key=f"continue_{i}"):
                        st.session_state.selected_story = story
                        st.rerun()
                    
                    if st.button(f"Delete", key=f"delete_{i}"):
                        st.session_state.crawl_history.pop(i)
                        save_crawl_history(st.session_state.crawl_history)
                        st.rerun()
        else:
            st.info("No stories found. Start by crawling a new story!")
        
        # Clear chat history
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Temporary Directory Info
        st.divider()
        st.header("📁 Temporary Storage")
        st.info(f"**Temp Dir:** {st.session_state.temp_dir}")
        
        if st.button("🧹 Clear Temp Directory", help="Remove all temporary files"):
            try:
                import shutil
                shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
                st.session_state.temp_dir = tempfile.mkdtemp(prefix="story_crawler_")
                add_chat_message("system", "🧹 Temporary directory cleared and recreated")
                st.rerun()
            except Exception as e:
                add_chat_message("error", f"❌ Error clearing temp directory: {e}")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    # Left column - New Crawl
    with col1:
        st.header("🆕 New Story")
        
        with st.form("crawl_form"):
            story_url = st.text_input("Story URL", 
                                    placeholder="https://example.com/story-url",
                                    help="URL of the story to crawl")
            
            st.subheader("📋 Crawl Settings")
            col_a, col_b = st.columns(2)
            with col_a:
                max_chapters = st.number_input("Max Chapters", min_value=1, value=100)
                gather_chapters = st.number_input("Gather Chapters", min_value=1, value=10)
            with col_b:
                big_summary_interval = st.number_input("Big Summary Interval", min_value=1, value=50)
                quota_per_minute = st.number_input("Quota Per Minute", min_value=1, value=15)
            
            summary_time_per_chapter = st.number_input("Summary Time Per Chapter (seconds)", 
                                                     min_value=1, value=20)
            
            crawl_and_summarize = st.form_submit_button("🚀 Crawl & Summarize", type="primary")
        
        if crawl_and_summarize:
            if not all([story_url, username, password, google_api_key]):
                add_chat_message("error", "❌ Please fill in all required fields (URL, credentials, API key)")
            else:
                add_chat_message("user", f"Starting new crawl and summary for: {story_url}")
                st.session_state.operation_status = "running"
                
                # Run crawl and summary in sequence
                async def run_crawl_and_summary():
                    safe_folder_name, actual_name = await crawl_story(story_url, username, password, st.session_state.temp_dir)
                    if safe_folder_name:
                        summary = await generate_summary(
                            safe_folder_name, st.session_state.temp_dir, 0, max_chapters, gather_chapters,
                            big_summary_interval, quota_per_minute, summary_time_per_chapter
                        )
                        if summary:
                            add_chat_message("system", f"📄 Final Summary:\n\n{summary[:500]}...")
                
                # Execute async function
                try:
                    asyncio.run(run_crawl_and_summary())
                except Exception as e:
                    add_chat_message("error", f"❌ Operation failed: {str(e)}")
                finally:
                    st.session_state.operation_status = "ready"
                    st.rerun()
    
    # Right column - Continue Summary
    with col2:
        st.header("▶️ Continue Summary")
        
        # Check if a story is selected from history
        selected_story = st.session_state.get('selected_story', None)
        
        with st.form("continue_form"):
            if selected_story:
                st.info(f"Selected story: **{selected_story['name']}**")
                safe_folder_name_continue = selected_story.get('safe_folder_name', selected_story['name'])
            else:
                available_stories = [story.get('safe_folder_name', story['name']) for story in st.session_state.crawl_history]
                if available_stories:
                    safe_folder_name_continue = st.selectbox("Select Story", options=available_stories, help="Choose from previously crawled stories")
                else:
                    safe_folder_name_continue = st.text_input("Safe Folder Name", 
                                                            placeholder="Enter safe folder name from history",
                                                            help="This should be the safe folder name shown in story history")
            
            st.subheader("📋 Continue Settings")
            col_c, col_d = st.columns(2)
            with col_c:
                start_chapter = st.number_input("Start Chapter", min_value=0, value=0)
                max_chapters_continue = st.number_input("Max Chapters to Process", min_value=1, value=50)
            with col_d:
                gather_chapters_continue = st.number_input("Gather Chapters", min_value=1, value=10, key="gather_continue")
                summary_time_continue = st.number_input("Summary Time Per Chapter", min_value=1, value=20, key="time_continue")
            
            # Previous summary data
            st.subheader("📚 Previous Summary Data (Optional)")
            previous_short = st.text_area("Previous Short Summaries (one per line)", height=100)
            previous_long = st.text_area("Previous Long Summaries (one per line)", height=100)
            previous_characters = st.text_area("Previous Characters", height=60)
            
            continue_summary = st.form_submit_button("🔄 Continue Summary", type="primary")
        
        if continue_summary:
            if not all([safe_folder_name_continue, google_api_key]):
                add_chat_message("error", "❌ Please provide safe folder name and API key")
            else:
                add_chat_message("user", f"Continuing summary for: {safe_folder_name_continue} from chapter {start_chapter}")
                
                # Prepare previous data
                short_list = [s.strip() for s in previous_short.split('\n') if s.strip()] if previous_short else []
                long_list = [s.strip() for s in previous_long.split('\n') if s.strip()] if previous_long else []
                
                async def run_continue_summary():
                    summary = await generate_summary(
                        safe_folder_name_continue, st.session_state.temp_dir, start_chapter, max_chapters_continue, 
                        gather_chapters_continue, 50, 15, summary_time_continue,
                        short_list, long_list, previous_characters
                    )
                    if summary:
                        add_chat_message("system", f"📄 Continued Summary:\n\n{summary[:500]}...")
                
                try:
                    asyncio.run(run_continue_summary())
                except Exception as e:
                    add_chat_message("error", f"❌ Continue operation failed: {str(e)}")
                finally:
                    st.rerun()
    
    # Chat area
    st.divider()
    st.header("💬 Activity Log")
    
    # Operation status indicator
    if st.session_state.operation_status == "running":
        st.info("🔄 Operation in progress... Please wait.")
    else:
        st.success("✅ Ready for new operations")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        display_chat_history()
    
    # Auto-refresh during operations
    if st.session_state.operation_status == "running":
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()

