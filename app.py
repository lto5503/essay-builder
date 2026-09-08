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

def load_csv_safe(file_path):
    if not os.path.exists(file_path): return None
    try: return pd.read_csv(file_path)
    except pd.errors.EmptyDataError: return None

# --- [초기 교육과정 마스터 루브릭 데이터베이스 구축] ---
def init_master_rubrics():
    master_data = [
        {"grade": "1-2학년", "theme": "생활/안전", "title": "횡단보도를 안전하게 건너는 방법", "good_example": "초록불이 켜져도 바로 건너지 않습니다. 왼쪽과 오른쪽을 살펴보고 차가 멈췄는지 확인한 뒤 손을 들고 건넙니다.", "criteria": "1) 구체적인 행동 2) 안전의 중요성", "scoring_criteria": "내용의 정확성 50점, 표현력 50점"},
        {"grade": "1-2학년", "theme": "도덕/인성", "title": "친구와 장난감을 사이좋게 나누어 써야 하는 이유", "good_example": "장난감을 혼자만 쓰면 친구가 속상해합니다. 함께 나누어 놀면 더 재미있는 놀이를 할 수 있고 사이도 좋아집니다.", "criteria": "1) 양보의 필요성 2) 긍정적 결과", "scoring_criteria": "이해심 50점, 문장 완성도 50점"},
        {"grade": "3-4학년", "theme": "사회/환경", "title": "학교 급식을 남기지 말아야 하는 이유", "good_example": "급식을 남기면 버려지는 음식물 쓰레기가 환경을 오염시킵니다. 또한 요리해주신 분들의 정성을 생각해서라도 먹을 만큼만 받아 다 먹어야 합니다.", "criteria": "1) 환경 문제 인식 2) 감사하는 마음", "scoring_criteria": "근거의 타당성 50점, 문제해결 의지 50점"},
        {"grade": "3-4학년", "theme": "국어/독서", "title": "선의의 거짓말(착한 거짓말)은 해도 될까?", "good_example": "친구의 마음을 다치지 않게 하려는 착한 거짓말은 가끔 필요합니다. 하지만 거짓말이 반복되면 믿음이 깨질 수 있으니 조심해야 합니다.", "criteria": "1) 상황에 따른 판단 2) 부작용에 대한 이해", "scoring_criteria": "주장의 명확성 40점, 근거 40점, 논리성 20점"},
        {"grade": "5-6학년", "theme": "과학/기술", "title": "숙제할 때 인공지능(AI) 챗봇을 사용해도 될까?", "good_example": "AI 챗봇 사용을 허용해야 합니다. 모르는 것을 빠르게 배울 수 있기 때문입니다. 단, 그대로 베끼지 않고 힌트만 얻는 규칙을 정해야 합니다.", "criteria": "1) 기술의 장점 2) 부작용 3) 올바른 사용 규칙", "scoring_criteria": "주장 30점, 근거 40점, 대안제시 30점"},
        {"grade": "5-6학년", "theme": "사회/토론", "title": "동물원을 점차 없애야 할까?", "good_example": "동물원을 없애야 합니다. 좁은 공간에서 동물들이 스트레스를 받기 때문입니다. 생태 보호 구역이나 가상현실(VR) 동물원으로 대체해야 합니다.", "criteria": "1) 동물 복지 2) 대안 제시", "scoring_criteria": "논리성 40점, 창의적 대안 30점, 표현력 30점"},
        {"grade": "5-6학년", "theme": "도덕/윤리", "title": "초등학생의 교내 스마트폰 사용 찬반", "good_example": "스마트폰을 허용해야 합니다. 긴급 연락과 학습 검색에 유용합니다. 게임이나 딴짓을 막기 위해 수업 중엔 끄는 규칙을 지키면 됩니다.", "criteria": "1) 명확한 찬반 2) 실용적 근거 3) 교내 규칙 제시", "scoring_criteria": "주장 30점, 근거 40점, 규칙제시 30점"}
    ]
    pd.DataFrame(master_data).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

if not os.path.exists(RUBRIC_FILE):
    init_master_rubrics()
else:
    df_r = load_csv_safe(RUBRIC_FILE)
    if df_r is not None and not df_r.empty:
        changed = False
        if 'grade' not in df_r.columns: df_r.insert(0, 'grade', '5-6학년'); changed = True
        if 'theme' not in df_r.columns: df_r.insert(1, 'theme', '자유주제'); changed = True
        if 'id' in df_r.columns: df_r = df_r.drop(columns=['id']); changed = True # ID 자동 관리를 위해 제거
        if changed: df_r.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

