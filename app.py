import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os
import re

st.set_page_config(page_title="에듀씽크 AI 플랫폼", page_icon="🎓", layout="wide")

SUBMISSION_FILE = "submissions.csv"
RUBRIC_FILE = "rubrics.csv"
SCHOOL_FILE = "schools.csv"

# --- [API 키 설정] ---
api_connected = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_connected = True

# --- [초기 파일 세팅] ---
if not os.path.exists(SCHOOL_FILE):
    pd.DataFrame({"school_name": ["좌야초등학교", "왕지초등학교", "신대초등학교"]}).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')

if not os.path.exists(RUBRIC_FILE):
    df_init_rubric = pd.DataFrame([
        {
            "id": 1,
            "title": "초등 5-6학년: 교내 스마트폰 자율 사용 찬반",
            "good_example": "스마트폰 자율 사용을 허용해야 한다. 디지털 학습 도구로 활용할 수 있고 자기 조절 능력을 기를 수 있기 때문이다. 물론 중독 우려도 있지만 규칙을 정하면 해결된다.",
            "criteria": "1) 주장 명확성 2) 구체적 근거 2가지 제시 3) 반론 수용 및 대안 제시",
            "scoring_criteria": "주장의 명확성(30점), 근거의 타당성(40점), 맞춤법 및 분량(30점)"
        }
    ])
    df_init_rubric.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
else:
    df_r = pd.read_csv(RUBRIC_FILE)
    if 'scoring_criteria' not in df_r.columns:
        df_r['scoring_criteria'] = "논리성(40점), 창의성(30점), 표현력(30점)"
        df_r.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

if os.path.exists(SUBMISSION_FILE):
    df_s = pd.read_csv(SUBMISSION_FILE)
    changed = False
    for col in ['school', 'grade', 'class_num', 'score']:
        if col not in df_s.columns:
            df_s[col] = "-"
            changed = True
    if changed:
        df_s.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')

def reset_student_session():
    st.session_state.step = 1
    for key in ['claim', 'reason', 'counter', 'draft_1', 'socratic_question', 'final_draft', 'growth_report', 'ai_score']:
        if key in st.session_state:
            del st.session_state[key]

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "사용할 프로그램을 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🧠 [선생님] Agent C 루브릭 금고", "📊 [선생님] 학생 제출 및 채점 현황"]
    )
    st.markdown("---")
    if api_connected:
        st.success("🟢 AI 학습 엔진 가동 중")
    else:
        st.error("🔴 AI 엔진 설정 필요")

