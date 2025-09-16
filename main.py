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
    if 'streaming_summaries' not in st.session_state:
        st.session_state.streaming_summaries = []
    if 'current_chapter' not in st.session_state:
        st.session_state.current_chapter = 0

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
        add_chat_message("system", f"🔧 Initializing crawler with headless browser...")
        
        # Debug mode handling
        debug_mode = st.session_state.get('debug_mode', False)
        if debug_mode:
            add_chat_message("system", f"🐛 Debug mode enabled - using visible browser")
        
        # Create crawler instance with debug settings
        crawler = bns_crawler(
            url, 
            temp_dir, 
            headless=not debug_mode,  # Use visible browser in debug mode
            wait_s=20 if debug_mode else 15  # Longer waits in debug mode
        )
        
        add_chat_message("system", f"🌐 Logging in and extracting chapter list...")
        
        # Extract story content (this is a blocking operation)
        # Run in executor to avoid blocking the async event loop
        import asyncio
        loop = asyncio.get_event_loop()
        
        def run_extraction():
            try:
                add_chat_message("system", "🔐 Attempting to login to website...")
                actual_story_name = crawler.extract_content(username, password)
                add_chat_message("system", f"📝 Successfully extracted story: {actual_story_name}")
                return actual_story_name
            except Exception as e:
                error_msg = f"Error in extraction: {str(e)}"
                print(error_msg)
                add_chat_message("error", f"❌ Crawler error: {error_msg}")
                raise e
            finally:
                # Always close the driver
                try:
                    crawler.driver.quit()
                    add_chat_message("system", "🔒 Browser driver closed")
                except Exception as cleanup_error:
                    print(f"Error closing driver: {cleanup_error}")
                    add_chat_message("system", f"⚠️ Warning: Issue closing browser: {cleanup_error}")
        
        # Run the extraction in a thread to avoid blocking with timeout
        try:
            actual_story_name = await asyncio.wait_for(
                loop.run_in_executor(None, run_extraction),
                timeout=300  # 5 minutes timeout
            )
        except asyncio.TimeoutError:
            add_chat_message("error", "❌ Crawling operation timed out after 5 minutes")
            try:
                crawler.driver.quit()
            except:
                pass
            raise Exception("Crawling timed out after 5 minutes")
        
        if not actual_story_name:
            raise Exception("Failed to extract story name")
        
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
        # Make sure to close the driver if it exists
        try:
            if 'crawler' in locals() and hasattr(crawler, 'driver'):
                crawler.driver.quit()
        except:
            pass
        return None, None

