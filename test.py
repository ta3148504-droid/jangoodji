import streamlit as st
import re
import os
from dotenv import load_dotenv
from google import genai

# ------------------ 환경변수 ------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ GOOGLE_API_KEY가 없습니다 (.env 확인)")
    st.stop()

client = genai.Client(api_key=api_key)

# ------------------ 파일 로드 ------------------
qa_path = "검침QA.txt"
manual_path = "검침_manual.txt"

try:
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_text = f.read()
except:
    st.error("❌ 검침QA.txt 파일 없음")
    st.stop()

try:
    with open(manual_path, "r", encoding="utf-8") as f:
        manual_text = f.read()
except:
    st.error("❌ 검침_manual.txt 파일 없음")
    st.stop()

# ------------------ QA 파싱 ------------------
blocks = [b.strip() for b in qa_text.split('---') if b.strip()]

qa_items = []
for block in blocks:
    q = re.search(r"Q\d+:\s*(.*)", block)
    a = re.search(r"A\d+:\s*(.*)", block)
    t = re.search(r"T\d+:\s*(.*)", block)

    qa_items.append({
        "q": q.group(1) if q else "",
        "a": a.group(1) if a else "",
        "t": t.group(1) if t else ""
    })

# ------------------ 검색 ------------------
def search_qa(question):
    results = []
    for item in qa_items:
        text = item["q"] + " " + item["a"] + " " + item["t"]

        score = 0
        for word in question.split():
            if word in text:
                score += 1

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in results[:3]]


def search_manual(question):
    results = []
    paragraphs = [p.strip() for p in manual_text.split("\n\n") if p.strip()]

    for para in paragraphs:
        score = 0
        for word in question.split():
            if word in para:
                score += 1

        if score > 0:
            results.append((score, para))

    results.sort(key=lambda x: x[0], reverse=True)
    return [para for score, para in results[:3]]

# ------------------ 답변 생성 ------------------
def get_answer(question):
    retrieved_qa = search_qa(question)
    retrieved_manual = search_manual(question)

    if not retrieved_qa and not retrieved_manual:
        return "문서에서 확인되지 않습니다."

    qa_context = "\n\n".join([
        f"질문: {i['q']}\n답변: {i['a']}\n태그: {i['t']}"
        for i in retrieved_qa
    ])

    manual_context = "\n\n".join(retrieved_manual)

    prompt = f"""
너는 검침 업무 지원 챗봇이다.
반드시 참고자료에 있는 내용만 근거로 답변해라.

참고자료에 없는 내용은 절대 생성하지 말고,
유사해 보여도 문서에 명확히 없으면 사용하지 마라.
추측, 상식, 일반적인 설명 금지.

문장을 재구성하거나 요약하지 말고,
가능한 한 원문 표현을 그대로 사용하여 답변해라.

[QA 참고자료]
{qa_context}

[매뉴얼 참고자료]
{manual_context}

[질문]
{question}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ 오류 발생: {e}"

# ------------------ UI ------------------
st.set_page_config(page_title="검침 챗봇", page_icon="💬")
st.title("검침 챗봇 💬")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 입력
user_input = st.chat_input("질문을 입력하세요")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    answer = get_answer(user_input)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    with st.chat_message("assistant"):
        st.write(answer)