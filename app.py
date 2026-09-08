import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os
import re
import random

st.set_page_config(page_title="에듀씽크 AI 플랫폼", page_icon="🎓", layout="wide")

SUBMISSION_FILE = "submissions.csv"
RUBRIC_FILE = "rubrics.csv"
SCHOOL_FILE = "schools.csv"

# --- [API 키 설정] ---
api_connected = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_connected = True

# --- [안전한 CSV 로드 함수] ---
def load_csv_safe(file_path):
    if not os.path.exists(file_path): return None
    try: return pd.read_csv(file_path)
    except pd.errors.EmptyDataError: return None

# --- [초기 세팅] ---
if not os.path.exists(SCHOOL_FILE):
    pd.DataFrame({"school_name": ["좌야초등학교", "왕지초등학교", "신대초등학교"]}).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')

if not os.path.exists(RUBRIC_FILE):
    df_init_rubric = pd.DataFrame([
        {"id": 1, "title": "초등 5-6학년: 교내 스마트폰 자율 사용 찬반", "good_example": "스마트폰을 허용해야 한다...", "criteria": "1) 주장 2) 근거 3) 반론", "scoring_criteria": "주장 30점, 근거 40점, 맞춤법 30점"}
    ])
    df_init_rubric.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

df_s = load_csv_safe(SUBMISSION_FILE)
if df_s is not None and not df_s.empty:
    changed = False
    for col in ['school', 'grade', 'class_num', 'score', 'teacher_score']:
        if col not in df_s.columns: df_s[col] = "-"; changed = True
    if changed: df_s.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
elif os.path.exists(SUBMISSION_FILE): os.remove(SUBMISSION_FILE)

def reset_student_session():
    st.session_state.step = 1
    for key in ['claim', 'reason', 'counter', 'draft_1', 'socratic_question', 'final_draft', 'growth_report', 'ai_score']:
        if key in st.session_state: del st.session_state[key]

def show_previous_steps(current_step):
    st.markdown("<br>", unsafe_allow_html=True)
    if current_step > 1:
        with st.expander("📌 [1단계] 나의 주장 (클릭하여 수정)", expanded=False): st.session_state.claim = st.text_input("1단계 수정:", value=st.session_state.get("claim", ""))
    if current_step > 2:
        with st.expander("💡 [2단계] 나의 근거 (클릭하여 수정)", expanded=False): st.session_state.reason = st.text_area("2단계 수정:", value=st.session_state.get("reason", ""), height=80)
    if current_step > 3:
        with st.expander("🛡️ [3단계] 반론 극복 (클릭하여 수정)", expanded=False): st.session_state.counter = st.text_area("3단계 수정:", value=st.session_state.get("counter", ""), height=80)
    st.markdown("<br>", unsafe_allow_html=True)

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "메뉴를 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🏆 [학급] 생각 나눔 & 오늘의 작가", "🧠 [선생님] Agent C 루브릭 금고", "📊 [선생님] 학생 제출 및 채점 현황"]
    )
    st.markdown("---")
    st.subheader("🔒 교사/관리자 모드")
    admin_pw = st.text_input("비밀번호 입력", type="password", placeholder="1234")
    is_admin = (admin_pw == "1234")
    if is_admin: st.success("👑 관리자 권한 활성화됨")
    
    st.markdown("---")
    if api_connected: st.success("🟢 AI 엔진 가동 중")
    else: st.error("🔴 AI 엔진 설정 필요")

