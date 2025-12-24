import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# --- 1. 페이지 설정 및 한글 폰트 설정 ---
st.set_page_config(page_title="🌱 극지식물 최적 EC 농도 연구", layout="wide")

# 한글 폰트 깨짐 방지 CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 기본 설정
SCHOOL_INFO = {
    "송도고": {"ec_target": 1.0, "color": "#AB63FA"},
    "하늘고": {"ec_target": 2.0, "color": "#00CC96"},  # 최적
    "아라고": {"ec_target": 4.0, "color": "#636EFA"},
    "동산고": {"ec_target": 8.0, "color": "#EF553B"}
}

# --- 2. 데이터 로딩 함수 (경로 자동 탐색 및 정규화) ---
@st.cache_data
def load_all_data():
    # 현재 디렉토리 및 하위 디렉토리에서 'data' 폴더 찾기
    current_path = Path(".")
    data_dir = None
    
    # 1순위: 현재 디렉토리의 data 폴더
    if (current_path / "data").is_dir():
        data_dir = current_path / "data"
    else:
        # 2순위: 하위 디렉토리 어디든 'data'라는 이름의 폴더 탐색
        for p in current_path.rglob("*"):
            if p.is_dir() and p.name == "data":
                data_dir = p
                break
            
    if data_dir is None:
        return None, None, "data 폴더를 찾을 수 없습니다."

    env_dfs = {}
    growth_df_dict = {}

    def normalize_nfc(text):
        return unicodedata.normalize('NFC', text)

    # 모든 파일 목록 (재귀적 탐색)
    all_files = list(data_dir.rglob("*"))

    # A. 환경 데이터 로드 (CSV)
    for school in SCHOOL_INFO.keys():
        target_name = f"{school}_환경데이터.csv"
        found_file = next((f for f in all_files if normalize_nfc(target_name) in normalize_nfc(f.name)), None)
        
        if found_file:
            try:
                # 인코딩 대응 (UTF-8 -> CP949 순서)
                try:
                    df = pd.read_csv(found_file, encoding='utf-8-sig')
                except:
                    df = pd.read_csv(found_file, encoding='cp949')
                df['school'] = school
                env_dfs[school] = df
            except Exception as e:
                st.error(f"{school} CSV 로딩 실패: {e}")

    # B. 생육 결과 데이터 로드 (XLSX)
    growth_file_name = "4개교_생육결과데이터.xlsx"
    found_growth_file = next((f for f in all_files if normalize_nfc(growth_file_name) in normalize_nfc(f.name)), None)

    if found_growth_file:
        try:
            xlsx = pd.ExcelFile(found_growth_file)
            for sheet in xlsx.sheet_names:
                norm_sheet = normalize_nfc(sheet)
                school_match = next((s for s in SCHOOL_INFO.keys() if s in norm_sheet), None)
                if school_match:
                    df = pd.read_excel(xlsx, sheet_name=sheet)
                    df['school'] = school_match
                    df['ec_target'] = SCHOOL_INFO[school_match]['ec_target']
                    growth_df_dict[school_match] = df
        except Exception as e:
            st.error(f"엑셀 로딩 실패: {e}")
    else:
        return env_dfs, growth_df_dict, "생육 결과 엑셀 파일을 찾을 수 없습니다."

    return env_dfs, growth_df_dict, None

# --- 3. 실행부 ---
with st.spinner('📊 데이터를 분석하는 중입니다...'):
    env_data, growth_data, error_msg = load_all_data()

if error_msg:
    st.error(f"❌ 오류 발생: {error_msg}")
    st.info("파일 구조 예시: `data/송도고_환경데이터.csv`, `data/4개교_생육결과데이터.xlsx`")
    st.stop()

