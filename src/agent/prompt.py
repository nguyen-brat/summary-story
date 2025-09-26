FIRST_EXTRACTCHARACTERNSUMMARY_PROMPT_TMPL = """Mỗi dòng liệt kê một nhân vật gồm tên nhân vật, giới thiệu về nhân vật được cung cấp dưới đây. \
Tóm tắt chương truyện được cung cấp dưới đây. trả lời theo mẫu không trả lời thêm gì khác:
{characters}
{previous_summary}
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
Tóm tắt chương truyện được cung cấp dưới đây, tóm tắt liền mạch với tóm tắt của các chương truyện trước được cung cấp. \
trả lời theo mẫu không trả lời thêm gì khác:

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
viết lại thành một tóm tắt những diễn biến chính. Hãy viết một cách liền mạch với các tóm tắt trước đó được cung cấp. \
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

REWRITE_SUMMARY_PROMPT_TMPL = """Viết lại tóm tắt dưới đây thành một đoạn giới thiệu cốt truyện chuyện nghiệp hơn. \
Dựa vào danh sách giới thiệu các nhân vật được cung cấp dưới đây, nếu lần đầu nhân vật được đề cập tới hãy giới thiệu nhân vật đó trong tóm tắt một cách ngắn gọn. \
không thêm bớt ý, không thay đổi ý nghĩa tránh lặp từ quá nhiều. \
Trả lời ngay vào tóm tắt không trả lời thêm gì khác.
Tóm tắt:
{summary}

Tóm tắt rút gọn:
"""