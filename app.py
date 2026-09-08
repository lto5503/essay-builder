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

# --- [초기 파일 세팅 및 스키마 자동 업데이트] ---
if not os.path.exists(SCHOOL_FILE):
    pd.DataFrame({"school_name": ["좌야초등학교", "왕지초등학교", "신대초등학교"]}).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')

if not os.path.exists(RUBRIC_FILE):
    df_init_rubric = pd.DataFrame([
        {
            "id": 1,
            "title": "초등 5-6학년: 교내 스마트폰 자율 사용 찬반",
            "good_example": "스마트폰 자율 사용을 허용해야 한다...",
            "criteria": "1) 주장 명확성 2) 구체적 근거 제시 3) 반론 수용",
            "scoring_criteria": "주장 30점, 근거 40점, 맞춤법 30점"
        }
    ])
    df_init_rubric.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

if os.path.exists(SUBMISSION_FILE):
    df_s = pd.read_csv(SUBMISSION_FILE)
    changed = False
    for col in ['school', 'grade', 'class_num', 'score', 'teacher_score']:
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

def show_previous_steps(current_step):
    st.markdown("<br>", unsafe_allow_html=True)
    if current_step > 1:
        with st.expander("📌 [1단계] 나의 주장 (클릭하여 수정)", expanded=False):
            st.session_state.claim = st.text_input("1단계 수정:", value=st.session_state.get("claim", ""))
    if current_step > 2:
        with st.expander("💡 [2단계] 나의 근거 (클릭하여 수정)", expanded=False):
            st.session_state.reason = st.text_area("2단계 수정:", value=st.session_state.get("reason", ""), height=80)
    if current_step > 3:
        with st.expander("🛡️ [3단계] 반론 극복 (클릭하여 수정)", expanded=False):
            st.session_state.counter = st.text_area("3단계 수정:", value=st.session_state.get("counter", ""), height=80)
    st.markdown("<br>", unsafe_allow_html=True)

# --- [사이드바 메뉴 및 관리자 로그인] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "사용할 프로그램을 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🧠 [선생님] Agent C 루브릭 금고", "📊 [선생님] 학생 제출 및 채점 현황"]
    )
    st.markdown("---")
    
    st.subheader("🔒 교사/관리자 모드")
    admin_pw = st.text_input("비밀번호 입력", type="password", placeholder="1234")
    is_admin = (admin_pw == "1234")
    if is_admin:
        st.success("👑 관리자 권한 활성화됨")
    
    st.markdown("---")
    if api_connected:
        st.success("🟢 AI 엔진 가동 중")
    else:
        st.error("🔴 AI 엔진 설정 필요")