# --- 4. 대시보드 화면 구성 ---
st.title("🌱 극지식물 최적 EC 농도 연구")
selected_school = st.sidebar.selectbox("🏫 분석 대상 학교", ["전체"] + list(SCHOOL_INFO.keys()))

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# --- Tab 1: 실험 개요 ---
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("연구 배경 및 목적")
        st.markdown("""> 본 연구는 극지식물의 생산성 향상을 위해 **배양액 농도(EC) 변화**가 
        식물의 생중량 및 잎 수 등 생육 지표에 미치는 영향을 분석합니다.""")
        
        summary_rows = []
        for s, info in SCHOOL_INFO.items():
            count = len(growth_data[s]) if s in growth_data else 0
            summary_rows.append({"학교": s, "목표 EC": info['ec_target'], "개체수": f"{count}개"})
        st.table(pd.DataFrame(summary_rows))

    with col2:
        st.subheader("주요 지표 (전체 평균)")
        all_env = pd.concat(env_data.values())
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        m1.metric("평균 온도", f"{all_env['temperature'].mean():.1f} °C")
        m2.metric("평균 습도", f"{all_env['humidity'].mean():.1f} %")
        m3.metric("평균 pH", f"{all_env['ph'].mean():.2f}")
        m4.metric("🏆 최적 EC", "2.0 (하늘고)", delta="생중량 최대")

# --- Tab 2: 환경 데이터 ---
with tab2:
    st.subheader("학교별 환경 지표 비교")
    env_summary = []
    for s, df in env_data.items():
        env_summary.append({
            "학교": s, "온도": df['temperature'].mean(), "습도": df['humidity'].mean(),
            "pH": df['ph'].mean(), "실측EC": df['ec'].mean(), "목표EC": SCHOOL_INFO[s]['ec_target']
        })
    sum_df = pd.DataFrame(env_summary)

    fig_env = make_subplots(rows=2, cols=2, subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 vs 실측 EC"))
    fig_env.add_trace(go.Bar(x=sum_df['학교'], y=sum_df['온도'], name="온도"), row=1, col=1)
    fig_env.add_trace(go.Bar(x=sum_df['학교'], y=sum_df['습도'], name="습도"), row=1, col=2)
    fig_env.add_trace(go.Bar(x=sum_df['학교'], y=sum_df['pH'], name="pH"), row=2, col=1)
    fig_env.add_trace(go.Bar(x=sum_df['학교'], y=sum_df['목표EC'], name="목표"), row=2, col=2)
    fig_env.add_trace(go.Bar(x=sum_df['학교'], y=sum_df['실측EC'], name="실측"), row=2, col=2)
    
    fig_env.update_layout(height=600, font=dict(family="Malgun Gothic"), showlegend=False)
    st.plotly_chart(fig_env, use_container_width=True)

    with st.expander("원본 데이터 및 CSV 다운로드"):
        st.dataframe(all_env)
        st.download_button("CSV 다운로드", all_env.to_csv(index=False).encode('utf-8-sig'), "env_data.csv")

# --- Tab 3: 생육 결과 ---
with tab3:
    all_growth = pd.concat(growth_data.values())
    
    # 핵심 통계
    st.info("💡 **하늘고(EC 2.0)**에서 생중량이 가장 높게 나타나, 해당 농도가 최적임을 시사합니다.")
    
    fig_growth = make_subplots(rows=2, cols=2, subplot_titles=("평균 생중량(g)", "평균 잎 수", "지상부 길이(mm)", "개체수"))
    agg_g = all_growth.groupby('school').mean(numeric_only=True).reindex(list(SCHOOL_INFO.keys()))
    agg_c = all_growth.groupby('school').size().reindex(list(SCHOOL_INFO.keys()))
    
    colors = [info['color'] for info in SCHOOL_INFO.values()]
    fig_growth.add_trace(go.Bar(x=agg_g.index, y=agg_g['생중량(g)'], marker_color=colors), row=1, col=1)
    fig_growth.add_trace(go.Bar(x=agg_g.index, y=agg_g['잎 수(장)'], marker_color=colors), row=1, col=2)
    fig_growth.add_trace(go.Bar(x=agg_g.index, y=agg_g['지상부 길이(mm)'], marker_color=colors), row=2, col=1)
    fig_growth.add_trace(go.Bar(x=agg_c.index, y=agg_c.values, marker_color=colors), row=2, col=2)
    
    fig_growth.update_layout(height=700, font=dict(family="Malgun Gothic"), showlegend=False)
    st.plotly_chart(fig_growth, use_container_width=True)

    with st.expander("원본 데이터 및 Excel 다운로드"):
        st.dataframe(all_growth)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            all_growth.to_excel(writer, index=False)
        st.download_button("Excel 다운로드", output.getvalue(), "growth_results.xlsx")
