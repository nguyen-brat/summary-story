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
from llama_index.utils.workflow import draw_most_recent_execution
from numpy import block

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, ToolOutput
from typing import Any, List
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.prompts import PromptTemplate

load_dotenv()

FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL = """Mỗi dòng liệt kê một nhân vật gồm tên nhân vật, giới thiệu về nhân vật. \
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
    summary: ChapterSummary = Field(description="Tóm tắt các chương truyện trước")

class BookSummary(Workflow):
    def __init__(
        self,
        story_paths,
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
        self.llm = GoogleGenAI(model="models/gemini-2.0-flash", system_prompt=system_prompt)
        # Initialize the chapter generator
        self.chapter_generator = self.get_chapter()
        
    def get_chapter(self, gather = 1):
        print(f"Starting get_chapter with {len(self.story_paths)} story paths")
        gather_chapters = []
        for chapter_path in self.story_paths:
            print(f"Processing chapter: {chapter_path}")
            try:
                with open(chapter_path, "r", encoding="utf-8") as f:
                    chapter_text = f.read()
                    print(f"Read {len(chapter_text)} characters from {chapter_path}")
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
        
        if (len(summaries_segment) <= self.max_chapters) and chapter_text:
            if summaries_segment == [] and chapters_summary_list == []:
                chapter_summary = self.llm.structured_predict(
                    ChapterSummary,
                    PromptTemplate(FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL),
                    chapter_text = chapter_text,
                )
            else:
                chapter_summary = self.llm.structured_predict(
                    ChapterSummary,
                    PromptTemplate(EXTRACT_CHARACTERSNSUMMARY_PROMPT_TMPL),
                    characters = characters,
                    previous_summary = summaries,
                    chapter_text = chapter_text,
                )
            summaries_segment.append(chapter_summary)
            await ctx.store.set("chapter_summaries", summaries_segment)
            
            if (len(summaries_segment) + 1) % self.big_summary_interval == 0:
                long_summary = self.big_summary(ctx, summaries_segment)
                ctx.store.set("big_summaries", chapters_summary_list + [long_summary])
                await ctx.store.set("chapter_summaries", [])
            return SummarizeEvent(summary=chapter_summary)
        
        return StopEvent(result=summaries)
        
    async def big_summary(
        self,
        ctx: Context,
        chapter_summary,
    ) -> SummarizeEvent:
        characters = await ctx.store.get("characters", "")
        summaries = '\n'.join(summary.summary for summary in chapter_summary)
        big_summary = self.llm.achat(
            [ChatMessage(role="user", content=LONG_SUMMARY_PROMPT_TMPL.format(characters=characters,summaries=summaries))]
        ).content
        return big_summary


if __name__ == "__main__":
    import os
    import asyncio

    story_paths = [
        os.path.join("story", "Cẩu Tại Sơ Thánh Ma Môn Làm Nhân Tài", f)
        for f in os.listdir(os.path.join("story", "Cẩu Tại Sơ Thánh Ma Môn Làm Nhân Tài"))
        if f.endswith(".txt")
    ]

    w = BookSummary(story_paths, big_summary_interval=10, max_chapters=1)

    async def main():
        result = await w.run()
        print(result)
        # draw_most_recent_execution()

    asyncio.run(main())