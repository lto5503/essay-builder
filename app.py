import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="생각 징검다리 - 서논술형 빌더", page_icon="📝", layout="centered")

DATA_FILE = "submissions.csv"

# --- [사이드바: 설정] ---
st.sidebar.header("🔑 시스템 설정")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)

st.sidebar.markdown("---")
teacher_mode = st.sidebar.checkbox("👩‍🏫 선생님 전용 관리자 모드")

good_example = ""
good_reason = ""

if teacher_mode:
    st.sidebar.subheader("🧠 Agent C: 기준 학습 (Few-Shot)")
    good_example = st.sidebar.text_area("모범 답안 (예시)")
    good_reason = st.sidebar.text_area("루브릭/평가 기준")
    
    if os.path.exists(DATA_FILE):
        df_saved = pd.read_csv(DATA_FILE)
        st.sidebar.write(f"총 제출: {len(df_saved)}건")
        st.sidebar.download_button(
            label="📥 데이터 다운로드",
            data=df_saved.to_csv(index=False).encode('utf-8-sig'),
            file_name="essay_submissions.csv",
            mime="text/csv",
        )

# --- [메인 UI] ---
st.title("📝 생각 징검다리: 서논술형 빌더")

if "step" not in st.session_state:
    st.session_state.step = 1

st.progress(st.session_state.step / 5)

if st.session_state.step == 1:
    st.subheader("1단계: 나의 주장 세우기 🎯")
    claim = st.text_input("이 문제에 대해 나는 어떤 입장을 가지고 있나요?", value=st.session_state.get("claim", ""))
    if st.button("다음 ➡️"):
        if claim.strip():
            st.session_state.claim = claim
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.subheader("2단계: 타당한 근거 대기 💡")
    reason = st.text_area("왜 그렇게 생각하나요?", value=st.session_state.get("reason", ""))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("다음 ➡️"):
            if reason.strip():
                st.session_state.reason = reason
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.subheader("3단계: 반론 생각하고 넘어서기 🛡️")
    counter_arg = st.text_area("다른 친구들이 반대한다면 어떻게 대답할까요?", value=st.session_state.get("counter_arg", ""))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전"):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("AI 피드백 받기 ✨"):
            if counter_arg.strip():
                st.session_state.counter_arg = counter_arg
                st.session_state.draft_1 = f"{st.session_state.claim} {st.session_state.reason} {st.session_state.counter_arg}"
                
                if api_key:
                    with st.spinner("논리를 분석하고 질문을 준비 중입니다... ⚙️"):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            
                            # Agent A: 논리 분석
                            eval_prompt = f"다음 초등학생 글의 논리적 결손을 2문장으로 진단하세요. 기준:{good_reason}\n글:{st.session_state.draft_1}"
                            st.session_state.agent_a_eval = model.generate_content(eval_prompt).text
                            
                            # Agent B: 꼬리 질문 생성
                            tutor_prompt = f"분석 리포트:{st.session_state.agent_a_eval}\n학생이 빈틈을 채우도록 다정한 꼬리 질문 1개를 하세요. 정답 금지."
                            st.session_state.ai_feedback = model.generate_content(tutor_prompt).text
                        except Exception as e:
                            st.session_state.ai_feedback = "AI 연결 오류가 발생했어요."
                else:
                    st.session_state.ai_feedback = "[테스트] 더 구체적인 예시를 하나만 들어줄 수 있을까?"
                
                st.session_state.step = 4
                st.rerun()

elif st.session_state.step == 4:
    st.subheader("4단계: 한 걸음 더 나아가기 (고쳐 쓰기) 🚀")
    st.info(f"**나의 첫 번째 글:**\n{st.session_state.draft_1}")
    st.warning(f"**🤖 AI 선생님의 질문:**\n{st.session_state.get('ai_feedback', '')}")
    
    draft_2 = st.text_area("질문을 생각하며 글을 더 멋지게 다듬어 보세요!", value=st.session_state.draft_1, height=150)
    
    if st.button("성장도 분석 및 최종 완성 📈"):
        st.session_state.draft_2 = draft_2
        if api_key:
            with st.spinner("얼마나 성장했는지 분석 중입니다..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    growth_prompt = f"""
                    초안: {st.session_state.draft_1}
                    수정본: {st.session_state.draft_2}
                    이 학생이 초안에서 수정본으로 넘어오며 어떤 논리적 발전(예: 구체성, 근거 추가 등)을 이루었는지 2문장으로 폭풍 칭찬하며 분석해 주세요.
                    """
                    st.session_state.agent_c_growth = model.generate_content(growth_prompt).text
                except Exception:
                    st.session_state.agent_c_growth = "성장도 분석 중 오류가 발생했습니다."
        else:
            st.session_state.agent_c_growth = "[테스트] 초안보다 훨씬 더 이유가 구체적으로 변해서 훌륭해요!"
        
        st.session_state.step = 5
        st.rerun()

elif st.session_state.step == 5:
    st.subheader("5단계: 최종 완성 및 자가 진단 📜")
    st.success(f"**최종 완성된 글:**\n{st.session_state.draft_2}")
    
    st.markdown("### 🌟 AI 선생님의 성장 리포트")
    st.info(st.session_state.get("agent_c_growth", ""))
    
    if teacher_mode:
        st.markdown("🔒 **[선생님 전용] Agent A 논리 분석 리포트**")
        st.error(st.session_state.get("agent_a_eval", ""))
    
    st.markdown("---")
    student_name = st.text_input("이름을 입력하고 제출하세요:")
    
    if st.button("📤 제출하기"):
        if student_name.strip():
            new_data = {
                "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "student_name": [student_name],
                "draft_1": [st.session_state.draft_1],
                "ai_feedback": [st.session_state.ai_feedback],
                "draft_2": [st.session_state.draft_2],
                "growth_report": [st.session_state.agent_c_growth]
            }
            df_new = pd.DataFrame(new_data)
            
            if os.path.exists(DATA_FILE):
                df_combined = pd.concat([pd.read_csv(DATA_FILE), df_new], ignore_index=True)
            else:
                df_combined = df_new
            
            df_combined.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
            st.success("🎉 성공적으로 제출되었습니다!")
            st.balloons()