import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="에듀씽크 AI 플랫폼", page_icon="🎓", layout="wide")

SUBMISSION_FILE = "submissions.csv"
RUBRIC_FILE = "rubrics.csv"

# --- [API 키 자동 로드 (화면 노출 없음)] ---
api_connected = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_connected = True

# --- [초기 루브릭 파일 세팅] ---
if not os.path.exists(RUBRIC_FILE):
    df_init_rubric = pd.DataFrame([
        {
            "id": 1,
            "title": "초등 5-6학년: 교내 스마트폰 자율 사용 찬반",
            "good_example": "스마트폰 자율 사용을 허용해야 한다. 디지털 학습 도구로 활용할 수 있고 자기 조절 능력을 기를 수 있기 때문이다. 물론 중독 우려도 있지만 규칙을 정하면 해결된다.",
            "criteria": "1) 주장 명확성 2) 구체적 근거 2가지 제시 3) 반론 수용 및 대안 제시"
        },
        {
            "id": 2,
            "title": "초등 3-4학년: 환경 보호를 위한 일회용품 제한",
            "good_example": "학교 급식실에서 일회용품 사용을 줄여야 한다. 쓰레기가 썩는 데 수백 년이 걸리기 때문이다. 설거지가 번거롭더라도 다회용기를 써야 한다.",
            "criteria": "1) 일상 실천 가능성 2) 환경 파괴 인과관계 설명 3) 쉬운 어휘 사용"
        }
    ])
    df_init_rubric.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "사용할 프로그램을 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🧠 [선생님] Agent C 루브릭 금고", "📊 [선생님] 학생 제출 및 채점 현황"]
    )
    st.markdown("---")
    if api_connected:
        st.success("🟢 AI 학습 엔진 정상 가동 중")
    else:
        st.error("🔴 AI 엔진 설정이 필요합니다 (.streamlit/secrets.toml)")

