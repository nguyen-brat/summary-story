from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    Context,
    step,
)
from dotenv import load_dotenv
from llama_index.llms.google_genai import GoogleGenAI
import asyncio
import time
from llama_index.utils.workflow import draw_most_recent_execution
from numpy import block

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, ToolOutput
from typing import Any, List
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.prompts import PromptTemplate

load_dotenv()

FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL = """Mỗi dòng liệt kê một nhân vật gồm tên nhân vật, giới thiệu về nhân vật được cung cấp dưới đây. \
Tóm tắt chương truyện được cung cấp dưới đây. trả lời theo mẫu không trả lời thêm gì khác:

-----

Mẫu:
## Danh sách nhân vật
Tên_nhân_vât_1: giới thiệu về nhân vật 1
Tên_nhân_vât_2: giới thiệu về nhân vật 2

## Tóm tắt chương truyện:
tóm tắt chương truyện
-----

Truyện:

{chapter_text}"""

EXTRACT_CHARACTERSNSUMMARY_PROMPT_TMPL = """cho danh sách các nhân vật đã được đề cập:
{characters}
Tóm tắt của các chương truyện trước:
{previous_summary}
Cập nhập danh sách các nhân vật và thông tin giới thiệu của các nhân vật đó \
nếu có thêm thông tin so với trong giới thiệu nhân vật cũ trong chương truyện được cung cấp dưới đây. \
Nếu không có gì thay đổi giữ nguyên danh sách cũ. Mỗi dòng liệt kê một nhân vật gồm tên nhân vật, giới thiệu về nhân vật. \
Tóm tắt chương truyện được cung cấp dưới đây. trả lời theo mẫu không trả lời thêm gì khác:

-----

Mẫu:
## Danh sách nhân vật
Tên_nhân_vât_1: giới thiệu về nhân vật 1
Tên_nhân_vât_2: giới thiệu về nhân vật 2

## Tóm tắt chương truyện:
tóm tắt chương truyện
-----

Truyện:

{chapter_text}"""

###
LONG_SUMMARY_PROMPT_TMPL = """Dựa vào tóm tắt các chương truyện trước được cung cấp dưới đây \
viết lại thành một tóm tắt những diễn biến chính xoay quanh nhân vật chính (được đề cập nhiều nhất trong truyện). \
Trả lời ngay vào tóm tắt không trả lời thêm gì khác như ví dụ.
Tóm tắt chính:
Tóm_tắt_cốt_truyện

-----
Danh sách các nhân vật:
{characters}

-----
Tóm tắt các chương truyện trước:
{summaries}

-----
Tóm tắt chính:
"""

class ChapterSummary(BaseModel):
    character: str = Field(description="Danh sách các nhân vật được đề cập. Mỗi dòng liệt kê một nhân vật (Tên_nhân_vât: giới thiệu về nhân vật)")
    summary: str = Field(description="Tóm tắt nội dung chính của chương truyện dưới 6 câu.")

class SummarizeEvent(Event):
    summary: ChapterSummary = Field(description="Tóm tắt các chương truyện trước và danh sách các nhân vật")

