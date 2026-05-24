import streamlit as st
import pandas as pd
import random
from supabase import create_client, Client

# --- 기본 설정 ---
st.set_page_config(page_title="주식시장 사이클 시뮬레이터", page_icon="📈", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()
INITIAL_ENDOWMENT = 2000000  # 초기 자금 200만 원

# --- 로그인 화면 ---
if "role" not in st.session_state:
    st.title("📈 주식시장 사이클 시뮬레이터")
    role = st.radio("접속 유형", ["학생", "교수"], horizontal=True)
    
    # 학생은 분반 선택 없이 '인하대'로 자동 접속 (교수만 선택 가능)
    if role == "교수":
        class_name = st.selectbox("분반 선택", ["인하대", "숙대1", "숙대2"])
    else:
        class_name = "인하대" 

    if role == "학생":
        name = st.text_input("이름을 입력하세요")
        if st.button("실험실 입장", type="primary"):
            if name:
                res = supabase.table("cycle_students").select("*").eq("name", name).eq("class_name", class_name).execute()
                if not res.data:
                    # Boom / Bust 50:50 균등 배정 로직
                    counts = supabase.table("cycle_students").select("group_type").eq("class_name", class_name).execute()
                    boom_count = sum(1 for row in counts.data if row['group_type'] == 'Boom')
                    bust_count = sum(1 for row in counts.data if row['group_type'] == 'Bust')
                    
                    if boom_count > bust_count:
                        assigned_group = "Bust"
                    elif bust_count > boom_count:
                        assigned_group = "Boom"
                    else:
                        assigned_group = random.choice(["Boom", "Bust"])
                        
                    supabase.table("cycle_students").insert({
                        "name": name, 
                        "class_name": class_name, 
                        "group_type": assigned_group
                    }).execute()
                st.session_state.role = "student"
                st.session_state.name = name
                st.session_state.class_name = class_name
                st.rerun()
            else:
                st.error("이름을 입력해주세요.")
    else:
        pw = st.text_input("비밀번호", type="password")
        if st.button("교수 통제소 입장", type="primary"):
            if pw == "3383":
                st.session_state.role = "professor"
                st.session_state.class_name = class_name
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 공통 데이터 로드 ---
my_class = st.session_state.class_name
status_res = supabase.table("cycle_status").select("*").eq("class_name", my_class).execute()
status_data = status_res.data[0]
phase = status_data['current_phase']
winning_result = status_data['winning_ball']

st.markdown(f"### 🏫 [{my_class} 분반] 행동재무학 실험실")
if st.button("로그아웃", key="logout"):
    st.session_state.clear()
    st.rerun()
st.write("---")

# ==========================================
# 👨‍🎓 학생 화면
# ==========================================
if st.session_state.role == "student":
    me = st.session_state.name
    
    if st.button("🔄 교수님 지시 후 화면 새로고침", type="primary", use_container_width=True):
        st.rerun()
    st.write("---")
    
    student_res = supabase.table("cycle_students").select("*").eq("name", me).eq("class_name", my_class).execute()
    student_data = student_res.data[0]
    my_group = student_data['group_type']
    
    if phase == "대기":
        st.info("다른 친구들이 입장할 때까지 잠시 대기해 주세요. 교수님이 안내하면 새로고침을 누르세요.")
        
    elif phase == "실험시작":
        # None 체크 적용 (Python 문법)
        if student_data['investment'] is not None and student_data['fear_level'] is not None:
            st.success("✅ 자산 배분 결정을 성공적으로 제출했습니다! 교수 화면의 실시간 통계 분석을 확인하세요.")
            st.stop()
            
        st.subheader("📊 현재 시장 트렌드 분석 리포트")
        if my_group == "Boom":
            st.markdown("#### 🚀 [시장 전반] 주식시장 지속적 호황 및 강세장 진입")
            st.line_chart(pd.DataFrame({"주가 (Price)": [100, 120, 115, 140, 165, 160, 185, 210, 235]}))
            st.write("📢 **시장 동향:** 최근 주식시장은 역사적인 최고치를 경신하며 강력한 상승 모멘텀을 유지하고 있습니다.")
        else:
            st.markdown("#### 🚨 [시장 전반] 주식시장 단기 폭락 및 금융위기 공포 확산")
            st.line_chart(pd.DataFrame({"주가 (Price)": [235, 210, 185, 190, 150, 120, 130, 95, 70]}))
            st.write("📢 **시장 동향:** 최근 주식시장은 가파른 폭락세를 보이며 패닉 셀링 징후가 포착되고 있습니다.")
            
        st.write("---")
        st.subheader("🧠 심리 및 투자 의사결정문")
        fear = st.slider("0: 공포 전혀 없음 ~ 6: 극심한 공포감", 0, 6, 3)
        st.write("---")
        st.write(f"**Q2. 당신에게 지금 확실한 자산 {INITIAL_ENDOWMENT:,} 원이 주어졌습니다. 이 중 얼마를 주식(위험 자산)에 투자하시겠습니까?**")
        
        # 투자 금액 천단위 쉼표가 적용된 selectbox(선택칸)
        invest_amount = st.selectbox(
            "투자할 금액을 선택하세요 (원)", 
            options=range(0, INITIAL_ENDOWMENT + 1, 100000), 
            index=10, 
            format_func=lambda x: f"{x:,}"
        )
        
        if st.button("💼 최종 의사결정 제출", type="primary"):
            supabase.table("cycle_students").update({
                "fear_level": fear,
                "investment": invest_amount
            }).eq("name", me).eq("class_name", my_class).execute()
            st.success("의사결정이 제출되었습니다!")
            st.rerun()

    elif phase == "종료":
        st.title("🏁 실험 결과 및 주사위 추첨")
        if student_data['investment'] is None:
            st.warning("제출하지 않은 상태에서 실험이 마감되었습니다.")
        else:
            keep_money = INITIAL_ENDOWMENT - student_data['investment']
            if winning_result == "노란공 (성공)":
                final_profit = keep_money + int(student_data['investment'] * 2.5)
                st.balloons()
                st.success(f"🎉 추첨 결과: **[노란공 - 투자 성공!]** 당신의 최종 자산은 **{final_profit:,} 원**입니다.")
            elif winning_result == "빨간공 (실패)":
                st.error(f"💥 추첨 결과: **[빨간공 - 투자 실패]** 당신의 최종 자산은 **{keep_money:,} 원**입니다.")
            else:
                st.info("교수님이 최종 주사위(공)를 추첨할 때까지 메인 화면을 주목해 주세요!")

# ==========================================
# 👨‍🏫 교수 통제 화면
# ==========================================
else:
    st.title("👨‍🏫 주식시장 사이클 시뮬레이터 통제소")
    if st.button("🔄 실시간 현황 새로고침", type="primary"):
        st.rerun()
    st.write("---")
    
    if phase == "대기":
        students_res = supabase.table("cycle_students").select("name").eq("class_name", my_class).execute()
        st.info(f"현재 강의실 입장 학생 수: {len(students_res.data)}명")
        if st.button("🚀 실험 시작"):
            supabase.table("cycle_status").update({"current_phase": "실험시작"}).eq("class_name", my_class).execute()
            st.rerun()
            
    elif phase == "실험시작":
        students_data = supabase.table("cycle_students").select("*").eq("class_name", my_class).execute()
        df = pd.DataFrame(students_data.data)
        if not df.empty and 'investment' in df.columns:
            submitted_df = df[df['investment'].notna()]
            st.metric("의사결정 완료 학생 수", f"{len(submitted_df)} 명")
            if st.button("🏁 실험 마감 및 통계 분석 결과 공개"):
                supabase.table("cycle_status").update({"current_phase": "종료"}).eq("class_name", my_class).execute()
                st.rerun()
            
    elif phase == "종료":
        st.header("📊 실험 결과 분석")
        students_data = supabase.table("cycle_students").select("*").eq("class_name", my_class).execute()
        df = pd.DataFrame(students_data.data)
        
        if not df.empty:
            # 1. 시각화
            fear_chart = df.groupby('group_type')['fear_level'].mean().reset_index()
            st.bar_chart(data=fear_chart, x='group_type', y='fear_level')
            
            # 2. 학생별 상세 결과 테이블 (계산 포함)
            def calc_final(row):
                if winning_result == "노란공 (성공)":
                    return (INITIAL_ENDOWMENT - row['investment']) + (row['investment'] * 2.5)
                elif winning_result == "빨간공 (실패)":
                    return (INITIAL_ENDOWMENT - row['investment'])
                return 0
            
            df['final_amount'] = df.apply(calc_final, axis=1)
            # 쉼표 포맷팅된 데이터프레임 표시
            df_display = df[['name', 'group_type', 'investment', 'final_amount']].copy()
            df_display['investment'] = df_display['investment'].apply(lambda x: f"{x:,} 원")
            df_display['final_amount'] = df_display['final_amount'].apply(lambda x: f"{x:,} 원")
            df_display.columns = ['이름', '시나리오', '투자 금액', '최종 금액']
            st.dataframe(df_display, use_container_width=True)
            
            # 3. 최종 확률 추첨 복불복 인터페이스 (복원됨)
            st.write("---")
            st.subheader("🎲 최종 시장 확률 추첨 (50% 확률 복불복)")
            if winning_result == "미정":
                col_draw1, col_draw2 = st.columns(2)
                if col_draw1.button("🟡 노란공 뽑기 (투자 성공!)", use_container_width=True):
                    supabase.table("cycle_status").update({"winning_ball": "노란공 (성공)"}).eq("class_name", my_class).execute()
                    st.rerun()
                if col_draw2.button("🔴 빨간공 뽑기 (투자 실패...)", use_container_width=True):
                    supabase.table("cycle_status").update({"winning_ball": "빨간공 (실패)"}).eq("class_name", my_class).execute()
                    st.rerun()
            else:
                st.success(f"🎯 최종 추첨 결과: **{winning_result}** 상태입니다.")
        
        st.write("---")
        if st.button("⚠️ 데이터 초기화"):
            supabase.table("cycle_status").update({"current_phase": "대기", "winning_ball": "미정"}).eq("class_name", my_class).execute()
            supabase.table("cycle_students").delete().eq("class_name", my_class).execute()
            st.rerun()
