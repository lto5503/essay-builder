import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import os
import re
import random
import streamlit.components.v1 as components

st.set_page_config(page_title="에듀씽크 AI 플랫폼", page_icon="🎓", layout="wide")

SUBMISSION_FILE = "submissions.csv"
RUBRIC_FILE = "rubrics.csv"
SCHOOL_FILE = "schools.csv"

# --- [API 키 설정] ---
api_connected = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_connected = True

# --- [동시 접속 안전 CSV 로드 및 저장 함수] ---
def load_csv_safe(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_csv(file_path)
        return df
    except pd.errors.EmptyDataError:
        return None
    except Exception:
        return None

def append_submission_safe(row_dict):
    df_new = pd.DataFrame([row_dict])
    file_exists = os.path.exists(SUBMISSION_FILE)
    try:
        df_new.to_csv(SUBMISSION_FILE, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        st.error(f"저장 중 동시성 지연 발생: {e}")
        return False

# --- [초기 파일 세팅] ---
if not os.path.exists(SCHOOL_FILE):
    pd.DataFrame({"school_name": ["좌야초등학교", "왕지초등학교", "신대초등학교"]}).to_csv(SCHOOL_FILE, index=False, encoding='utf-8-sig')

def init_master_rubrics():
    master_data = [
        {"grade": "1-2학년", "theme": "생활/안전", "title": "횡단보도를 안전하게 건너는 방법", "good_example": "초록불이 켜져도 바로 건너지 않습니다. 차가 멈췄는지 보고 손을 듭니다.", "criteria": "1) 구체적 행동 2) 안전의식", "scoring_criteria": "내용 정확성 50점, 표현력 50점"},
        {"grade": "3-4학년", "theme": "사회/환경", "title": "학교 급식을 남기지 말아야 하는 이유", "good_example": "음식물 쓰레기로 인한 환경오염을 줄이고 감사하는 마음을 갖습니다.", "criteria": "1) 환경보호 2) 감사", "scoring_criteria": "근거 타당성 50점, 논리성 50점"},
        {"grade": "5-6학년", "theme": "과학/기술", "title": "숙제할 때 인공지능(AI) 챗봇을 사용해도 될까?", "good_example": "AI 사용을 허용하되, 베끼지 않고 힌트만 얻는 규칙을 정해야 합니다.", "criteria": "1) 장단점 파악 2) 올바른 사용 규칙", "scoring_criteria": "주장 30점, 근거 40점, 대안 30점"},
        {"grade": "5-6학년", "theme": "사회/토론", "title": "동물원을 점차 없애야 할까?", "good_example": "동물원을 없애고 야생 보호구역이나 VR 동물원으로 대체해야 합니다.", "criteria": "1) 동물복지 2) 대안 제시", "scoring_criteria": "논리성 40점, 대안 30점, 표현력 30점"}
    ]
    pd.DataFrame(master_data).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

if not os.path.exists(RUBRIC_FILE):
    init_master_rubrics()
else:
    df_r = load_csv_safe(RUBRIC_FILE)
    if df_r is not None and not df_r.empty:
        ch = False
        if 'grade' not in df_r.columns: df_r.insert(0, 'grade', '5-6학년'); ch = True
        if 'theme' not in df_r.columns: df_r.insert(1, 'theme', '자유주제'); ch = True
        if ch: df_r.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')

df_s = load_csv_safe(SUBMISSION_FILE)
if df_s is not None and not df_s.empty:
    ch = False
    for col in ['school', 'grade', 'class_num', 'score', 'teacher_score']:
        if col not in df_s.columns: df_s[col] = "-"; ch = True
    if ch: df_s.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')

def reset_student_session():
    st.session_state.step = 1
    for k in ['claim', 'reason', 'counter', 'draft_1', 'socratic_question', 'final_draft', 'growth_report', 'ai_score']:
        if k in st.session_state: del st.session_state[k]

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("🎓 에듀씽크 센터")
    menu = st.radio(
        "메뉴를 선택하세요",
        ["📝 [학생] 생각 징검다리 글쓰기", "🏆 [학급] 생각 나눔 & 오늘의 작가", "🧠 [선생님] Agent C 루브릭 관리", "📊 [선생님] 제출 현황 대시보드"]
    )
    st.markdown("---")
    st.subheader("🔒 교사/관리자 모드")
    admin_pw = st.text_input("관리자 비밀번호", type="password", placeholder="1234")
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
    
    if df_rubrics is not None and not df_rubrics.empty:
        st.markdown("### 🔍 글쓰기 주제 선택")
        f1, f2, f3 = st.columns(3)
        with f1: sel_grade = st.selectbox("1️⃣ 학년군 선택", df_rubrics['grade'].unique())
        filtered_themes = df_rubrics[df_rubrics['grade'] == sel_grade]['theme'].unique()
        with f2: sel_theme = st.selectbox("2️⃣ 교과/분야 선택", filtered_themes)
        filtered_topics = df_rubrics[(df_rubrics['grade'] == sel_grade) & (df_rubrics['theme'] == sel_theme)]['title'].tolist()
        with f3: selected_topic = st.selectbox("3️⃣ 세부 논제 선택", filtered_topics, key="sel_topic")
    else:
        st.info("등록된 루브릭이 없습니다."); st.stop()

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
                    if append_submission_safe(new_row):
                        st.success("🎉 제출 완료!"); st.balloons()
        with c2:
            if st.button("✨ 다른 논제 도전하기"): reset_student_session(); st.rerun()

# ==============================================================================
# 2. [학급] 생각 나눔 & 인터랙티브 사다리 게임
# ==============================================================================
elif menu == "🏆 [학급] 생각 나눔 & 오늘의 작가":
    st.header("🏆 우리 반 생각 나눔터 & 인터랙티브 사다리 게임")
    st.caption("학생들의 글을 함께 발표하고, AI가 뽑은 오늘의 작가들과 실시간 사다리 타기를 진행해보세요!")
    
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
            if "selected_sub_idx" not in st.session_state: st.session_state.selected_sub_idx = None
            for idx, row in f_df.iterrows():
                time_str = str(row['timestamp'])[11:16] if pd.notnull(row['timestamp']) else ""
                if st.button(f"🧑‍🎓 {row['student_name']} ({time_str})", key=f"sbtn_{idx}", use_container_width=True):
                    st.session_state.selected_sub_idx = idx

        with col_view:
            st.subheader("📖 생각 공유 스크린")
            if st.session_state.selected_sub_idx is not None and st.session_state.selected_sub_idx in df_submissions.index:
                sel_row = df_submissions.loc[st.session_state.selected_sub_idx]
                
                if is_admin:
                    # 관리자 모드: 학생 명단 및 글 직접 수정 및 삭제
                    st.markdown(f"#### ✏️ [교사 모드] {sel_row['student_name']} 학생 글 수정 및 관리")
                    with st.form(key=f"edit_sub_form_{st.session_state.selected_sub_idx}"):
                        edit_name = st.text_input("학생 이름", value=sel_row['student_name'])
                        edit_draft = st.text_area("학생이 작성한 글", value=sel_row['final_draft'], height=160)
                        edit_growth = st.text_area("AI 분석/피드백", value=sel_row['growth_report'], height=80)
                        edit_score = st.text_input("AI 점수", value=sel_row['score'])
                        
                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            if st.form_submit_button("💾 수정 내용 저장", type="primary"):
                                df_submissions.at[st.session_state.selected_sub_idx, 'student_name'] = edit_name
                                df_submissions.at[st.session_state.selected_sub_idx, 'final_draft'] = edit_draft
                                df_submissions.at[st.session_state.selected_sub_idx, 'growth_report'] = edit_growth
                                df_submissions.at[st.session_state.selected_sub_idx, 'score'] = edit_score
                                df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                                st.success("수정 완료되었습니다!"); st.rerun()
                        with btn_c2:
                            if st.form_submit_button("🗑️ 이 글 삭제"):
                                df_submissions = df_submissions.drop(index=st.session_state.selected_sub_idx)
                                df_submissions.to_csv(SUBMISSION_FILE, index=False, encoding='utf-8-sig')
                                st.session_state.selected_sub_idx = None
                                st.success("삭제 완료되었습니다!"); st.rerun()
                else:
                    # 일반 학생/수업 모드
                    st.markdown(f"### {sel_row['student_name']} 학생의 생각")
                    st.caption(f"논제: {sel_row['topic']} / 제출시간: {sel_row['timestamp']}")
                    with st.container(border=True):
                        st.markdown(f"**{sel_row['final_draft']}**")
                    with st.expander("🤖 AI 분석 결과 보기"):
                        st.write(sel_row['growth_report'])
            else:
                st.info("좌측 학생 목록에서 이름을 클릭하면 작성한 글이 표시됩니다.")

        # --- [실제 인터랙티브 사다리 타기 게임] ---
        st.markdown("---")
        st.header("🎯 실시간 인터랙티브 사다리 타기 게임")
        st.caption("참가 인원과 이름을 지정하고, 이름을 클릭하면 선을 따라 실제로 내려가는 사다리 게임입니다!")

        # 우수 작가 추천 후보군 추출
        f_df['num_score'] = pd.to_numeric(f_df['score'], errors='coerce').fillna(0)
        top_candidates = f_df.sort_values(by="num_score", ascending=False)['student_name'].tolist()

        c_lad1, c_lad2 = st.columns([1, 2])
        with c_lad1:
            ladder_count = st.number_input("사다리 인원수 (2~8명)", min_value=2, max_value=8, value=min(4, max(2, len(f_df))))
        with c_lad2:
            default_names = ", ".join(top_candidates[:ladder_count]) if len(top_candidates) >= ladder_count else "학생A, 학생B, 학생C, 학생D"
            names_input = st.text_input("참가자 이름 (쉼표로 구분, 직접 수정 가능)", value=default_names)

        prizes_default = "1등 선물, 달콤한 간식, 비타민, 힘찬 박수, 초콜릿, 칭찬 스티커, 음료수, 미소"
        prizes_user = st.text_input("하단 당첨 선물 목록 (쉼표로 구분)", value=prizes_default)

        names_list = [n.strip() for n in names_input.split(",") if n.strip()][:ladder_count]
        prizes_list = [p.strip() for p in prizes_user.split(",") if p.strip()][:ladder_count]
        
        while len(names_list) < ladder_count: names_list.append(f"참가자{len(names_list)+1}")
        while len(prizes_list) < ladder_count: prizes_list.append("👏 박수")

        # 사다리 가로줄 난수 생성 및 세션 보존
        if "ladder_data" not in st.session_state or st.button("🎲 사다리 새로 섞기 / 리셋"):
            # 6개 층에 가로줄 랜덤 배치
            levels = 6
            bridges = []
            for lvl in range(levels):
                col = random.randint(0, ladder_count - 2)
                bridges.append({"level": lvl, "col": col})
            st.session_state.ladder_data = bridges

        # HTML5 Canvas 인터랙티브 사다리 게임 컴포넌트 생성
        ladder_json_bridges = str(st.session_state.ladder_data)
        names_js = str(names_list)
        prizes_js = str(prizes_list)

        html_ladder_code = f"""
        <div style="text-align: center; font-family: sans-serif; background: #ffffff; padding: 20px; border-radius: 12px; border: 2px solid #e0e6ed;">
            <p style="color: #2b6cb0; font-weight: bold; font-size: 16px; margin-bottom: 8px;">👇 상단의 학생 이름을 클릭하면 사다리를 타고 내려갑니다!</p>
            <canvas id="ladderCanvas" width="700" height="420" style="border: 1px solid #ddd; background: #fdfdfd; border-radius: 8px;"></canvas>
            <div id="resultText" style="margin-top: 12px; font-size: 18px; font-weight: bold; color: #d9534f; height: 30px;"></div>
        </div>

        <script>
            const canvas = document.getElementById("ladderCanvas");
            const ctx = canvas.getContext("2d");
            const numCols = {ladder_count};
            const names = {names_js};
            const prizes = {prizes_js};
            const bridges = {ladder_json_bridges};
            const levels = 6;

            const startY = 60;
            const endY = 360;
            const colWidth = (canvas.width - 120) / (numCols - 1);
            const levelHeight = (endY - startY) / levels;

            function getColX(col) {{
                return 60 + col * colWidth;
            }}
            function getLevelY(lvl) {{
                return startY + lvl * levelHeight + (levelHeight / 2);
            }}

            function drawBoard() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.lineWidth = 4;
                ctx.strokeStyle = "#4a5568";
                ctx.fillStyle = "#2d3748";
                ctx.font = "bold 15px sans-serif";
                ctx.textAlign = "center";

                // 세로줄 및 이름, 선물 그리기
                for (let i = 0; i < numCols; i++) {{
                    let x = getColX(i);
                    ctx.beginPath();
                    ctx.moveTo(x, startY);
                    ctx.lineTo(x, endY);
                    ctx.stroke();

                    // 이름 박스
                    ctx.fillStyle = "#ebf8ff";
                    ctx.fillRect(x - 45, 12, 90, 36);
                    ctx.strokeStyle = "#3182ce";
                    ctx.strokeRect(x - 45, 12, 90, 36);
                    ctx.fillStyle = "#2b6cb0";
                    ctx.fillText(names[i], x, 35);

                    // 선물 박스
                    ctx.fillStyle = "#feebc8";
                    ctx.fillRect(x - 45, endY + 8, 90, 36);
                    ctx.strokeStyle = "#dd6b20";
                    ctx.strokeRect(x - 45, endY + 8, 90, 36);
                    ctx.fillStyle = "#c05621";
                    ctx.fillText(prizes[i], x, endY + 31);
                    ctx.strokeStyle = "#4a5568";
                }}

                // 가로줄 그리기
                ctx.lineWidth = 4;
                ctx.strokeStyle = "#718096";
                for (let b of bridges) {{
                    let x1 = getColX(b.col);
                    let x2 = getColX(b.col + 1);
                    let y = getLevelY(b.level);
                    ctx.beginPath();
                    ctx.moveTo(x1, y);
                    ctx.lineTo(x2, y);
                    ctx.stroke();
                }}
            }}

            drawBoard();

            // 사다리 타기 애니메이션
            let isAnimating = false;
            canvas.addEventListener("click", function(e) {{
                if (isAnimating) return;
                const rect = canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                for (let i = 0; i < numCols; i++) {{
                    let x = getColX(i);
                    if (mouseX >= x - 45 && mouseX <= x + 45 && mouseY >= 12 && mouseY <= 48) {{
                        runLadder(i);
                        break;
                    }}
                }}
            }});

            function runLadder(startCol) {{
                isAnimating = true;
                drawBoard();
                let currentCol = startCol;
                let path = [{{x: getColX(currentCol), y: startY}}];

                for (let lvl = 0; lvl < levels; lvl++) {{
                    let yLvl = getLevelY(lvl);
                    path.push({{x: getColX(currentCol), y: yLvl}});
                    
                    // 가로줄 확인
                    for (let b of bridges) {{
                        if (b.level === lvl) {{
                            if (b.col === currentCol) {{
                                currentCol++;
                                path.push({{x: getColX(currentCol), y: yLvl}});
                                break;
                            }} else if (b.col === currentCol - 1) {{
                                currentCol--;
                                path.push({{x: getColX(currentCol), y: yLvl}});
                                break;
                            }}
                        }}
                    }}
                }}
                path.push({{x: getColX(currentCol), y: endY}});

                // 선 애니메이션 그리기
                let pIdx = 0;
                let curPos = {{x: path[0].x, y: path[0].y}};
                ctx.strokeStyle = "#e53e3e";
                ctx.lineWidth = 6;

                function animate() {{
                    if (pIdx >= path.length - 1) {{
                        document.getElementById("resultText").innerText = "🎉 [" + names[startCol] + "] ➡️ [" + prizes[currentCol] + "] 당첨 축하합니다!";
                        isAnimating = false;
                        return;
                    }}
                    let target = path[pIdx + 1];
                    let dx = target.x - curPos.x;
                    let dy = target.y - curPos.y;
                    let dist = Math.hypot(dx, dy);

                    if (dist < 6) {{
                        curPos.x = target.x;
                        curPos.y = target.y;
                        pIdx++;
                    }} else {{
                        curPos.x += (dx / dist) * 6;
                        curPos.y += (dy / dist) * 6;
                    }}

                    ctx.beginPath();
                    ctx.moveTo(path[pIdx].x, path[pIdx].y);
                    ctx.lineTo(curPos.x, curPos.y);
                    ctx.stroke();

                    requestAnimationFrame(animate);
                }}
                document.getElementById("resultText").innerText = names[startCol] + " 학생 사다리 타고 내려가는 중... 🏃";
                animate();
            }}
        </script>
        """
        components.html(html_ladder_code, height=500)

    else:
        st.info("현재 제출된 글이 없습니다.")

# ==============================================================================
# 3. [선생님] Agent C 루브릭 관리 (수정/삭제 유지)
# ==============================================================================
elif menu == "🧠 [선생님] Agent C 루브릭 관리":
    st.header("🧠 Agent C: 교과/학년별 루브릭 통합 관리")
    if not is_admin: st.warning("🔒 수정 및 삭제는 좌측 관리자 비밀번호를 입력해야 가능합니다.")
    df_rubrics = load_csv_safe(RUBRIC_FILE)
    
    tab1, tab2 = st.tabs(["📋 루브릭 목록 및 수정/삭제", "➕ 신규 루브릭 등록"])
    with tab1:
        if df_rubrics is not None and not df_rubrics.empty:
            for original_idx, row in df_rubrics.iterrows():
                with st.expander(f"[{row['grade']}] {row['theme']} - {row['title']}"):
                    if is_admin:
                        with st.form(key=f"rf_{original_idx}"):
                            eg = st.text_input("학년군", value=row['grade'])
                            eth = st.text_input("주제", value=row['theme'])
                            eti = st.text_input("논제", value=row['title'])
                            ec = st.text_area("기준", value=row['criteria'])
                            es = st.text_input("배점", value=row['scoring_criteria'])
                            eex = st.text_area("예시", value=row['good_example'])
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.form_submit_button("💾 수정 저장"):
                                    df_rubrics.at[original_idx, 'grade'] = eg; df_rubrics.at[original_idx, 'theme'] = eth
                                    df_rubrics.at[original_idx, 'title'] = eti; df_rubrics.at[original_idx, 'criteria'] = ec
                                    df_rubrics.at[original_idx, 'scoring_criteria'] = es; df_rubrics.at[original_idx, 'good_example'] = eex
                                    df_rubrics.to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig'); st.success("저장 완료"); st.rerun()
                            with c2:
                                if st.form_submit_button("🗑️ 삭제", type="primary"):
                                    df_rubrics = df_rubrics.drop(index=original_idx).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
                                    st.success("삭제 완료"); st.rerun()
                    else:
                        st.markdown(f"**기준:** {row['criteria']}\n\n**배점:** {row['scoring_criteria']}")
    with tab2:
        ng = st.selectbox("학년군", ["1-2학년", "3-4학년", "5-6학년", "공통"])
        nth = st.selectbox("교과", ["사회/환경", "과학/기술", "국어/독서", "도덕/인성", "자유"])
        nti = st.text_input("논제")
        ncr = st.text_area("평가 기준")
        nsc = st.text_input("배점표")
        nex = st.text_area("모범 답안")
        if st.button("💾 루브릭 추가", type="primary") and nti:
            new_r = {"grade": ng, "theme": nth, "title": nti, "good_example": nex, "criteria": ncr, "scoring_criteria": nsc}
            pd.concat([df_rubrics if df_rubrics is not None else pd.DataFrame(), pd.DataFrame([new_r])], ignore_index=True).to_csv(RUBRIC_FILE, index=False, encoding='utf-8-sig')
            st.success("등록 완료"); st.rerun()

# ==============================================================================
# 4. [선생님] 제출 현황 대시보드
# ==============================================================================
elif menu == "📊 [선생님] 제출 현황 대시보드":
    st.header("📊 제출 현황 및 채점 대시보드")
    if not is_admin: st.warning("🔒 엑셀 다운로드 및 수정/삭제는 좌측 관리자 비밀번호를 입력해야 가능합니다.")
    df_submissions = load_csv_safe(SUBMISSION_FILE)
    if df_submissions is not None and not df_submissions.empty:
        filtered_df = df_submissions.copy()
        filtered_df.insert(0, '선택', False)
        dc = ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'score', 'teacher_score', 'final_draft', 'growth_report'] if is_admin else ['선택', 'timestamp', 'school', 'grade', 'class_num', 'student_name', 'topic', 'final_draft', 'growth_report']
        cc = {"선택": st.column_config.CheckboxColumn("선택"), "score": st.column_config.TextColumn("🤖 AI 점수", disabled=True), "teacher_score": st.column_config.TextColumn("👩‍🏫 교사 점수 (더블클릭)")} if is_admin else {"선택": st.column_config.CheckboxColumn("선택")}
        
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