# ==============================================================================
# 1. [학생] 생각 징검다리 글쓰기 (기존 동일하므로 UI만 축약 반영)
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
    scoring_crit = current_rubric.get("scoring_criteria", "논리성, 표현력 평가")

    if "step" not in st.session_state: st.session_state.step = 1
    steps = ["1. 주장", "2. 근거", "3. 반론 극복", "4. AI 질문", "5. 다듬기 및 제출"]
    st.progress(st.session_state.step / 5)

    if st.session_state.step == 1:
        st.subheader("🎯 1단계: 나의 입장 밝히기")
        claim = st.text_input("어떻게 생각하나요?", value=st.session_state.get("claim", ""))
        if st.button("다음 단계 ➡️"):
            if claim.strip(): st.session_state.claim = claim; st.session_state.step = 2; st.rerun()

    elif st.session_state.step == 2:
        st.subheader("💡 2단계: 주장을 뒷받침할 근거 대기")
        show_previous_steps(2)
        reason = st.text_area("왜 그렇게 생각하나요?", value=st.session_state.get("reason", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"): st.session_state.step = 1; st.rerun()
        with c2:
            if st.button("다음 단계 ➡️"):
                if reason.strip(): st.session_state.reason = reason; st.session_state.step = 3; st.rerun()

    elif st.session_state.step == 3:
        st.subheader("🛡️ 3단계: 반대 의견 생각하고 극복하기")
        show_previous_steps(3)
        counter = st.text_area("반대 의견과 나의 생각은?", value=st.session_state.get("counter", ""), height=100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"): st.session_state.step = 2; st.rerun()
        with c2:
            if st.button("AI 코치에게 검단받기 ✨"):
                if counter.strip():
                    st.session_state.counter = counter
                    st.session_state.draft_1 = f"주장: {st.session_state.get('claim', '')}\n근거: {st.session_state.get('reason', '')}\n반론: {st.session_state.get('counter', '')}"
                    with st.spinner("논리 분석 중..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.5-flash-lite', generation_config={'max_output_tokens': 200, 'temperature': 0.7})
                            prompt = f"학생의 글 논리적 결손을 파악하고 꼬리 질문 1개를 작성하세요.\n[글]: {st.session_state.draft_1}"
                            st.session_state.socratic_question = model.generate_content(prompt).text
                            st.session_state.step = 4; st.rerun()
                        except Exception as e: st.error(f"오류: {e}")

    elif st.session_state.step == 4:
        st.subheader("🚀 4단계: 생각을 더 깊게 다듬기")
        show_previous_steps(4)
        st.warning(f"**🤖 AI 질문:** {st.session_state.get('socratic_question', '')}")
        final_draft = st.text_area("완성된 글 다듬기:", height=150, value=st.session_state.get("final_draft", ""))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 이전"): st.session_state.step = 3; st.rerun()
        with c2:
            if st.button("최종 완성 및 AI 채점 📈"):
                if final_draft.strip():
                    st.session_state.final_draft = final_draft
                    with st.spinner("AI가 배점 기준에 따라 채점 중입니다..."):
                        try:
                            model = genai.GenerativeModel('gemini-3.5-flash-lite', generation_config={'max_output_tokens': 300, 'temperature': 0.3})
                            eval_prompt = f"""초등학생 글쓰기 성장 보고서 및 채점.\n[초안]: {st.session_state.get('draft_1', '')}\n[수정본]: {st.session_state.get('final_draft', '')}\n[채점 기준(100점 만점)]: {scoring_crit}\n출력형식:\n[성장한점]: (구체적 칭찬)\n[종합격려]: (한 문장)\n[최종점수]: (숫자만)"""
                            eval_resp = model.generate_content(eval_prompt).text
                            score_match = re.search(r'\[최종점수\]:\s*(\d+)', eval_resp)
                            st.session_state.ai_score = score_match.group(1) if score_match else "-"
                            st.session_state.growth_report = eval_resp.replace(f"[최종점수]: {st.session_state.ai_score}", "").strip()
                            st.session_state.step = 5; st.rerun()
                        except Exception as e: st.error(f"오류: {e}")

    elif st.session_state.step == 5:
        st.subheader("📜 5단계: 나의 생각 최종본 및 제출")
        safe_final_draft = st.session_state.get('final_draft', '')
        safe_ai_score = st.session_state.get('ai_score', '-')
        safe_growth_report = st.session_state.get('growth_report', '')
        
        st.success(f"**완성글:**\n{safe_final_draft}")
        st.info(f"**🌟 AI 분석 (AI 채점: {safe_ai_score}점):**\n{safe_growth_report}")
        
        st.markdown("### 📝 제출자 정보 입력")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: school = st.selectbox("학교", df_schools['school_name'].tolist())
        with sc2: grade = st.selectbox("학년", [str(i)+"학년" for i in range(1, 7)])
        with sc3: class_num = st.selectbox("반", [str(i)+"반" for i in range(1, 16)])
        with sc4: student_name = st.text_input("이름")

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("📤 최종 제출하기"):
                if student_name.strip():
                    new_row = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "school": school, "grade": grade, "class_num": class_num, "student_name": student_name, "topic": selected_topic, "score": safe_ai_score, "teacher_score": "-", "final_draft": safe_final_draft, "growth_report": safe_growth_report}
                    pd.DataFrame([new_row]).to_csv(SUBMISSION_FILE, mode='a', header=not os.path.exists(SUBMISSION_FILE), index=False, encoding='utf-8-sig')
                    st.success("🎉 성공적으로 제출되었습니다!")
                    st.balloons()
        with c2:
            if st.button("✨ 다른 논제 도전하기"): reset_student_session(); st.rerun()

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
                st.markdown(f"**🎯 AI 방향성(꼬리질문) 기준:** {row['criteria']}")
                st.markdown(f"**💯 100점 채점 배점표:** {row.get('scoring_criteria', '미설정')}")
                st.markdown(f"**📝 모범 답안 예시:** {row['good_example']}")

    with tab2:
        new_title = st.text_input("논제/주제명")
        new_criteria = st.text_area("평가 기준 (AI 꼬리 질문용 방향성)")
        new_scoring = st.text_input("상세 채점 배점표 (예: 논리성 40점, 근거타당성 30점, 맞춤법 30점)")
        new_example = st.text_area("모범 답안 (Few-Shot 예시)")

        if st.button("💾 루브릭 저장"):
            if new_title and new_criteria and new_scoring:
                new_data = {"id": len(df_rubrics) + 1, "title": new_title, "good_example": new_example, "criteria": new_criteria, "scoring_criteria": new_scoring}
                pd.concat([df_rubrics, pd.DataFrame([new_data])], ignore_index=True).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                st.success("저장 완료!")
                st.rerun()

# ==============================================================================
# 3. [선생님] 학생 제출 및 채점 현황 대시보드
# ==============================================================================
elif menu == "📊 [선생님] 학생 제출 및 채점 현황":
    st.header("📊 제출 현황 및 채점 대시보드")
    
    if not is_admin:
        st.warning("🔒 엑셀 다운로드, 교사 채점, 삭제 기능은 좌측 사이드바에서 [관리자 비밀번호]를 입력해야 활성화됩니다.")
        
    tab_dash, tab_school = st.tabs(["📈 종합 채점 관리", "🏫 학교 목록 관리"])
    
    with tab_school:
        st.subheader("등록된 학교 목록")
        df_schools = pd.read_csv(SCHOOL_FILE)
        st.write(", ".join(df_schools['school_name'].tolist()))
        new_school = st.text_input("새로운 학교 이름 추가")
        if st.button("➕ 학교 추가"):
            if new_school.strip() and new_school not in df_schools['school_name'].values:
                pd.concat([df_schools, pd.DataFrame([{"school_name": new_school}])], ignore_index=True).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')
                st.success("학교 추가 완료!"); st.rerun()

    with tab_dash:
        if os.path.exists(SUBMISSION_FILE):
            df_submissions = pd.read_csv(SUBMISSION_FILE)
            
            # --- [스마트 필터링] ---
            f1, f2, f3, f4 = st.columns(4)
            with f1: sch_filter = st.selectbox("학교", ["전체"] + list(df_submissions['school'].unique()))
            with f2: grd_filter = st.selectbox("학년", ["전체"] + list(df_submissions['grade'].unique()))
            with f3: cls_filter = st.selectbox("반", ["전체"] + list(df_submissions['class_num'].unique()))
            with f4: name_filter = st.text_input("이름 검색")

            filtered_df = df_submissions.copy()
            if sch_filter != "전체": filtered_df = filtered_df[filtered_df['school'] == sch_filter]
            if grd_filter != "전체": filtered_df = filtered_df[filtered_df['grade'] == grd_filter]
            if cls_filter != "전체": filtered_df = filtered_df[filtered_df['class_num'] == cls_filter]
            if name_filter: filtered_df = filtered_df[filtered_df['student_name'].str.astype(str).str.contains(name_filter, na=False)]

            # UI용 체크박스 열 생성
            filtered_df.insert(0, '선택', False)
            
            st.markdown(f"**총 검색 결과: {len(filtered_df)}건**")

            # --- [관리자 여부에 따른 테이블 칼럼 구성] ---
            if is_admin:
                display_cols = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'score', 'teacher_score', 'final_draft', 'growth_report']
                column_config = {
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
                    "score": st.column_config.TextColumn("🤖 AI 점수", disabled=True),
                    "teacher_score": st.column_config.TextColumn("👩‍🏫 교사 점수 (더블클릭 수정)"),
                    "timestamp": st.column_config.TextColumn("제출일시", disabled=True),
                    "school": st.column_config.TextColumn("학교", disabled=True),
                    "grade": st.column_config.TextColumn("학년", disabled=True),
                    "class_num": st.column_config.TextColumn("반", disabled=True),
                    "student_name": st.column_config.TextColumn("이름", disabled=True),
                    "topic": st.column_config.TextColumn("논제", disabled=True),
                    "final_draft": st.column_config.TextColumn("최종본", disabled=True),
                    "growth_report": st.column_config.TextColumn("AI 분석", disabled=True)
                }
            else:
                display_cols = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'final_draft', 'growth_report']
                column_config = {
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
                    "timestamp": st.column_config.TextColumn("제출일시", disabled=True),
                    "school": st.column_config.TextColumn("학교", disabled=True),
                    "grade": st.column_config.TextColumn("학년", disabled=True),
                    "class_num": st.column_config.TextColumn("반", disabled=True),
                    "student_name": st.column_config.TextColumn("이름", disabled=True),
                    "topic": st.column_config.TextColumn("논제", disabled=True),
                    "final_draft": st.column_config.TextColumn("최종본", disabled=True),
                    "growth_report": st.column_config.TextColumn("AI 분석", disabled=True)
                }

            # 데이터 에디터 렌더링
            edited_df = st.data_editor(filtered_df[display_cols], column_config=column_config, hide_index=True, use_container_width=True)
            
            # 선택된 행 추출
            selected_rows = edited_df[edited_df['선택'] == True]

            # --- [관리자 전용 액션 버튼] ---
            if is_admin:
                act1, act2, act3 = st.columns(3)
                
                with act1:
                    if not selected_rows.empty:
                        export_df = selected_rows.drop(columns=['선택'])
                        st.download_button("📥 선택 항목 엑셀 다운로드", data=export_df.to_csv(index=False).encode('utf-8-sig'), file_name=f"selected_reports_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
                        
                with act2:
                    if st.button("💾 수정한 교사 점수 저장하기"):
                        for idx, row in edited_df.iterrows():
                            # 수정된 교사 점수를 원본 데이터 프레임에 반영
                            df_submissions.loc[df_submissions['timestamp'] == row['timestamp'], 'teacher_score'] = row['teacher_score']
                        df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                        st.success("교사 점수가 저장되었습니다.")
                        st.rerun()
                        
                with act3:
                    if not selected_rows.empty:
                        if st.button("🗑️ 선택 항목 완전 삭제", type="primary"):
                            timestamps_to_delete = selected_rows['timestamp'].tolist()
                            df_submissions = df_submissions[~df_submissions['timestamp'].isin(timestamps_to_delete)]
                            df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                            st.success("해당 데이터가 영구 삭제되었습니다.")
                            st.rerun()
        else:
            st.info("제출된 답안이 없습니다.")