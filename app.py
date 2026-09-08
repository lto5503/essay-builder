import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="생각 징검다리 - 서논술형 빌더", page_icon="📝", layout="centered")

# 데이터 저장을 위한 CSV 파일 경로
DATA_FILE = "submissions.csv"

st.title("📝 생각 징검다리: 서논술형 빌더")
st.write("단계별로 생각을 정리하여 한 편의 멋진 글을 완성해 보세요!")

# 사이드바 설정 (API 키 및 선생님 전용 모드)
st.sidebar.header("🔑 설정 및 관리자")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)

st.sidebar.markdown("---")
teacher_mode = st.sidebar.checkbox("👩‍🏫 선생님 전용 관리자 모드")

if teacher_mode:
    st.sidebar.subheader("📊 제출된 학생 글 목록")
    if os.path.exists(DATA_FILE):
        df_saved = pd.read_csv(DATA_FILE)
        st.sidebar.write(f"총 제출 건수: {len(df_saved)}건")
        st.sidebar.dataframe(df_saved[["timestamp", "claim"]])
        
        # CSV 다운로드 버튼
        csv_data = df_saved.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="📥 전체 제출 데이터 다운로드 (CSV)",
            data=csv_data,
            file_name="essay_submissions.csv",
            mime="text/csv",
        )
    else:
        st.sidebar.info("아직 제출된 데이터가 없습니다.")
    st.markdown("---")

# 세션 상태 초기화
if "step" not in st.session_state:
    st.session_state.step = 1

# 진행 상황 표시
st.progress(st.session_state.step / 4)
st.write(f"현재 단계: **{st.session_state.step} / 4 단계**")

# 1단계: 주장
if st.session_state.step == 1:
    st.subheader("1단계: 나의 주장 세우기 🎯")
    st.write("이 문제에 대해 나는 어떤 입장을 가지고 있나요?")
    claim = st.text_input("예: 나는 스마트폰 사용 시간을 제한해야 한다고 생각한다.", value=st.session_state.get("claim", ""))
    
    if st.button("다음 단계로 ➡️"):
        if not claim.strip():
            st.warning("내용을 입력해 주세요!")
        else:
            st.session_state.claim = claim
            st.session_state.step = 2
            st.rerun()

# 2단계: 근거
elif st.session_state.step == 2:
    st.subheader("2단계: 타당한 근거 대기 💡")
    st.write("왜 그렇게 생각하나요? 뒷받침할 수 있는 이유를 적어보세요.")
    reason = st.text_area("예: 왜냐하면 시력도 나빠지고 공부에 집중할 수 없기 때문이다.", value=st.session_state.get("reason", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전 단계"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("다음 단계로 ➡️"):
            if not reason.strip():
                st.warning("근거를 입력해 주세요!")
            else:
                st.session_state.reason = reason
                st.session_state.step = 3
                st.rerun()

# 3단계: 반론 및 재반박
elif st.session_state.step == 3:
    st.subheader("3단계: 반론 생각하고 넘어서기 🛡️")
    st.write("다른 친구들이 '하지만 ~할 수도 있어'라고 반대한다면 어떻게 대답할 수 있을까요?")
    counter_arg = st.text_area("예: 물론 편리한 점도 있지만, 건강을 생각하면 제한이 더 중요하다.", value=st.session_state.get("counter_arg", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전 단계"):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("AI 피드백 및 글 완성하기 ✨"):
            if not counter_arg.strip():
                st.warning("내용을 입력해 주세요!")
            else:
                st.session_state.counter_arg = counter_arg
                
                if api_key:
                    with st.spinner("AI 선생님이 생각을 넓혀주는 질문을 고민 중이에요... 🤔"):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"""
                            너는 초등학생의 글쓰기를 돕는 친절한 소크라테스 선생님이야.
                            학생이 작성한 글의 뼈대야:
                            - 주장: {st.session_state.claim}
                            - 근거: {st.session_state.reason}
                            - 반론 극복: {st.session_state.counter_arg}
                            
                            이 내용을 바탕으로 정답을 알려주지 말고, 학생이 생각을 더 깊게 확장할 수 있도록 부드러운 꼬리 질문을 1~2문장으로 던져줘.
                            """
                            response = model.generate_content(prompt)
                            st.session_state.ai_feedback = response.text
                        except Exception as e:
                            st.session_state.ai_feedback = f"API 연동 중 오류가 발생했습니다: {e}"
                else:
                    st.session_state.ai_feedback = "API 키가 입력되지 않아 시뮬레이션 질문을 던져요: '만약 이 규칙을 어기는 친구가 있다면 어떻게 설득할 수 있을까요?'"
                
                st.session_state.step = 4
                st.rerun()

# 4단계: 최종 완성 및 자가 진단 루브릭 & 제출
elif st.session_state.step == 4:
    st.subheader("4단계: 나의 생각 완성본 및 자가 진단 📜")
    st.success("와! 징검다리를 모두 건너 멋진 글이 완성되었어요.")
    
    final_essay = f"{st.session_state.claim} {st.session_state.reason} {st.session_state.counter_arg}"
    
    st.markdown("### 📝 완성된 글")
    st.info(final_essay)
    
    st.markdown("### 🤖 생각 넓히기 AI 선생님의 질문")
    st.warning(st.session_state.get("ai_feedback", "질문이 없습니다."))
    
    st.markdown("---")
    st.markdown("### ✅ 스스로 점검하는 배움 성장 확인표 (자가 진단)")
    check1 = st.checkbox("나의 주장이 뚜렷하게 잘 드러났나요?")
    check2 = st.checkbox("타당한 이유(근거)를 구체적으로 작성했나요?")
    check3 = st.checkbox("다른 사람의 반대 의견을 고려해 보았나요?")
    
    # 학생 이름 입력 (제출용)
    student_name = st.text_input("학생 이름을 입력하고 제출해 주세요:", value=st.session_state.get("student_name", ""))
    
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        if st.button("📤 선생님께 최종 제출하기"):
            if not student_name.strip():
                st.error("이름을 입력해야 제출할 수 있어요!")
            elif not (check1 and check2 and check3):
                st.warning("자가 진단 체크리스트를 모두 확인해 주세요!")
            else:
                # 데이터 저장 로직
                new_data = {
                    "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "student_name": [student_name],
                    "claim": [st.session_state.claim],
                    "reason": [st.session_state.reason],
                    "counter_arg": [st.session_state.counter_arg],
                    "final_essay": [final_essay],
                    "ai_feedback": [st.session_state.get("ai_feedback", "")]
                }
                df_new = pd.DataFrame(new_data)
                
                if os.path.exists(DATA_FILE):
                    df_existing = pd.read_csv(DATA_FILE)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                else:
                    df_combined = df_new
                
                df_combined.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
                st.success(f"🎉 {student_name} 학생의 글이 성공적으로 제출되었습니다!")
                
    with col_sub2:
        if st.button("🔄 처음부터 다시 쓰기"):
            st.session_state.step = 1
            st.rerun()