# 초기화 스키마 점검
if not os.path.exists(SCHOOL_FILE):
    pd.DataFrame({"school_name": ["좌야초등학교", "왕지초등학교", "신대초등학교"]}).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')

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

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "메뉴를 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🏆 [학급] 생각 나눔 & 오늘의 작가", "🧠 [선생님] Agent C 루브릭 관리", "📊 [선생님] 제출 현황 대시보드"]
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
# 1. [학생] 생각 징검다리 글쓰기 (학년/주제 필터 적용)
# ==============================================================================
if menu == "📝 [학생] 생각 징검다리 글쓰기":
    st.header("📝 생각 징검다리: 서논술형 쓰기 훈련")
    df_rubrics = load_csv_safe(RUBRIC_FILE)
    df_schools = load_csv_safe(SCHOOL_FILE)
    
    if df_rubrics is not None and not df_rubrics.empty:
        st.markdown("### 🔍 나의 글쓰기 주제 찾기")
        f1, f2, f3 = st.columns(3)
        with f1: sel_grade = st.selectbox("1️⃣ 학년군 선택", df_rubrics['grade'].unique())
        filtered_themes = df_rubrics[df_rubrics['grade'] == sel_grade]['theme'].unique()
        with f2: sel_theme = st.selectbox("2️⃣ 교과/분야 선택", filtered_themes)
        filtered_topics = df_rubrics[(df_rubrics['grade'] == sel_grade) & (df_rubrics['theme'] == sel_theme)]['title'].tolist()
        with f3: selected_topic = st.selectbox("3️⃣ 세부 논제 선택", filtered_topics, key="sel_topic")
    else:
        st.error("등록된 루브릭이 없습니다. 선생님 메뉴에서 등록해주세요.")
        st.stop()

    c_top1, c_top2 = st.columns([4, 1])
    with c_top2:
        if st.button("🔄 글쓰기 초기화"): reset_student_session(); st.rerun()

    if "current_topic" not in st.session_state: st.session_state.current_topic = selected_topic
    elif st.session_state.current_topic != selected_topic: st.session_state.current_topic = selected_topic; reset_student_session(); st.rerun()

    current_rubric_row = df_rubrics[df_rubrics["title"] == selected_topic].iloc[0]
    scoring_crit = current_rubric_row.get("scoring_criteria", "논리성 평가")

    if "step" not in st.session_state: st.session_state.step = 1
    st.progress(st.session_state.step / 5)

    if st.session_state.step == 1:
        st.subheader("🎯 1단계: 나의 입장 밝히기")
        claim = st.text_input("어떻게 생각하나요?", value=st.session_state.get("claim", ""))
        if st.button("다음 단계 ➡️"):
            if claim.strip(): st.session_state.claim = claim; st.session_state.step = 2; st.rerun()

    elif st.session_state.step == 2:
        st.subheader("💡 2단계: 주장을 뒷받침할 근거 대기")
        reason = st.text_area("왜 그렇게 생각하나요?", value=st.session_state.get("reason", ""), height=100)
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("⬅️ 이전"): st.session_state.step = 1; st.rerun()
        with c2: 
            if st.button("다음 단계 ➡️"):
                if reason.strip(): st.session_state.reason = reason; st.session_state.step = 3; st.rerun()

    elif st.session_state.step == 3:
        st.subheader("🛡️ 3단계: 반대 의견 극복하기")
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
# 2. [학급] 생각 나눔 & 오늘의 작가 (이전 코드 유지)
# ==============================================================================
elif menu == "🏆 [학급] 생각 나눔 & 오늘의 작가":
    st.header("🏆 우리 반 생각 나눔터 & 오늘의 작가")
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
        if sort_f == "이름순 (가나다)": f_df = f_df.sort_values(by="student_name")
        elif sort_f == "제출순 (최신순)": f_df = f_df.sort_values(by="timestamp", ascending=False)
        elif sort_f == "제출순 (오래된순)": f_df = f_df.sort_values(by="timestamp", ascending=True)

        st.markdown("---")
        col_list, col_view = st.columns([1, 2])
        with col_list:
            st.subheader(f"👥 제출 학생 ({len(f_df)}명)")
            if "selected_student_idx" not in st.session_state: st.session_state.selected_student_idx = None
            for idx, row in f_df.iterrows():
                time_str = str(row['timestamp'])[11:16] if pd.notnull(row['timestamp']) else ""
                if st.button(f"🧑‍🎓 {row['student_name']} ({time_str})", key=f"btn_{idx}", use_container_width=True): st.session_state.selected_student_idx = idx
        with col_view:
            st.subheader("📖 생각 공유 스크린")
            if st.session_state.selected_student_idx is not None and st.session_state.selected_student_idx in f_df.index:
                sel_row = f_df.loc[st.session_state.selected_student_idx]
                st.markdown(f"### {sel_row['student_name']} 학생의 생각")
                with st.container(border=True): st.markdown(f"**{sel_row['final_draft']}**")
                with st.expander("🤖 AI 분석 결과 보기"):
                    if is_admin: st.write(f"**AI 점수:** {sel_row['score']}점")
                    st.write(sel_row['growth_report'])
            else:
                st.info("좌측에서 학생 이름을 클릭하면 이곳에 작성한 글이 나타납니다.")
        st.markdown("---")
        st.header("🎉 오늘의 작가 & 행운의 사다리 타기")
        c_p1, c_p2 = st.columns([1, 2])
        with c_p1: num_winners = st.number_input("몇 명을 뽑을까요?", min_value=1, max_value=len(f_df) if len(f_df)>0 else 1, value=min(3, max(1, len(f_df))))
        with c_p2: prizes_input = st.text_input("🎁 선물 목록", value="초코파이, 사탕, 마이구미")
        if st.button("🚀 오늘의 작가 발표 및 사다리 타기 시작!", type="primary"):
            f_df['numeric_score'] = pd.to_numeric(f_df['score'], errors='coerce').fillna(0)
            top_df = f_df.sort_values(by="numeric_score", ascending=False).head(num_winners)
            st.balloons(); st.subheader(f"🏆 우수 작가 {len(top_df)}인 발표!")
            prize_list = [p.strip() for p in prizes_input.split(",") if p.strip()]
            while len(prize_list) < len(top_df): prize_list.append("👏 힘찬 박수")
            prize_list = prize_list[:len(top_df)]
            random.shuffle(prize_list)
            cols = st.columns(len(top_df))
            for i, (idx, row) in enumerate(top_df.iterrows()):
                with cols[i]:
                    st.markdown(f"### 🥇 {row['student_name']}")
                    st.success(f"AI 점수: {row['numeric_score']}점")
                    st.info(f"🎁 선물: {prize_list[i]}")
    else: st.info("제출된 글이 없습니다.")