class BookSummary(Workflow):
    def __init__(
        self,
        story_paths,
        gather_chapters = 1,
        max_chapters: int = 1000,
        big_summary_interval: int = 100,
        system_prompt = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if system_prompt is None:
            system_prompt = """
            Bạn là một trợ lí nhiệm vụ của bạn là tóm tắt lại một câu chuyện.\
            trả lời bằng tiếng Việt.
            """
        self.story_paths = story_paths
        self.big_summary_interval = big_summary_interval
        self.max_chapters = max_chapters
        self.gather_chapters = gather_chapters
        self.llm = GoogleGenAI(model="models/gemini-2.0-flash", system_prompt=system_prompt)
        self.chapter_generator = self.get_chapter(gather_chapters)
        # Rate limiting tracking
        self.request_timestamps = []
        self.daily_request_count = 0
        self.daily_reset_time = time.time() + 24 * 3600  # Reset daily counter every 24 hours
        
    async def _rate_limited_llm_call(self, llm_method, *args, **kwargs):
        """
        Wrapper for LLM calls with rate limiting for Google Gemini free tier:
        - 10 requests per minute
        - 1500 requests per day
        """
        max_retries = 5
        base_delay = 6  # 6 seconds = 60/10 for rate limiting
        
        for attempt in range(max_retries):
            try:
                # Check and wait for rate limits
                await self._check_rate_limits()
                
                # Make the LLM call
                if asyncio.iscoroutinefunction(llm_method):
                    result = await llm_method(*args, **kwargs)
                else:
                    result = llm_method(*args, **kwargs)
                
                # Track successful request
                self._track_request()
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a rate limit error
                if any(term in error_msg for term in ['quota', 'rate limit', 'too many requests', '429']):
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limit exceeded. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # For other errors, re-raise immediately
                    raise e
        
        # If all retries failed
        raise Exception(f"Failed to complete LLM call after {max_retries} attempts")
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset daily counter if needed
        if current_time > self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = current_time + 24 * 3600
        
        # Check daily limit
        if self.daily_request_count >= 1500:
            sleep_time = self.daily_reset_time - current_time
            print(f"Daily request limit (1500) reached. Sleeping for {sleep_time/3600:.2f} hours")
            await asyncio.sleep(sleep_time)
            self.daily_request_count = 0
            self.daily_reset_time = time.time() + 24 * 3600
        
        # Clean old timestamps (older than 1 minute)
        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 60]
        
        # Check per-minute limit
        if len(self.request_timestamps) >= 10:
            oldest_request = min(self.request_timestamps)
            sleep_time = 60 - (current_time - oldest_request)
            if sleep_time > 0:
                print(f"Per-minute limit (10) reached. Sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
    
    def _track_request(self):
        """Track a successful request"""
        current_time = time.time()
        self.request_timestamps.append(current_time)
        self.daily_request_count += 1
        
    def get_chapter(self, gather = 1):
        gather_chapters = []
        for chapter_path in self.story_paths:
            try:
                with open(chapter_path, "r", encoding="utf-8") as f:
                    chapter_text = f.read()
                    gather_chapters.append(chapter_text)
                    if len(gather_chapters) == gather:
                        cop = gather_chapters
                        gather_chapters = []
                        print(f"Yielding {len(cop)} chapters with total length: {sum(len(ch) for ch in cop)}")
                        yield '\n'.join(cop)
            except FileNotFoundError:
                print(f"File not found: {chapter_path}")
            except Exception as e:
                print(f"Error reading {chapter_path}: {e}")
        
        # Yield any remaining chapters
        if gather_chapters:
            print(f"Yielding final {len(gather_chapters)} chapters")
            yield '\n'.join(gather_chapters)

    @step
    async def summarize_chapter(
        self,
        ctx: Context,
        ev: StartEvent | SummarizeEvent,
    ) -> SummarizeEvent | StopEvent:
        summaries_segment = await ctx.store.get("chapter_summaries", [])
        chapter_summary = '\n'.join(summary.summary for summary in summaries_segment)
        chapters_summary_list = await ctx.store.get("big_summaries", [])
        chapters_summary = '\n'.join(summary for summary in chapters_summary_list)
        summaries = chapters_summary + '\n' + chapter_summary
        
        characters = await ctx.store.get("characters", "")
        
        # Get the next chapter from the instance generator
        try:
            chapter_text = next(self.chapter_generator)
        except StopIteration:
            chapter_text = None
        
        if (len(summaries_segment)*self.gather_chapters < self.max_chapters) and chapter_text:
            if (summaries_segment == []) and (chapters_summary_list == []):
                chapter_summary = await self._rate_limited_llm_call(
                    self.llm.structured_predict,
                    ChapterSummary,
                    PromptTemplate(FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL),
                    chapter_text = chapter_text,
                )
            else:
                chapter_summary = await self._rate_limited_llm_call(
                    self.llm.structured_predict,
                    ChapterSummary,
                    PromptTemplate(EXTRACT_CHARACTERSNSUMMARY_PROMPT_TMPL),
                    characters = characters,
                    previous_summary = summaries,
                    chapter_text = chapter_text,
                )
            summaries_segment.append(chapter_summary)
            await ctx.store.set("chapter_summaries", summaries_segment)
            await ctx.store.set("characters", chapter_summary.character)
            
            if (len(summaries_segment)*self.gather_chapters + 1) % self.big_summary_interval == 0:
                long_summary = await self.big_summary(ctx, summaries_segment)
                await ctx.store.set("big_summaries", chapters_summary_list + [long_summary])
                await ctx.store.set("chapter_summaries", [])
            
            print(chapter_summary.summary)
            print("-"*40)
            return SummarizeEvent(summary=chapter_summary)
        
        return StopEvent(result=summaries)
        
    async def big_summary(
        self,
        ctx: Context,
        chapter_summary,
    ) -> str:
        characters = await ctx.store.get("characters", "")
        summaries = '\n'.join(summary.summary for summary in chapter_summary)
        big_summary_response = await self._rate_limited_llm_call(
            self.llm.achat,
            [ChatMessage(role="user", content=LONG_SUMMARY_PROMPT_TMPL.format(characters=characters,summaries=summaries))]
        )
        return big_summary_response.content


if __name__ == "__main__":
    import os
    import asyncio

    story_paths = [
        os.path.join("story", "Cẩu Tại Sơ Thánh Ma Môn Làm Nhân Tài", f)
        for f in os.listdir(os.path.join("story", "Cẩu Tại Sơ Thánh Ma Môn Làm Nhân Tài"))
        if f.endswith(".txt")
    ]
    story_paths.sort()
    w = BookSummary(story_paths, big_summary_interval=50, max_chapters=100, gather_chapters=1)

    async def main():
        result = await w.run()
        print("*"*10 + "final summary" + "*"*10)
        print(result)
        # draw_most_recent_execution()

    asyncio.run(main())