# ==============================================================================
# 프로그램 1: [학생] 생각 징검다리 글쓰기
# ==============================================================================
if menu == "📝 [학생] 생각 징검다리 글쓰기":
    st.header("📝 생각 징검다리: 서논술형 쓰기 훈련")
    st.caption("주제에 맞춰 한 단계씩 생각을 징검다리처럼 건너보세요.")

    df_rubrics = pd.read_csv(RUBRIC_FILE)
    topic_list = df_rubrics["title"].tolist()
    selected_topic = st.selectbox("📌 오늘 도전할 논제를 선택하세요:", topic_list)
    current_rubric = df_rubrics[df_rubrics["title"] == selected_topic].iloc[0]

    st.info(f"**💡 글쓰기 목표 기준:** {current_rubric['criteria']}")

    if "step" not in st.session_state:
        st.session_state.step = 1

    steps = ["1. 주장 세우기", "2. 근거 제시", "3. 반론 극복", "4. AI 핑퐁 질문", "5. 다듬기 및 제출"]
    st.progress(st.session_state.step / 5)
    st.caption(f"진행 단계: **{steps[st.session_state.step - 1]}**")

    # Step 1: 주장
    if st.session_state.step == 1:
        st.subheader("🎯 1단계: 나의 입장(주장) 밝히기")
        claim = st.text_input("이 문제에 대해 어떻게 생각하나요?", value=st.session_state.get("claim", ""), placeholder="나는 ~라고 생각한다.")
        if st.button("다음 단계 ➡️"):
            if claim.strip():
                st.session_state.claim = claim
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("입장을 한 줄로 적어주세요!")

    # Step 2: 근거
    elif st.session_state.step == 2:
        st.subheader("💡 2단계: 주장을 뒷받침할 구체적 근거 대기")
        st.write(f"**나의 주장:** {st.session_state.claim}")
        reason = st.text_area("왜 그렇게 생각하나요? 2가지 이상의 이유를 적어보세요.", value=st.session_state.get("reason", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 1
                st.rerun()
        with c2:
            if st.button("다음 단계 ➡️"):
                if reason.strip():
                    st.session_state.reason = reason
                    st.session_state.step = 3
                    st.rerun()

    # Step 3: 반론 극복
    elif st.session_state.step == 3:
        st.subheader("🛡️ 3단계: 반대 의견 생각하고 극복하기")
        counter = st.text_area("반대하는 친구들의 생각과 그것을 넘어설 나의 생각은?", value=st.session_state.get("counter", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 2
                st.rerun()
        with c2:
            if st.button("AI 소크라테스 코치에게 검단받기 ✨"):
                if not counter.strip():
                    st.error("반대 의견에 대한 생각을 적어주세요!")
                elif not api_connected:
                    st.error("AI 엔진 키 설정이 되어있지 않습니다.")
                else:
                    st.session_state.counter = counter
                    draft_text = f"주장: {st.session_state.claim}\n근거: {st.session_state.reason}\n반론: {st.session_state.counter}"
                    st.session_state.draft_1 = draft_text

                    with st.spinner("AI 튜터가 글의 논리를 정밀 분석 중입니다..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.6-flash')
                            prompt = f"""
                            당신은 초등학생의 논리적 사고를 키워주는 소크라테스 교사입니다.
                            [교사 기준/루브릭]: {current_rubric['criteria']}
                            [모범 사례]: {current_rubric['good_example']}
                            
                            [학생이 쓴 글]:
                            {draft_text}

                            지침:
                            1. 절대 정답을 바로 써주거나 대신 고쳐주지 마세요.
                            2. 글에서 가장 논리가 부족한 결손 지점을 파악하세요.
                            3. 학생이 생각을 넓히고 보완할 수 있는 다정한 꼬리 질문 1개를 2문장 이내로 작성하세요.
                            """
                            resp = model.generate_content(prompt)
                            st.session_state.socratic_question = resp.text
                            st.session_state.step = 4
                            st.rerun()
                        except Exception as e:
                            st.error(f"AI 통신 오류: {e}")

    # Step 4: 다듬기
    elif st.session_state.step == 4:
        st.subheader("🚀 4단계: 생각을 더 깊게 다듬기")
        st.warning(f"**🤖 소크라테스 튜터의 생각 질문:**\n\n{st.session_state.socratic_question}")
        st.markdown("위 질문에 대한 생각을 보태어, 전체 글을 자연스러운 한 편의 완성문으로 다듬어 보세요.")
        
        final_draft = st.text_area("완성된 글 다듬기:", height=150, value=st.session_state.get("final_draft", ""))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 3
                st.rerun()
        with c2:
            if st.button("최종 완성 및 성장 분석 📈"):
                if not final_draft.strip():
                    st.error("완성된 글을 작성해 주세요!")
                else:
                    st.session_state.final_draft = final_draft
                    with st.spinner("AI가 초안 대비 성장을 분석 중입니다..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.6-flash')
                            eval_prompt = f"""
                            초등학생의 글쓰기 수정 전/후 성장 보고서를 작성해 주세요.
                            [초안]: {st.session_state.draft_1}
                            [수정본]: {st.session_state.final_draft}
                            [교사 기준]: {current_rubric['criteria']}

                            출력 형식:
                            1. 성장한 점 (어떤 근거나 설명이 보강되었는지 구체적 칭찬)
                            2. 종합 격려 (한 문장)
                            """
                            eval_resp = model.generate_content(eval_prompt)
                            st.session_state.growth_report = eval_resp.text
                            st.session_state.step = 5
                            st.rerun()
                        except Exception as e:
                            st.error(f"통신 오류: {e}")

    # Step 5: 최종 제출
    elif st.session_state.step == 5:
        st.subheader("📜 5단계: 나의 생각 최종본 및 성장 리포트")
        st.success(f"**내가 완성한 글:**\n\n{st.session_state.final_draft}")
        st.info(f"**🌟 AI 성장 분석표:**\n\n{st.session_state.growth_report}")
        
        student_name = st.text_input("학생 이름을 입력하고 제출하세요:")
        if st.button("📤 최종 제출하기"):
            if student_name.strip():
                new_row = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "student_name": student_name,
                    "topic": selected_topic,
                    "final_draft": st.session_state.final_draft,
                    "growth_report": st.session_state.growth_report
                }
                df_sub = pd.DataFrame([new_row])
                if os.path.exists(SUBMISSION_FILE):
                    df_sub.to_csv(SUBMISSION_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
                else:
                    df_sub.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                st.success("🎉 성공적으로 제출되었습니다!")
                st.balloons()
            else:
                st.error("이름을 입력해 주세요!")

# ==============================================================================
# 프로그램 2: [선생님] Agent C 루브릭 금고
# ==============================================================================
elif menu == "🧠 [선생님] Agent C 루브릭 금고":
    st.header("🧠 Agent C: 기준 학습용 루브릭 금고")
    st.caption("AI의 Few-Shot 평가 기준(논제, 모범 답안, 평가 루브릭)을 등록하고 관리합니다.")

    tab1, tab2 = st.tabs(["📋 등록된 루브릭 목록", "➕ 신규 루브릭 등록"])
    df_rubrics = pd.read_csv(RUBRIC_FILE)

    with tab1:
        st.subheader(f"등록된 루브릭: 총 {len(df_rubrics)}건")
        for _, row in df_rubrics.iterrows():
            with st.expander(f"📌 [{row['id']}] {row['title']}"):
                st.markdown(f"**🎯 채점 기준 (Rubric):**\n{row['criteria']}")
                st.markdown(f"**📝 모범 답안:**\n{row['good_example']}")

    with tab2:
        st.subheader("새로운 논제 등록")
        new_title = st.text_input("논제/주제명")
        new_criteria = st.text_area("평가 기준 (AI가 지킬 규칙)")
        new_example = st.text_area("모범 답안 (Few-Shot 예시)")

        if st.button("💾 루브릭 금고에 저장"):
            if new_title and new_criteria and new_example:
                new_data = {
                    "id": len(df_rubrics) + 1,
                    "title": new_title,
                    "good_example": new_example,
                    "criteria": new_criteria
                }
                df_updated = pd.concat([df_rubrics, pd.DataFrame([new_data])], ignore_index=True)
                df_updated.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                st.success("루브릭이 저장되었습니다.")
                st.rerun()
            else:
                st.error("모든 항목을 입력해 주세요.")

# ==============================================================================
# 프로그램 3: [선생님] 제출 현황
# ==============================================================================
elif menu == "📊 [선생님] 학생 제출 및 채점 현황":
    st.header("📊 학생 제출 및 AI 성장 리포트")
    if os.path.exists(SUBMISSION_FILE):
        df_submissions = pd.read_csv(SUBMISSION_FILE)
        st.write(f"총 제출: **{len(df_submissions)}건**")
        st.dataframe(df_submissions, use_container_width=True)
        csv_download = df_submissions.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_download,
            file_name=f"student_reports_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("제출된 답안이 없습니다.")