# ==============================================================================
# 1. [학생] 생각 징검다리
# ==============================================================================
if menu == "📝 [학생] 생각 징검다리 글쓰기":
    st.header("📝 생각 징검다리: 서논술형 쓰기 훈련")
    
    df_rubrics = pd.read_csv(RUBRIC_FILE)
    df_schools = pd.read_csv(SCHOOL_FILE)
    
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        selected_topic = st.selectbox("📌 논제 선택:", df_rubrics["title"].tolist(), key="selected_topic_box")
    with col_t2:
        st.write("")
        st.write("")
        if st.button("🔄 처음부터 쓰기"):
            reset_student_session()
            st.rerun()

    if "current_active_topic" not in st.session_state:
        st.session_state.current_active_topic = selected_topic
    elif st.session_state.current_active_topic != selected_topic:
        st.session_state.current_active_topic = selected_topic
        reset_student_session()
        st.rerun()

    current_rubric = df_rubrics[df_rubrics["title"] == selected_topic].iloc[0]
    scoring_crit = current_rubric.get("scoring_criteria", "논리성, 표현력 종합 평가")

    if "step" not in st.session_state:
        st.session_state.step = 1

    steps = ["1. 주장", "2. 근거", "3. 반론 극복", "4. AI 질문", "5. 다듬기 및 제출"]
    st.progress(st.session_state.step / 5)

    if st.session_state.step == 1:
        st.subheader("🎯 1단계: 나의 입장 밝히기")
        claim = st.text_input("어떻게 생각하나요?", value=st.session_state.get("claim", ""))
        if st.button("다음 단계 ➡️"):
            if claim.strip():
                st.session_state.claim = claim
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("입장을 적어주세요!")

    elif st.session_state.step == 2:
        st.subheader("💡 2단계: 주장을 뒷받침할 근거 대기")
        st.write(f"**나의 주장:** {st.session_state.get('claim', '')}")
        reason = st.text_area("왜 그렇게 생각하나요?", value=st.session_state.get("reason", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 1; st.rerun()
        with c2:
            if st.button("다음 단계 ➡️"):
                if reason.strip():
                    st.session_state.reason = reason
                    st.session_state.step = 3; st.rerun()

    elif st.session_state.step == 3:
        st.subheader("🛡️ 3단계: 반대 의견 생각하고 극복하기")
        counter = st.text_area("반대 의견과 그것을 넘어설 나의 생각은?", value=st.session_state.get("counter", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 2; st.rerun()
        with c2:
            if st.button("AI 소크라테스 코치에게 검단받기 ✨"):
                if not counter.strip():
                    st.error("반대 의견을 적어주세요!")
                else:
                    st.session_state.counter = counter
                    st.session_state.draft_1 = f"주장: {st.session_state.get('claim', '')}\n근거: {st.session_state.get('reason', '')}\n반론: {st.session_state.get('counter', '')}"
                    with st.spinner("논리 분석 중..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.5-flash-lite', generation_config={'max_output_tokens': 200, 'temperature': 0.7})
                            prompt = f"소크라테스 교사로서 다음 글의 논리적 결손을 파악하고, 학생이 생각을 보완할 수 있는 다정한 꼬리 질문 1개를 2문장 이내로 작성하세요.\n[글]: {st.session_state.draft_1}"
                            st.session_state.socratic_question = model.generate_content(prompt).text
                            st.session_state.step = 4
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")

    elif st.session_state.step == 4:
        st.subheader("🚀 4단계: 생각을 더 깊게 다듬기")
        st.warning(f"**🤖 AI 질문:** {st.session_state.get('socratic_question', '')}")
        final_draft = st.text_area("완성된 글 다듬기:", height=150, value=st.session_state.get("final_draft", ""))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.step = 3; st.rerun()
        with c2:
            if st.button("최종 완성 및 AI 채점 📈"):
                if final_draft.strip():
                    st.session_state.final_draft = final_draft
                    with st.spinner("AI가 배점 기준에 따라 채점 및 분석 중입니다..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.5-flash-lite', generation_config={'max_output_tokens': 300, 'temperature': 0.3})
                            eval_prompt = f"""
                            초등학생 글쓰기 성장 보고서 및 채점을 진행하세요.
                            [초안]: {st.session_state.get('draft_1', '')}
                            [수정본]: {st.session_state.get('final_draft', '')}
                            [채점 기준(100점 만점)]: {scoring_crit}

                            출력형식:
                            [성장한점]: (구체적 칭찬)
                            [종합격려]: (한 문장)
                            [최종점수]: (숫자만 작성. 예: 85)
                            """
                            eval_resp = model.generate_content(eval_prompt).text
                            
                            # 정규식으로 점수 추출
                            score_match = re.search(r'\[최종점수\]:\s*(\d+)', eval_resp)
                            st.session_state.ai_score = score_match.group(1) if score_match else "채점불가"
                            
                            st.session_state.growth_report = eval_resp.replace(f"[최종점수]: {st.session_state.ai_score}", "").strip()
                            st.session_state.step = 5
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")

    elif st.session_state.step == 5:
        st.subheader("📜 5단계: 나의 생각 최종본 및 제출")
        # Session State 안전 호출망(.get) 적용
        safe_final_draft = st.session_state.get('final_draft', '')
        safe_ai_score = st.session_state.get('ai_score', '진행 중')
        safe_growth_report = st.session_state.get('growth_report', '분석 중입니다.')
        
        st.success(f"**완성글:**\n{safe_final_draft}")
        st.info(f"**🌟 AI 분석 (AI 채점: {safe_ai_score}점):**\n{safe_growth_report}")
        
        st.markdown("### 📝 제출자 정보 입력")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            school = st.selectbox("학교", df_schools['school_name'].tolist())
        with sc2:
            grade = st.selectbox("학년", [str(i)+"학년" for i in range(1, 7)])
        with sc3:
            class_num = st.selectbox("반", [str(i)+"반" for i in range(1, 16)])
        with sc4:
            student_name = st.text_input("이름")

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("📤 최종 제출하기"):
                if student_name.strip():
                    new_row = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "school": school,
                        "grade": grade,
                        "class_num": class_num,
                        "student_name": student_name,
                        "topic": selected_topic,
                        "score": safe_ai_score,
                        "final_draft": safe_final_draft,
                        "growth_report": safe_growth_report
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
        with c2:
            if st.button("✨ 다른 논제 도전하기"):
                reset_student_session()
                st.rerun()

# ==============================================================================
# 2. [선생님] Agent C 루브릭 금고
# ==============================================================================
elif menu == "🧠 [선생님] Agent C 루브릭 금고":
    st.header("🧠 Agent C: 기준 학습용 루브릭 금고")
    tab1, tab2 = st.tabs(["📋 등록된 루브릭 목록", "➕ 신규 루브릭 등록"])
    df_rubrics = pd.read_csv(RUBRIC_FILE)

    with tab1:
        for _, row in df_rubrics.iterrows():
            with st.expander(f"📌 [{row['id']}] {row['title']}"):
                st.markdown(f"**🎯 방향성 기준:** {row['criteria']}")
                st.markdown(f"**💯 100점 배점 기준:** {row.get('scoring_criteria', '미설정')}")
                st.markdown(f"**📝 모범 답안:** {row['good_example']}")

    with tab2:
        new_title = st.text_input("논제/주제명")
        new_criteria = st.text_area("평가 기준 (AI 꼬리 질문용 방향성)")
        new_scoring = st.text_input("채점 배점표 (예: 논리성 40점, 창의성 30점, 맞춤법 30점)")
        new_example = st.text_area("모범 답안 (Few-Shot 예시)")

        if st.button("💾 루브릭 저장"):
            if new_title and new_criteria and new_scoring:
                new_data = {"id": len(df_rubrics) + 1, "title": new_title, "good_example": new_example, "criteria": new_criteria, "scoring_criteria": new_scoring}
                pd.concat([df_rubrics, pd.DataFrame([new_data])], ignore_index=True).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                st.success("저장 완료!")
                st.rerun()

# ==============================================================================
# 3. [선생님] 제출 현황 및 학교 관리
# ==============================================================================
elif menu == "📊 [선생님] 학생 제출 및 채점 현황":
    st.header("📊 제출 현황 및 설정")
    
    tab_dash, tab_school = st.tabs(["📈 채점 대시보드", "🏫 학교 목록 관리"])
    
    with tab_school:
        st.subheader("등록된 학교 목록")
        df_schools = pd.read_csv(SCHOOL_FILE)
        st.write(", ".join(df_schools['school_name'].tolist()))
        
        new_school = st.text_input("새로운 학교 이름 추가 (예: 순천남산초등학교)")
        if st.button("➕ 학교 추가"):
            if new_school.strip() and new_school not in df_schools['school_name'].values:
                pd.concat([df_schools, pd.DataFrame([{"school_name": new_school}])], ignore_index=True).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')
                st.success(f"'{new_school}' 추가 완료!")
                st.rerun()

    with tab_dash:
        if os.path.exists(SUBMISSION_FILE):
            df_submissions = pd.read_csv(SUBMISSION_FILE)
            
            st.markdown("### 🔍 정밀 검색 필터")
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                sch_filter = st.selectbox("학교", ["전체"] + list(df_submissions['school'].unique()))
            with f2:
                grd_filter = st.selectbox("학년", ["전체"] + list(df_submissions['grade'].unique()))
            with f3:
                cls_filter = st.selectbox("반", ["전체"] + list(df_submissions['class_num'].unique()))
            with f4:
                name_filter = st.text_input("이름 검색")

            filtered_df = df_submissions.copy()
            if sch_filter != "전체": filtered_df = filtered_df[filtered_df['school'] == sch_filter]
            if grd_filter != "전체": filtered_df = filtered_df[filtered_df['grade'] == grd_filter]
            if cls_filter != "전체": filtered_df = filtered_df[filtered_df['class_num'] == cls_filter]
            if name_filter: filtered_df = filtered_df[filtered_df['student_name'].str.astype(str).str.contains(name_filter, na=False)]

            st.write(f"검색 결과: **{len(filtered_df)}건**")
            st.dataframe(filtered_df, use_container_width=True)
            
            st.download_button(
                label="📥 필터링된 결과 CSV 다운로드",
                data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"student_reports_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("제출된 답안이 없습니다.")