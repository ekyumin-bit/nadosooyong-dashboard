import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# 1. 페이지 설정 및 한글 폰트 CSS 적용
st.set_page_config(page_title="🌱 극지식물 최적 EC 농도 연구", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 설정 정보
SCHOOL_INFO = {
    "송도고": {"ec_target": 1.0, "color": "#AB63FA"},
    "하늘고": {"ec_target": 2.0, "color": "#00CC96"}, # 최적
    "아라고": {"ec_target": 4.0, "color": "#636EFA"},
    "동산고": {"ec_target": 8.0, "color": "#EF553B"}
}

# 2. 데이터 로딩 함수 (캐싱 및 파일명 정규화 적용)
@st.cache_data
def load_all_data():
    data_dir = Path("data")
    if not data_dir.exists():
        st.error("❌ 'data/' 디렉토리가 존재하지 않습니다.")
        return None, None

    env_dfs = {}
    growth_df_dict = {}

    # 파일명 정규화 비교 함수
    def normalize_compare(target_name, file_name):
        return unicodedata.normalize('NFC', file_name) == unicodedata.normalize('NFC', target_name)

    all_files = list(data_dir.iterdir())

    # 환경 데이터 로드
    for school in SCHOOL_INFO.keys():
        target_filename = f"{school}_환경데이터.csv"
        found_file = next((f for f in all_files if normalize_compare(target_filename, f.name)), None)
        
        if found_file:
            df = pd.read_csv(found_file)
            df['school'] = school
            env_dfs[school] = df
        else:
            st.warning(f"⚠️ {school} 환경 데이터를 찾을 수 없습니다.")

    # 생육 결과 데이터 로드 (xlsx)
    growth_filename = "4개교_생육결과데이터.xlsx"
    found_growth_file = next((f for f in all_files if normalize_compare(growth_filename, f.name)), None)

    if found_growth_file:
        xlsx = pd.ExcelFile(found_growth_file)
        # 시트명 정규화 처리하여 로드
        for sheet in xlsx.sheet_names:
            norm_sheet = unicodedata.normalize('NFC', sheet)
            school_match = next((s for s in SCHOOL_INFO.keys() if s in norm_sheet), None)
            if school_match:
                df = pd.read_excel(xlsx, sheet_name=sheet)
                df['school'] = school_match
                df['ec_target'] = SCHOOL_INFO[school_match]['ec_target']
                growth_df_dict[school_match] = df
    else:
        st.error("❌ 생육 결과 데이터 파일을 찾을 수 없습니다.")

    return env_dfs, growth_df_dict

# 3. 메인 로직
with st.spinner('데이터를 불러오는 중입니다...'):
    env_data, growth_data = load_all_data()

if env_data and growth_data:
    # 사이드바 설정
    st.sidebar.header("📍 필터 설정")
    selected_school = st.sidebar.selectbox("데이터 분석 학교 선택", ["전체"] + list(SCHOOL_INFO.keys()))

    st.title("🌱 극지식물 최적 EC 농도 연구 대시보드")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

    # --- Tab 1: 실험 개요 ---
    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("연구 배경 및 목적")
            st.info("본 연구는 극지 환경에서 식물의 생산성을 극대화하기 위한 최적의 배양액 농도(EC)를 도출하는 것을 목적으로 합니다.")
            
            # 정보 테이블 구성
            info_table = []
            total_plants = 0
            for s, info in SCHOOL_INFO.items():
                count = len(growth_data[s]) if s in growth_data else 0
                total_plants += count
                info_table.append({"학교명": s, "목표 EC": info['ec_target'], "개체 수": count})
            st.table(pd.DataFrame(info_table))

        with col2:
            st.subheader("핵심 지표")
            m1, m2 = st.columns(2)
            m3, m4 = st.columns(2)
            
            all_env = pd.concat(env_data.values())
            m1.metric("총 개체수", f"{total_plants} 개")
            m2.metric("평균 온도", f"{all_env['temperature'].mean():.1f} °C")
            m3.metric("평균 습도", f"{all_env['humidity'].mean():.1f} %")
            m4.metric("🏆 최적 EC", "2.0 (하늘고)")

    # --- Tab 2: 환경 데이터 ---
    with tab2:
        st.subheader("학교별 환경 지표 비교")
        
        # 데이터 집계
        env_summary = []
        for s, df in env_data.items():
            env_summary.append({
                "학교": s,
                "평균 온도": df['temperature'].mean(),
                "평균 습도": df['humidity'].mean(),
                "평균 pH": df['ph'].mean(),
                "실측 EC": df['ec'].mean(),
                "목표 EC": SCHOOL_INFO[s]['ec_target']
            })
        summary_df = pd.DataFrame(env_summary)

        # 2x2 서브플롯
        fig_env = make_subplots(rows=2, cols=2, subplot_titles=("평균 온도 (°C)", "평균 습도 (%)", "평균 pH", "목표 vs 실측 EC"))
        
        fig_env.add_trace(go.Bar(x=summary_df['학교'], y=summary_df['평균 온도'], name="온도", marker_color="#FFA15A"), row=1, col=1)
        fig_env.add_trace(go.Bar(x=summary_df['학교'], y=summary_df['평균 습도'], name="습도", marker_color="#19D3F3"), row=1, col=2)
        fig_env.add_trace(go.Bar(x=summary_df['학교'], y=summary_df['평균 pH'], name="pH", marker_color="#FECB52"), row=2, col=1)
        
        fig_env.add_trace(go.Bar(x=summary_df['학교'], y=summary_df['목표 EC'], name="목표 EC"), row=2, col=2)
        fig_env.add_trace(go.Bar(x=summary_df['학교'], y=summary_df['실측 EC'], name="실측 EC"), row=2, col=2)

        fig_env.update_layout(height=700, font=dict(family="Malgun Gothic, Noto Sans KR, sans-serif"), showlegend=False)
        st.plotly_chart(fig_env, use_container_width=True)

        # 선택 학교 시계열 분석
        if selected_school != "전체":
            st.subheader(f"📈 {selected_school} 실시간 환경 변화")
            target_df = env_data[selected_school].copy()
            target_df['time'] = pd.to_datetime(target_df['time'])
            
            fig_line = make_subplots(specs=[[{"secondary_y": True}]])
            fig_line.add_trace(go.Scatter(x=target_df['time'], y=target_df['temperature'], name="온도 (°C)"), secondary_y=False)
            fig_line.add_trace(go.Scatter(x=target_df['time'], y=target_df['humidity'], name="습도 (%)", line=dict(dash='dot')), secondary_y=True)
            fig_line.add_trace(go.Scatter(x=target_df['time'], y=target_df['ec'], name="실측 EC", line=dict(width=3)), secondary_y=False)
            # 목표 EC 수평선
            fig_line.add_hline(y=SCHOOL_INFO[selected_school]['ec_target'], line_dash="dash", line_color="red", annotation_text="목표 EC")
            
            st.plotly_chart(fig_line, use_container_width=True)

        with st.expander("📂 환경 데이터 원본 확인 및 다운로드"):
            combined_env = pd.concat(env_data.values())
            st.dataframe(combined_env)
            csv = combined_env.to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV 다운로드", csv, "env_data.csv", "text/csv")

    # --- Tab 3: 생육 결과 ---
    with tab3:
        all_growth = pd.concat(growth_data.values())
        
        # 핵심 결과 카드
        avg_weight = all_growth.groupby('school')['생중량(g)'].mean().reset_index()
        best_school = avg_weight.loc[avg_weight['생중량(g)'].idxmax(), 'school']
        
        st.success(f"🥇 가장 우수한 생육을 보인 그룹: **{best_school} (EC {SCHOOL_INFO[best_school]['ec_target']})**")

        # 2x2 생육 비교 그래프
        growth_metrics = ['생중량(g)', '잎 수(장)', '지상부 길이(mm)', '개체번호'] # 개체번호는 count용
        fig_growth = make_subplots(rows=2, cols=2, subplot_titles=("평균 생중량(g) ⭐", "평균 잎 수(장)", "평균 지상부 길이(mm)", "실험 개체수"))

        # 집계 데이터
        agg_growth = all_growth.groupby('school').agg({
            '생중량(g)': 'mean',
            '잎 수(장)': 'mean',
            '지상부 길이(mm)': 'mean',
            '개체번호': 'count'
        }).reindex(list(SCHOOL_INFO.keys()))

        colors = [info['color'] for info in SCHOOL_INFO.values()]
        
        fig_growth.add_trace(go.Bar(x=agg_growth.index, y=agg_growth['생중량(g)'], marker_color=colors), row=1, col=1)
        fig_growth.add_trace(go.Bar(x=agg_growth.index, y=agg_growth['잎 수(장)'], marker_color=colors), row=1, col=2)
        fig_growth.add_trace(go.Bar(x=agg_growth.index, y=agg_growth['지상부 길이(mm)'], marker_color=colors), row=2, col=1)
        fig_growth.add_trace(go.Bar(x=agg_growth.index, y=agg_growth['개체번호'], marker_color=colors), row=2, col=2)

        fig_growth.update_layout(height=700, showlegend=False, font=dict(family="Malgun Gothic, sans-serif"))
        st.plotly_chart(fig_growth, use_container_width=True)

        # 분포 및 상관관계
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("학교별 생중량 분포")
            fig_box = px.box(all_growth, x="school", y="생중량(g)", color="school", color_discrete_map={k: v['color'] for k, v in SCHOOL_INFO.items()})
            st.plotly_chart(fig_box, use_container_width=True)
        with c2:
            st.subheader("잎 수 vs 생중량 상관관계")
            fig_scatter = px.scatter(all_growth, x="잎 수(장)", y="생중량(g)", color="school", trendline="ols")
            st.plotly_chart(fig_scatter, use_container_width=True)

        with st.expander("📂 생육 데이터 원본 확인 및 다운로드"):
            st.dataframe(all_growth)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                all_growth.to_excel(writer, index=False, sheet_name='Combined_Data')
            buffer.seek(0)
            st.download_button(
                label="Excel 다운로드",
                data=buffer,
                file_name="growth_data_total.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.error("데이터 파일을 로드할 수 없습니다. 파일 경로와 파일명을 확인해주세요.")
