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
import json
import re
from llama_index.utils.workflow import draw_most_recent_execution
from numpy import block

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, ToolOutput
from typing import Any, List
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.prompts import PromptTemplate

import sys
sys.path.append("..")
from trackapi import TrackApi
from prompt import (
    FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL,
    EXTRACT_CHARACTERSNSUMMARY_PROMPT_TMPL,
    LONG_SUMMARY_PROMPT_TMPL,
)
load_dotenv()


class ChapterSummary(BaseModel):
    character: str = Field(description="Danh sách các nhân vật được đề cập. Mỗi dòng liệt kê một nhân vật (Tên_nhân_vât: giới thiệu về nhân vật)")
    summary: str = Field(description="Tóm tắt nội dung chính của chương truyện dưới 6 câu.")

class SummarizeEvent(Event):
    summary: ChapterSummary = Field(description="Tóm tắt các chương truyện trước và danh sách các nhân vật")

class BookSummary(Workflow, TrackApi):
    def __init__(
        self,
        story_paths,
        gather_chapters=1,
        max_chapters: int = 1000,
        big_summary_interval: int = 100,
        quota_per_minute: int = 15,
        system_prompt=None,
        **kwargs
    ):
        Workflow.__init__(self, **kwargs)
        TrackApi.__init__(self, quota_per_minute)

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
    
    max_chapters = 100
    gather_chapters = 1
    big_summary_interval = 50
    quota_per_minute = 15  # Adjust based on your API tier
    summary_time_per_chapter = 20
    name = "Cẩu Tại Sơ Thánh Ma Môn Làm Nhân Tài"

    story_paths = [
        os.path.join("story", name, f)
        for f in os.listdir(os.path.join("story", name))
        if f.endswith(".txt")
    ]
    story_paths.sort()
    w = BookSummary(
        story_paths, 
        big_summary_interval=big_summary_interval, 
        max_chapters=max_chapters, 
        gather_chapters=gather_chapters,
        quota_per_minute=quota_per_minute  # Adjust based on your API tier
    )

    async def main():
        result = await w.run(timeout=max_chapters//gather_chapters*summary_time_per_chapter)
        print("*"*10 + "final summary" + "*"*10)
        print(result)
        return result
        # draw_most_recent_execution()

    result = asyncio.run(main())
    with open(os.path.join("summary", name + "_summary.txt"), "w", encoding="utf-8") as f:
        f.write(result)