async def generate_summary(safe_folder_name, temp_dir, start_chapter, max_chapters, gather_chapters, 
                         big_summary_interval, quota_per_minute, summary_time_per_chapter,
                         short_summaries=None, long_summaries=None, characters="", streaming_placeholder=None):
    """Generate story summary with streaming updates"""
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
        from agent.workflow import ProgressSummaryEvent
        
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
        
        # Clear previous streaming data
        st.session_state.streaming_summaries = []
        st.session_state.current_chapter = 0
        
        handler = w.run(
            timeout=max_chapters//gather_chapters*summary_time_per_chapter,
        )

        # Stream events and update UI in real-time
        async for ev in handler.stream_events():
            if isinstance(ev, ProgressSummaryEvent):
                st.session_state.current_chapter += 1
                chapter_summary = {
                    "chapter": st.session_state.current_chapter,
                    "summary": ev.msg,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.streaming_summaries.append(chapter_summary)
                
                # Add to chat log immediately
                add_chat_message("system", f"📖 Chapter {st.session_state.current_chapter}: {ev.msg[:100]}...")
                
                # Update the streaming placeholder if provided
                if streaming_placeholder:
                    with streaming_placeholder.container():
                        st.success(f"✅ Processed Chapter {st.session_state.current_chapter}")
                        st.text_area(
                            f"Chapter {st.session_state.current_chapter} Summary:", 
                            ev.msg, 
                            height=120, 
                            key=f"stream_chapter_{st.session_state.current_chapter}"
                        )
                        
                        # Show all processed chapters
                        if len(st.session_state.streaming_summaries) > 1:
                            with st.expander(f"📚 All {len(st.session_state.streaming_summaries)} Processed Chapters"):
                                for i, chap in enumerate(st.session_state.streaming_summaries, 1):
                                    st.text_area(
                                        f"Chapter {chap['chapter']} ({chap['timestamp']}):", 
                                        chap['summary'], 
                                        height=80,
                                        key=f"all_chapters_{i}"
                                    )

        result = await handler
        
        add_chat_message("system", f"✅ Summary generation completed!")
        add_chat_message("system", f"📝 Generated summary length: {len(str(result))} characters")
        
        return str(result).strip()
        
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
            
            # Add debug mode option
            debug_mode = st.checkbox("🐛 Debug Mode", help="Enable detailed logging for troubleshooting")
        
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
    
    # Main content area - Single column layout
    col_main = st.columns([1])[0]
    
    with col_main:
        # New Story Section
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
            
            # Add test button for debugging
            col_test, col_empty = st.columns([1, 2])
            with col_test:
                test_crawler = st.form_submit_button("🧪 Test Crawler", help="Test crawler initialization without full crawl")
        
        st.divider()
        
        # Continue Summary Section
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
        
        st.divider()
        
        # Streaming Output Section
        st.header("📝 Real-time Chapter Summaries")
        
        # Create placeholder for streaming updates
        streaming_placeholder = st.empty()
        
        # Show current streaming status
        if st.session_state.operation_status == "running":
            with streaming_placeholder.container():
                st.info("🔄 Processing chapters... Summaries will appear here in real-time.")
                
                # Display any existing streaming summaries
                if st.session_state.streaming_summaries:
                    latest_summary = st.session_state.streaming_summaries[-1]
                    st.success(f"✅ Latest: Chapter {latest_summary['chapter']} processed at {latest_summary['timestamp']}")
                    st.text_area(
                        f"Chapter {latest_summary['chapter']} Summary:", 
                        latest_summary['summary'], 
                        height=120
                    )
                    
                    if len(st.session_state.streaming_summaries) > 1:
                        with st.expander(f"📚 View All {len(st.session_state.streaming_summaries)} Processed Chapters"):
                            for chap in st.session_state.streaming_summaries:
                                st.text_area(
                                    f"Chapter {chap['chapter']} ({chap['timestamp']}):", 
                                    chap['summary'], 
                                    height=80,
                                    key=f"display_chap_{chap['chapter']}"
                                )
        elif st.session_state.streaming_summaries:
            # Show completed summaries
            with streaming_placeholder.container():
                st.success(f"✅ Completed! Processed {len(st.session_state.streaming_summaries)} chapters")
                
                # Show latest summary
                latest_summary = st.session_state.streaming_summaries[-1]
                st.text_area(
                    f"Final Chapter {latest_summary['chapter']} Summary:", 
                    latest_summary['summary'], 
                    height=120
                )
                
                # Show all summaries in expander
                with st.expander(f"📚 View All {len(st.session_state.streaming_summaries)} Chapters"):
                    for chap in st.session_state.streaming_summaries:
                        st.text_area(
                            f"Chapter {chap['chapter']} ({chap['timestamp']}):", 
                            chap['summary'], 
                            height=80,
                            key=f"final_chap_{chap['chapter']}"
                        )
                        
                # Clear summaries button
                if st.button("🗑️ Clear Chapter Summaries"):
                    st.session_state.streaming_summaries = []
                    st.session_state.current_chapter = 0
                    st.rerun()
        else:
            with streaming_placeholder.container():
                st.info("👆 Start a crawl or continue a summary above to see real-time chapter summaries here!")
        
        # Process form submissions
        if crawl_and_summarize:
            if not all([story_url, username, password, google_api_key]):
                add_chat_message("error", "❌ Please fill in all required fields (URL, credentials, API key)")
            else:
                # Store debug mode in session state
                st.session_state.debug_mode = debug_mode
                
                add_chat_message("user", f"Starting new crawl and summary for: {story_url}")
                add_chat_message("system", f"🔧 Preparing to crawl with settings: Max chapters: {max_chapters}, Gather: {gather_chapters}")
                if debug_mode:
                    add_chat_message("system", f"🐛 Debug mode is ON - browser will be visible and use longer timeouts")
                st.session_state.operation_status = "running"
                st.rerun()  # Trigger immediate UI update
                
                # Run crawl and summary in sequence with streaming
                async def run_crawl_and_summary():
                    try:
                        add_chat_message("system", "🚀 Starting crawling process...")
                        safe_folder_name, actual_name = await crawl_story(story_url, username, password, st.session_state.temp_dir)
                        
                        if safe_folder_name and actual_name:
                            add_chat_message("system", f"✅ Crawling completed for: {actual_name}")
                            add_chat_message("system", "🤖 Starting AI summarization...")
                            
                            summary = await generate_summary(
                                safe_folder_name, st.session_state.temp_dir, 0, max_chapters, gather_chapters,
                                big_summary_interval, quota_per_minute, summary_time_per_chapter,
                                streaming_placeholder=streaming_placeholder
                            )
                            if summary:
                                add_chat_message("system", f"📄 Final Summary:\n\n{summary[:500]}...")
                        else:
                            add_chat_message("error", "❌ Crawling failed - cannot proceed with summarization")
                    except Exception as e:
                        add_chat_message("error", f"❌ Error in crawl and summary process: {str(e)}")
                        import traceback
                        add_chat_message("error", f"🔍 Traceback: {traceback.format_exc()}")
                
                # Execute async function with better error handling
                try:
                    asyncio.run(run_crawl_and_summary())
                except Exception as e:
                    add_chat_message("error", f"❌ Operation failed: {str(e)}")
                    import traceback
                    add_chat_message("error", f"🔍 Full traceback: {traceback.format_exc()}")
                finally:
                    st.session_state.operation_status = "ready"
                    st.rerun()
        
        # Handle test crawler button
        if test_crawler:
            if not story_url:
                add_chat_message("error", "❌ Please provide a story URL for testing")
            else:
                add_chat_message("user", f"🧪 Testing crawler initialization for: {story_url}")
                st.session_state.operation_status = "running"
                st.rerun()
                
                async def test_crawler_func():
                    try:
                        add_chat_message("system", "🧪 Starting crawler test...")
                        
                        # Store debug mode
                        st.session_state.debug_mode = debug_mode
                        
                        # Test crawler initialization
                        test_crawler = bns_crawler(
                            story_url, 
                            st.session_state.temp_dir,
                            headless=not debug_mode,
                            wait_s=20 if debug_mode else 15
                        )
                        add_chat_message("system", "✅ Crawler initialized successfully")
                        
                        # Test navigation
                        add_chat_message("system", "🌐 Testing navigation to story page...")
                        test_crawler.driver.get(story_url)
                        test_crawler._ready()
                        
                        page_title = test_crawler.driver.title
                        add_chat_message("system", f"📄 Page loaded: {page_title}")
                        
                        # Test login elements
                        add_chat_message("system", "🔍 Looking for login elements...")
                        try:
                            login_btn = test_crawler.driver.find_element(By.CSS_SELECTOR, "a.bg-blue-600")
                            add_chat_message("system", "✅ Login button found")
                        except Exception as e:
                            add_chat_message("error", f"❌ Login button not found: {e}")
                        
                        # Close driver
                        test_crawler.driver.quit()
                        add_chat_message("system", "✅ Test completed successfully!")
                        
                    except Exception as e:
                        add_chat_message("error", f"❌ Test failed: {str(e)}")
                        import traceback
                        add_chat_message("error", f"🔍 Traceback: {traceback.format_exc()}")
                        try:
                            if 'test_crawler' in locals():
                                test_crawler.driver.quit()
                        except:
                            pass
                
                try:
                    # Import here to avoid issues
                    from selenium.webdriver.common.by import By
                    asyncio.run(test_crawler_func())
                except Exception as e:
                    add_chat_message("error", f"❌ Test execution failed: {str(e)}")
                finally:
                    st.session_state.operation_status = "ready"
                    st.rerun()
        
        if continue_summary:
            if not all([safe_folder_name_continue, google_api_key]):
                add_chat_message("error", "❌ Please provide safe folder name and API key")
            else:
                add_chat_message("user", f"Continuing summary for: {safe_folder_name_continue} from chapter {start_chapter}")
                st.session_state.operation_status = "running"
                st.rerun()  # Trigger immediate UI update
                
                # Prepare previous data
                short_list = [s.strip() for s in previous_short.split('\n') if s.strip()] if previous_short else []
                long_list = [s.strip() for s in previous_long.split('\n') if s.strip()] if previous_long else []
                
                async def run_continue_summary():
                    summary = await generate_summary(
                        safe_folder_name_continue, st.session_state.temp_dir, start_chapter, max_chapters_continue, 
                        gather_chapters_continue, 50, 15, summary_time_continue,
                        short_list, long_list, previous_characters, streaming_placeholder=streaming_placeholder
                    )
                    if summary:
                        add_chat_message("system", f"📄 Continued Summary:\n\n{summary[:500]}...")
                
                try:
                    asyncio.run(run_continue_summary())
                except Exception as e:
                    add_chat_message("error", f"❌ Continue operation failed: {str(e)}")
                finally:
                    st.session_state.operation_status = "ready"
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

