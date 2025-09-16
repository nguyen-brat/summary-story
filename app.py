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
from multiprocessing import Process, Queue as mpQueue
from queue import Queue as tQueue
import threading
from selenium.webdriver.common.by import By
import html

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
    .summary-box {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
        background-color: #ffffff;
        height: auto;
        overflow-y: hidden;
        word-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)

def display_summary_box(text):
    """Displays text in a custom box that expands to fit content."""
    escaped_text = html.escape(text).replace('\n', '<br>')
    st.markdown(f'<div class="summary-box">{escaped_text}</div>', unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'crawl_history' not in st.session_state:
        st.session_state.crawl_history = load_crawl_history()
    if 'operation_status' not in st.session_state:
        st.session_state.operation_status = "ready"
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp(prefix="story_crawler_")
    if 'streaming_summaries' not in st.session_state:
        st.session_state.streaming_summaries = []
    if 'story_to_summarize' not in st.session_state:
        st.session_state.story_to_summarize = None
    if 'summary_thread' not in st.session_state:
        st.session_state.summary_thread = None
    if 'summary_queue' not in st.session_state:
        st.session_state.summary_queue = None
    if 'final_summary' not in st.session_state:
        st.session_state.final_summary = None


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
    safe_name = re.sub(r'[^\w\s-]', '', story_name)
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    safe_name = safe_name.strip('_')
    if len(safe_name) > 50:
        safe_name = safe_name[:50].rstrip('_')
    if not safe_name:
        safe_name = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return safe_name

def crawler_process(url, username, password, temp_dir, n_chapters, queue):
    """This function runs in a separate process to avoid blocking the Streamlit UI."""
    from crawl.crawling import bns_crawler
    try:
        crawler = bns_crawler(url, temp_dir, n_chapters=n_chapters, headless=True)
        actual_story_name = crawler.extract_content(username, password)
        if actual_story_name:
            queue.put({"status": "success", "result": actual_story_name})
        else:
            queue.put({"status": "error", "result": "Failed to extract story name."})
    except Exception as e:
        queue.put({"status": "error", "result": str(e)})
    finally:
        try:
            if 'crawler' in locals() and hasattr(crawler, 'driver'):
                crawler.driver.quit()
        except:
            pass

async def generate_summary_async(queue, safe_folder_name, temp_dir, start_chapter, max_chapters, gather_chapters,
                               big_summary_interval, quota_per_minute, summary_time_per_chapter,
                               short_summaries=None, long_summaries=None, characters=""):
    """Asynchronously generates summaries and puts them in a queue."""
    try:
        if 'google_api_key' in st.session_state:
            os.environ['GOOGLE_API_KEY'] = st.session_state.google_api_key
        story_files = []
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                txt_files = [f for f in os.listdir(item_path) if f.endswith('.txt')]
                if txt_files:
                    story_files = [os.path.join(item_path, f) for f in sorted(txt_files)]
                    break
        if not story_files:
            raise Exception("No story files found in temporary directory")
        from agent.workflow import BookSummary, ProgressSummaryEvent
        w = BookSummary(
            story_files[start_chapter:],
            big_summary_interval=big_summary_interval,
            max_chapters=max_chapters,
            gather_chapters=gather_chapters,
            quota_per_minute=quota_per_minute,
            initial_short_summaries=short_summaries or [],
            initial_long_summaries=long_summaries or [],
            initial_characters=characters,
            # api_key=st.session_state.google_api_key if 'google_api_key' in st.session_state else None
        )
        current_chapter = 0
        handler = w.run(timeout=max_chapters // gather_chapters * summary_time_per_chapter)
        async for ev in handler.stream_events():
            if isinstance(ev, ProgressSummaryEvent):
                current_chapter += 1
                chapter_summary = {
                    "chapter": current_chapter,
                    "summary": ev.msg,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                queue.put(chapter_summary)
        result = await handler
        queue.put({"status": "done", "summary": str(result).strip()})
    except Exception as e:
        queue.put({"status": "error", "message": str(e)})

def run_summary_in_thread(queue, *args):
    """Runs the async summary generator in a new event loop in a separate thread."""
    asyncio.run(generate_summary_async(queue, *args))

def main():
    init_session_state()
    st.title("📚 Story Summary AI")
    st.markdown("*Automated story crawling and AI-powered summarization*")
    with st.sidebar:
        if st.button("📝 New Summary Session", use_container_width=True):
            # Clear all session state to start fresh
            for key in list(st.session_state.keys()):
                if key != 'temp_dir': # Keep the temp dir
                    del st.session_state[key]
            st.rerun()
            
        st.header("🔧 Settings")
        with st.expander("🔑 API Configuration", expanded=True):
            google_api_key = st.text_input("Google Gemini API Key", type="password", help="Enter your Google Gemini API key")
            if google_api_key:
                st.session_state.google_api_key = google_api_key
        with st.expander("🌐 Website Credentials", expanded=True):
            username = st.text_input("Username", help="Website login username")
            password = st.text_input("Password", type="password", help="Website login password")
        st.divider()
        st.header("📖 Story History")
        if st.session_state.crawl_history:
            for i, story in enumerate(st.session_state.crawl_history):
                with st.expander(f"📚 {story['name']}", expanded=False):
                    st.write(f"**URL:** {story['url']}")
                    st.write(f"**Crawled:** {story['crawl_date'][:10]}")
                    st.write(f"**Safe Folder Name:** {story.get('safe_folder_name', 'N/A')}")
                    if st.button(f"Delete", key=f"delete_{i}"):
                        st.session_state.crawl_history.pop(i)
                        save_crawl_history(st.session_state.crawl_history)
                        st.rerun()
        else:
            st.info("No stories found. Start by crawling a new story!")
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        st.divider()
        st.header("📁 Temporary Storage")
        st.info(f"**Temp Dir:** {st.session_state.temp_dir}")
        if st.button("🧹 Clear Temp Directory", help="Remove all temporary files"):
            try:
                shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
                st.session_state.temp_dir = tempfile.mkdtemp(prefix="story_crawler_")
                add_chat_message("system", "🧹 Temporary directory cleared and recreated")
                st.rerun()
            except Exception as e:
                add_chat_message("error", f"❌ Error clearing temp directory: {e}")

    col_main = st.columns([1])[0]
    with col_main:
        # Display Final Summary if it exists
        if st.session_state.final_summary:
            st.header("✅ Final Summary")
            display_summary_box(st.session_state.final_summary)
            st.divider()

        st.header("🆕 New Story")
        with st.form("crawl_form"):
            story_url = st.text_input("Story URL", placeholder="https://example.com/story-url")
            st.subheader("📋 Crawl Settings")
            col_a, col_b = st.columns(2)
            with col_a:
                n_chapters = st.number_input("Chapters to Crawl", min_value=1, value=10)
                max_chapters = st.number_input("Max Chapters to Summarize", min_value=1, value=100)
                gather_chapters = st.number_input("Gather Chapters", min_value=1, value=10)
            with col_b:
                big_summary_interval = st.number_input("Big Summary Interval", min_value=1, value=50)
                quota_per_minute = st.number_input("Quota Per Minute", min_value=1, value=15)
            summary_time_per_chapter = st.number_input("Summary Time Per Chapter (s)", min_value=1, value=20)
            crawl_and_summarize = st.form_submit_button("🚀 Crawl & Summarize", type="primary")

        st.divider()
        st.header("📝 Real-time Chapter Summaries")
        streaming_placeholder = st.empty()
        
        # UI rendering logic for summaries
        if st.session_state.streaming_summaries:
            with streaming_placeholder.container():
                if st.session_state.operation_status == "summarizing":
                    st.info("🔄 Processing chapters...")
                else:
                    st.success(f"✅ Completed! Processed {len(st.session_state.streaming_summaries)} chapters")
                
                latest_summary = st.session_state.streaming_summaries[-1]
                st.subheader(f"Chapter {latest_summary['chapter']} Summary:")
                display_summary_box(latest_summary['summary'])
                
                if len(st.session_state.streaming_summaries) > 1:
                    with st.expander(f"📚 View All {len(st.session_state.streaming_summaries)} Processed Chapters"):
                        for chap in reversed(st.session_state.streaming_summaries):
                            st.subheader(f"Chapter {chap['chapter']} ({chap['timestamp']}):")
                            display_summary_box(chap['summary'])
        else:
            with streaming_placeholder.container():
                st.info("👆 Start a crawl to see real-time chapter summaries.")

        if crawl_and_summarize:
            if not all([story_url, username, password, google_api_key]):
                add_chat_message("error", "❌ Please fill in all required fields (URL, credentials, API key)")
            else:
                add_chat_message("user", f"🚀 Starting new crawl and summary for: {story_url}")
                st.session_state.streaming_summaries = []
                st.session_state.final_summary = None
                st.session_state.operation_status = "crawling"
                st.rerun()

        if st.session_state.operation_status == "crawling":
            add_chat_message("system", "🕷️ Crawling in progress...")
            queue = mpQueue()
            p = Process(target=crawler_process, args=(story_url, username, password, st.session_state.temp_dir, n_chapters, queue))
            p.start()
            p.join()
            if not queue.empty():
                result = queue.get()
                if result["status"] == "success":
                    add_chat_message("system", f"✅ Crawling successful: {result['result']}")
                    st.session_state.story_to_summarize = result['result']
                    st.session_state.operation_status = "summarizing"
                else:
                    add_chat_message("error", f"❌ Crawling failed: {result['result']}")
                    st.session_state.operation_status = "ready"
                st.rerun()

        if st.session_state.operation_status == "summarizing":
            if st.session_state.summary_thread is None:
                add_chat_message("system", "🤖 Starting summarization...")
                st.session_state.summary_queue = tQueue()
                safe_folder_name = create_safe_folder_name(st.session_state.story_to_summarize)
                args = (st.session_state.summary_queue, safe_folder_name, st.session_state.temp_dir, 0, max_chapters, gather_chapters,
                        big_summary_interval, quota_per_minute, summary_time_per_chapter)
                st.session_state.summary_thread = threading.Thread(target=run_summary_in_thread, args=args, daemon=True)
                st.session_state.summary_thread.start()

            # Check the queue for updates from the summary thread
            while not st.session_state.summary_queue.empty():
                item = st.session_state.summary_queue.get()
                if isinstance(item, dict) and item.get("status") == "done":
                    st.session_state.final_summary = item['summary']
                    add_chat_message("system", f"📄 Final Summary Generated.")
                    st.session_state.operation_status = "ready"
                    st.session_state.summary_thread = None
                    st.session_state.story_to_summarize = None
                    st.rerun()
                elif isinstance(item, dict) and item.get("status") == "error":
                     add_chat_message("error", f"❌ Summarization failed: {item['message']}")
                     st.session_state.operation_status = "ready"
                     st.session_state.summary_thread = None
                     st.rerun()
                else:
                    st.session_state.streaming_summaries.append(item)
            
            if st.session_state.summary_thread and st.session_state.summary_thread.is_alive():
                time.sleep(2)
                st.rerun()
            else: # Thread might have finished, do one last check and clean up
                st.session_state.operation_status = "ready"
                st.session_state.summary_thread = None
                st.rerun()

    st.divider()
    st.header("💬 Activity Log")
    if st.session_state.operation_status in ["crawling", "summarizing"]:
        st.info("🔄 Operation in progress... Please wait.")
    else:
        st.success("✅ Ready for new operations")
    chat_container = st.container()
    with chat_container:
        display_chat_history()

if __name__ == "__main__":
    main()