# ==============================================================================
# 1. [학생] 생각 징검다리 글쓰기
# ==============================================================================
if menu == "📝 [학생] 생각 징검다리 글쓰기":
    st.header("📝 생각 징검다리: 서논술형 쓰기 훈련")
    df_rubrics = load_csv_safe(RUBRIC_FILE)
    df_schools = load_csv_safe(SCHOOL_FILE)
    
    c_top1, c_top2 = st.columns([4, 1])
    with c_top1: selected_topic = st.selectbox("📌 논제 선택:", df_rubrics["title"].tolist() if df_rubrics is not None else [], key="sel_topic")
    with c_top2:
        st.write(""); st.write("")
        if st.button("🔄 처음부터 쓰기"): reset_student_session(); st.rerun()

    if "current_topic" not in st.session_state: st.session_state.current_topic = selected_topic
    elif st.session_state.current_topic != selected_topic: st.session_state.current_topic = selected_topic; reset_student_session(); st.rerun()

    scoring_crit = "설정된 기준 없음"
    if df_rubrics is not None and not df_rubrics.empty:
        scoring_crit = df_rubrics[df_rubrics["title"] == selected_topic].iloc[0].get("scoring_criteria", "논리성 평가")

    if "step" not in st.session_state: st.session_state.step = 1
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
        st.subheader("🛡️ 3단계: 반대 의견 극복하기")
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
                    with st.spinner("분석 중..."):
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
                            eval_prompt = f"성장 보고서 및 채점.\n[초안]: {st.session_state.get('draft_1', '')}\n[수정본]: {st.session_state.get('final_draft', '')}\n[채점 기준(100점 만점)]: {scoring_crit}\n출력형식:\n[성장한점]: (내용)\n[종합격려]: (내용)\n[최종점수]: (숫자만)"
                            eval_resp = model.generate_content(eval_prompt).text
                            score_match = re.search(r'\[최종점수\]:\s*(\d+)', eval_resp)
                            st.session_state.ai_score = score_match.group(1) if score_match else "-"
                            st.session_state.growth_report = eval_resp.replace(f"[최종점수]: {st.session_state.ai_score}", "").strip()
                            st.session_state.step = 5; st.rerun()
                        except Exception as e: st.error(f"오류: {e}")

    elif st.session_state.step == 5:
        st.subheader("📜 5단계: 제출")
        st.success(f"**완성글:**\n{st.session_state.get('final_draft', '')}")
        st.info(f"**🌟 AI 분석 ({st.session_state.get('ai_score', '-')}점):**\n{st.session_state.get('growth_report', '')}")
        
        st.markdown("### 📝 제출자 정보")
        s1, s2, s3, s4 = st.columns(4)
        with s1: school = st.selectbox("학교", df_schools['school_name'].tolist() if df_schools is not None else ["등록학교없음"])
        with s2: grade = st.selectbox("학년", [f"{i}학년" for i in range(1, 7)])
        with s3: class_num = st.selectbox("반", [f"{i}반" for i in range(1, 16)])
        with s4: student_name = st.text_input("이름")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📤 최종 제출하기"):
                if student_name.strip():
                    new_row = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "school": school, "grade": grade, "class_num": class_num, "student_name": student_name, "topic": selected_topic, "score": st.session_state.get('ai_score', '-'), "teacher_score": "-", "final_draft": st.session_state.get('final_draft', ''), "growth_report": st.session_state.get('growth_report', '')}
                    pd.DataFrame([new_row]).to_csv(SUBMISSION_FILE, mode='a', header=not os.path.exists(SUBMISSION_FILE), index=False, encoding='utf-8-sig')
                    st.success("🎉 제출 완료!"); st.balloons()
        with c2:
            if st.button("✨ 다른 논제 도전하기"): reset_student_session(); st.rerun()