# ==============================================================================
# 3. [선생님] Agent C 루브릭 관리 (전면 개편: 필터링 및 직접 수정/삭제)
# ==============================================================================
elif menu == "🧠 [선생님] Agent C 루브릭 관리":
    st.header("🧠 Agent C: 교과/학년별 루브릭 통합 관리")
    if not is_admin: st.warning("🔒 수정 및 삭제는 좌측 관리자 비밀번호를 입력해야 가능합니다.")
    
    df_rubrics = load_csv_safe(RUBRIC_FILE)
    
    tab1, tab2 = st.tabs(["📋 루브릭 목록 및 수정/삭제", "➕ 신규 루브릭 등록"])
    
    with tab1:
        if df_rubrics is not None and not df_rubrics.empty:
            f1, f2 = st.columns(2)
            with f1: filter_grade = st.selectbox("학년군 필터", ["전체"] + list(df_rubrics['grade'].unique()))
            with f2: 
                theme_options = ["전체"]
                if filter_grade != "전체": theme_options += list(df_rubrics[df_rubrics['grade'] == filter_grade]['theme'].unique())
                else: theme_options += list(df_rubrics['theme'].unique())
                filter_theme = st.selectbox("주제/교과 필터", theme_options)
            
            view_df = df_rubrics.copy()
            if filter_grade != "전체": view_df = view_df[view_df['grade'] == filter_grade]
            if filter_theme != "전체": view_df = view_df[view_df['theme'] == filter_theme]
            
            st.markdown(f"총 **{len(view_df)}건**의 루브릭이 검색되었습니다.")
            
            for original_idx, row in view_df.iterrows():
                with st.expander(f"[{row['grade']}] {row['theme']} - {row['title']}"):
                    if is_admin:
                        # 관리자: 폼을 통한 직접 수정 및 삭제
                        with st.form(key=f"form_{original_idx}"):
                            edit_grade = st.text_input("학년군", value=row['grade'], key=f"eg_{original_idx}")
                            edit_theme = st.text_input("교과/주제", value=row['theme'], key=f"eth_{original_idx}")
                            edit_title = st.text_input("논제(제목)", value=row['title'], key=f"eti_{original_idx}")
                            edit_criteria = st.text_area("AI 평가 방향성", value=row['criteria'], key=f"ec_{original_idx}")
                            edit_score = st.text_input("배점 기준", value=row['scoring_criteria'], key=f"es_{original_idx}")
                            edit_ex = st.text_area("모범 답안", value=row['good_example'], key=f"eex_{original_idx}")
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.form_submit_button("💾 수정 내용 저장"):
                                    df_rubrics.at[original_idx, 'grade'] = edit_grade
                                    df_rubrics.at[original_idx, 'theme'] = edit_theme
                                    df_rubrics.at[original_idx, 'title'] = edit_title
                                    df_rubrics.at[original_idx, 'criteria'] = edit_criteria
                                    df_rubrics.at[original_idx, 'scoring_criteria'] = edit_score
                                    df_rubrics.at[original_idx, 'good_example'] = edit_ex
                                    df_rubrics.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                                    st.success("수정 완료!"); st.rerun()
                            with c2:
                                if st.form_submit_button("🗑️ 이 루브릭 삭제", type="primary"):
                                    df_rubrics = df_rubrics.drop(index=original_idx)
                                    df_rubrics.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                                    st.success("삭제 완료!"); st.rerun()
                    else:
                        # 일반 사용자: 단순 조회
                        st.markdown(f"**🎯 평가 기준:** {row['criteria']}")
                        st.markdown(f"**💯 배점표:** {row['scoring_criteria']}")
                        st.markdown(f"**📝 모범 답안:** {row['good_example']}")
        else:
            st.info("등록된 루브릭이 없습니다.")

    with tab2:
        st.subheader("새로운 교육과정 루브릭 등록")
        new_g = st.selectbox("학년군 지정", ["1-2학년", "3-4학년", "5-6학년", "전학년 공통", "직접 입력"])
        if new_g == "직접 입력": new_g = st.text_input("학년군 직접 입력")
        
        new_th = st.selectbox("교과/주제 지정", ["국어/독서", "도덕/인성", "사회/환경", "과학/기술", "창의/자유", "직접 입력"])
        if new_th == "직접 입력": new_th = st.text_input("주제 직접 입력")

        new_ti = st.text_input("논제/주제명")
        new_cr = st.text_area("평가 기준 (AI 꼬리 질문용)")
        new_sc = st.text_input("상세 채점 배점표")
        new_ex = st.text_area("모범 답안 (Few-Shot)")

        if st.button("💾 신규 루브릭 추가", type="primary"):
            if new_ti and new_cr:
                new_row = {"grade": new_g, "theme": new_th, "title": new_ti, "good_example": new_ex, "criteria": new_cr, "scoring_criteria": new_sc}
                if df_rubrics is not None: pd.concat([df_rubrics, pd.DataFrame([new_row])], ignore_index=True).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                else: pd.DataFrame([new_row]).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                st.success(f"[{new_ti}] 등록 완료!"); st.rerun()
            else: st.error("논제와 평가 기준은 필수 입력입니다.")