# ==============================================================================
# 2. [학급] 생각 나눔 & 오늘의 작가 (신규 추가된 종합 토론 관제 센터)
# ==============================================================================
elif menu == "🏆 [학급] 생각 나눔 & 오늘의 작가":
    st.header("🏆 우리 반 생각 나눔터 & 오늘의 작가")
    st.caption("학생들이 쓴 글을 다 함께 화면으로 보며 생각을 나누고, AI가 뽑은 오늘의 작가와 사다리 게임을 즐겨보세요!")
    
    df_submissions = load_csv_safe(SUBMISSION_FILE)
    if df_submissions is not None and not df_submissions.empty:
        st.markdown("### 🔍 학급 선택 및 정렬")
        f1, f2, f3, f4 = st.columns(4)
        with f1: sch_f = st.selectbox("학교", ["전체"] + list(df_submissions['school'].unique()))
        with f2: grd_f = st.selectbox("학년", ["전체"] + list(df_submissions['grade'].unique()))
        with f3: cls_f = st.selectbox("반", ["전체"] + list(df_submissions['class_num'].unique()))
        with f4: sort_f = st.selectbox("정렬 방식", ["이름순 (가나다)", "제출순 (최신순)", "제출순 (오래된순)"])

        f_df = df_submissions.copy()
        if sch_f != "전체": f_df = f_df[f_df['school'] == sch_f]
        if grd_f != "전체": f_df = f_df[f_df['grade'] == grd_f]
        if cls_f != "전체": f_df = f_df[f_df['class_num'] == cls_f]

        # 정렬 로직 적용
        if sort_f == "이름순 (가나다)": f_df = f_df.sort_values(by="student_name")
        elif sort_f == "제출순 (최신순)": f_df = f_df.sort_values(by="timestamp", ascending=False)
        elif sort_f == "제출순 (오래된순)": f_df = f_df.sort_values(by="timestamp", ascending=True)

        st.markdown("---")
        
        # 좌우 레이아웃 분할 (관제 센터 뷰)
        col_list, col_view = st.columns([1, 2])
        
        with col_list:
            st.subheader(f"👥 제출 학생 ({len(f_df)}명)")
            st.info("이름을 클릭하면 우측에 글이 표시됩니다.")
            
            if "selected_student_idx" not in st.session_state:
                st.session_state.selected_student_idx = None

            # 학생 버튼 리스트 렌더링
            for idx, row in f_df.iterrows():
                # 시간 포맷 예쁘게 (HH:MM)
                time_str = str(row['timestamp'])[11:16] if pd.notnull(row['timestamp']) else ""
                btn_label = f"🧑‍🎓 {row['student_name']} ({time_str})"
                
                if st.button(btn_label, key=f"btn_{idx}", use_container_width=True):
                    st.session_state.selected_student_idx = idx

        with col_view:
            st.subheader("📖 생각 공유 스크린")
            if st.session_state.selected_student_idx is not None and st.session_state.selected_student_idx in f_df.index:
                sel_row = f_df.loc[st.session_state.selected_student_idx]
                st.markdown(f"### {sel_row['student_name']} 학생의 생각")
                st.caption(f"논제: {sel_row['topic']} / 제출시간: {sel_row['timestamp']}")
                
                with st.container(border=True):
                    st.markdown(f"**{sel_row['final_draft']}**")
                
                with st.expander("🤖 AI 분석 결과 보기"):
                    if is_admin: st.write(f"**AI 점수:** {sel_row['score']}점")
                    st.write(sel_row['growth_report'])
            else:
                st.markdown("""
                <div style='padding: 50px; text-align: center; background-color: #f0f2f6; border-radius: 10px;'>
                    <h3 style='color: #666;'>좌측에서 학생 이름을 클릭하면<br>이곳에 작성한 글이 나타납니다. 👈</h3>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.header("🎉 오늘의 작가 & 행운의 사다리 타기")
        st.caption("AI 점수를 기준으로 우수 작성자를 뽑고, 행운의 선물을 추첨합니다!")
        
        c_p1, c_p2 = st.columns([1, 2])
        with c_p1:
            num_winners = st.number_input("몇 명의 작가를 뽑을까요?", min_value=1, max_value=len(f_df) if len(f_df)>0 else 1, value=3)
        with c_p2:
            prizes_input = st.text_input("🎁 선물 목록 (쉼표로 구분하여 입력, 예: 사탕, 초콜릿, 박수)", value="초코파이, 사탕, 마이구미")
            
        if st.button("🚀 오늘의 작가 발표 및 사다리 타기 시작!", type="primary"):
            # AI 점수 숫자로 변환 후 내림차순 정렬 (점수가 없으면 0점 처리)
            f_df['numeric_score'] = pd.to_numeric(f_df['score'], errors='coerce').fillna(0)
            top_df = f_df.sort_values(by="numeric_score", ascending=False).head(num_winners)
            
            st.balloons()
            st.subheader(f"🏆 오늘의 우수 작가 {len(top_df)}인 발표!")
            
            prize_list = [p.strip() for p in prizes_input.split(",") if p.strip()]
            # 선물 개수가 당첨자보다 적으면 꽝으로 채우고, 많으면 자름
            while len(prize_list) < len(top_df): prize_list.append("👏 힘찬 박수")
            prize_list = prize_list[:len(top_df)]
            
            random.shuffle(prize_list) # 사다리 섞기
            
            cols = st.columns(len(top_df))
            for i, (idx, row) in enumerate(top_df.iterrows()):
                with cols[i]:
                    st.markdown(f"### 🥇 {row['student_name']}")
                    st.success(f"**AI 점수:** {row['numeric_score']}점")
                    st.info(f"**🎁 행운의 당첨:** {prize_list[i]}")
    else:
        st.info("아직 제출된 글이 없습니다.")

# ==============================================================================
# 3. [선생님] Agent C 루브릭 금고 (이하 기존 코드 유지 축약)
# ==============================================================================
elif menu == "🧠 [선생님] Agent C 루브릭 금고":
    st.header("🧠 Agent C: 기준 학습용 루브릭 금고")
    tab1, tab2 = st.tabs(["📋 목록", "➕ 등록"])
    df_rubrics = load_csv_safe(RUBRIC_FILE)
    with tab1:
        if df_rubrics is not None:
            for _, row in df_rubrics.iterrows():
                with st.expander(f"📌 [{row['id']}] {row['title']}"):
                    st.write(f"기준: {row['criteria']}")
    with tab2:
        new_title = st.text_input("논제")
        new_criteria = st.text_area("평가 기준")
        new_scoring = st.text_input("배점표")
        new_example = st.text_area("모범 답안")
        if st.button("💾 저장") and new_title:
            pd.concat([df_rubrics if df_rubrics is not None else pd.DataFrame(), pd.DataFrame([{"id": len(df_rubrics)+1 if df_rubrics is not None else 1, "title": new_title, "good_example": new_example, "criteria": new_criteria, "scoring_criteria": new_scoring}])], ignore_index=True).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig'); st.success("저장 완료!"); st.rerun()

# ==============================================================================
# 4. [선생님] 학생 제출 및 채점 현황 대시보드 (기존 유지)
# ==============================================================================
elif menu == "📊 [선생님] 학생 제출 및 채점 현황":
    st.header("📊 제출 현황 및 채점 대시보드")
    if not is_admin: st.warning("🔒 엑셀 다운로드 및 수정은 좌측 관리자 비밀번호를 입력해야 가능합니다.")
    
    df_submissions = load_csv_safe(SUBMISSION_FILE)
    if df_submissions is not None and not df_submissions.empty:
        filtered_df = df_submissions.copy()
        filtered_df.insert(0, '선택', False)
        
        if is_admin:
            display_cols = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'score', 'teacher_score', 'final_draft', 'growth_report']
            col_cfg = {"선택": st.column_config.CheckboxColumn("선택"), "score": st.column_config.TextColumn("🤖 AI 점수", disabled=True), "teacher_score": st.column_config.TextColumn("👩‍🏫 교사 점수 (더블클릭)")}
        else:
            display_cols = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'final_draft', 'growth_report']
            col_cfg = {"선택": st.column_config.CheckboxColumn("선택")}
            
        edited_df = st.data_editor(filtered_df[display_cols], column_config=col_cfg, hide_index=True, use_container_width=True)
        selected_rows = edited_df[edited_df['선택'] == True]

        if is_admin:
            act1, act2, act3 = st.columns(3)
            with act1:
                if not selected_rows.empty:
                    st.download_button("📥 선택 항목 엑셀 다운로드", data=selected_rows.drop(columns=['선택']).to_csv(index=False).encode('utf-8-sig'), file_name=f"reports_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
            with act2:
                if st.button("💾 교사 점수 저장"):
                    for idx, row in edited_df.iterrows(): df_submissions.loc[df_submissions['timestamp'] == row['timestamp'], 'teacher_score'] = row['teacher_score']
                    df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig'); st.success("저장 완료"); st.rerun()
            with act3:
                if not selected_rows.empty:
                    if st.button("🗑️ 선택 항목 삭제", type="primary"):
                        df_submissions = df_submissions[~df_submissions['timestamp'].isin(selected_rows['timestamp'].tolist())]
                        if df_submissions.empty: os.remove(SUBMISSION_FILE)
                        else: df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                        st.success("삭제 완료"); st.rerun()
    else: st.info("기록이 없습니다.")