# ==============================================================================
# 4. [선생님] 학생 제출 및 채점 현황 대시보드 (기존 유지 축약)
# ==============================================================================
elif menu == "📊 [선생님] 제출 현황 대시보드":
    st.header("📊 제출 현황 및 채점 대시보드")
    if not is_admin: st.warning("🔒 관리자 권한이 필요합니다.")
    df_submissions = load_csv_safe(SUBMISSION_FILE)
    if df_submissions is not None and not df_submissions.empty:
        filtered_df = df_submissions.copy()
        filtered_df.insert(0, '선택', False)
        if is_admin:
            dc = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'score', 'teacher_score', 'final_draft', 'growth_report']
            cc = {"선택": st.column_config.CheckboxColumn("선택"), "score": st.column_config.TextColumn("🤖 AI 점수", disabled=True), "teacher_score": st.column_config.TextColumn("👩‍🏫 교사 점수 (더블클릭)")}
        else:
            dc = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'final_draft', 'growth_report']
            cc = {"선택": st.column_config.CheckboxColumn("선택")}
        edited_df = st.data_editor(filtered_df[dc], column_config=cc, hide_index=True, use_container_width=True)
        sel_rows = edited_df[edited_df['선택'] == True]
        if is_admin:
            a1, a2, a3 = st.columns(3)
            with a1:
                if not sel_rows.empty: st.download_button("📥 엑셀 다운로드", data=sel_rows.drop(columns=['선택']).to_csv(index=False).encode('utf-8-sig'), file_name=f"reports.csv", mime="text/csv")
            with a2:
                if st.button("💾 교사 점수 저장"):
                    for i, r in edited_df.iterrows(): df_submissions.loc[df_submissions['timestamp'] == r['timestamp'], 'teacher_score'] = r['teacher_score']
                    df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig'); st.success("저장 완료"); st.rerun()
            with a3:
                if not sel_rows.empty and st.button("🗑️ 삭제", type="primary"):
                    df_submissions = df_submissions[~df_submissions['timestamp'].isin(sel_rows['timestamp'].tolist())]
                    if df_submissions.empty: os.remove(SUBMISSION_FILE)
                    else: df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                    st.success("삭제 완료"); st.rerun()
    else: st.info("기록이 없습니다.")
