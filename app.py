import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(
    page_title="국내 식품 회수·판매중지 위해 요인 분석",
    layout="wide"
)

# 2. 한글 폰트 설정 (로컬 Windows/Mac 및 Streamlit Cloud Linux 모두 대응)
def set_korean_font():
    font_candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Streamlit Cloud (Linux)
        "C:/Windows/Fonts/malgun.ttf",                      # Windows
        "/System/Library/Fonts/AppleGothic.ttf",            # Mac
    ]
    for path in font_candidates:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            font_name = fm.FontProperties(fname=path).get_name()
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()

# 3. 데이터 로드 및 전처리
@st.cache_data
def load_data(filepath="I0490.csv"):
    df = pd.read_csv(filepath, encoding="utf-8")

    df["CRET_DT"] = pd.to_datetime(df["CRET_DTM"], errors="coerce")
    df["YEAR"] = df["CRET_DT"].dt.year
    df["YM"] = df["CRET_DT"].dt.to_period("M").astype(str)

    df["PRDLST_TYPE"] = df["PRDLST_TYPE"].fillna("미분류(무등록 등)")
    df["RTRVL_GRDCD_NM"] = df["RTRVL_GRDCD_NM"].fillna("등급미상")

    def classify_reason(text):
        t = str(text)
        if any(k in t for k in ["세균", "대장균", "리스테리아", "황색포도상구균", "살모넬라", "바실러스", "클로스트리디움", "곰팡이", "진균", "노로바이러스", "비브리오", "미생물", "식중독"]):
            return "미생물·식중독균"
        if any(k in t for k in ["잔류농약", "농약", "동물용의약품", "항생제", "항균"]):
            return "잔류농약·의약품"
        if any(k in t for k in ["이물", "유리", "금속", "플라스틱", "벌레", "쇳가루", "돌", "비닐"]):
            return "이물 혼입"
        if any(k in t for k in ["중금속", "납", "카드뮴", "수은", "비소", "아플라톡신", "제랄레논", "벤조피렌", "MCPD", "프탈레이트", "DEHP", "용출", "포름알데히드", "초산에틸", "타르색소", "보존료", "첨가물", "알레르기", "알러지", "아황산", "발색제", "파라핀", "소르빈산", "안식향산", "메탄올", "에틸카바메이트", "독소", "히스타민", "잔류용매", "벤젠", "산화방지제", "감미료", "색소", "형광증백제", "타다라필", "실데나필", "피록시캄", "발기부전", "기준초과", "기준 초과", "기준치 초과", "불검출", "양성"]):
            return "화학적 위해·부정물질"
        if any(k in t for k in ["무등록", "무신고", "영업등록", "영업신고", "미신고", "미등록", "수입신고", "품목제조보고", "허용되지 않는", "사용불가", "사용금지", "원료"]):
            return "무등록·불법원료"
        if any(k in t for k in ["표시", "유통기한", "소비기한", "제조일자", "경과", "변조", "허위", "과대광고"]):
            return "표시·기한 위반"
        if any(k in t for k in ["함량", "붕해", "산가", "과산화물가", "성상", "수분", "회분", "당도", "알코올", "프로바이오틱스", "진세노사이드", "기능성", "영양", "품질", "부적합"]):
            return "품질·함량 부적합"
        return "기타"

    df["REASON_CAT"] = df["RTRVLPRVNS"].apply(classify_reason)

    sido_map = {
        "서울": "서울특별시", "서울시": "서울특별시",
        "경북": "경상북도", "경남": "경상남도",
        "울산": "울산광역시", "인천": "인천광역시",
        "강원": "강원특별자치도", "전남광주통합특별시": "전남·광주"
    }
    def clean_sido(addr):
        if pd.isna(addr):
            return "미상"
        first = str(addr).split()[0]
        if first.startswith("경남"):
            return "경상남도"
        return sido_map.get(first, first)

    df["SIDO"] = df["ADDR"].apply(clean_sido)
    return df

df = load_data()

# 4. 사이드바 필터 위젯
st.sidebar.header("조회 조건 필터")

min_year, max_year = int(df["YEAR"].min()), int(df["YEAR"].max())
year_range = st.sidebar.slider("등록 연도 범위", min_year, max_year, (min_year, max_year))

all_grades = ["1등급", "2등급", "3등급", "자율회수", "등급미상"]
available_grades = [g for g in all_grades if g in df["RTRVL_GRDCD_NM"].unique()]
selected_grades = st.sidebar.multiselect("회수 등급", available_grades, default=available_grades)

all_types = df["PRDLST_TYPE"].value_counts().index.tolist()
selected_types = st.sidebar.multiselect("식품 유형", all_types, default=all_types)

# 필터 적용
filtered = df[
    (df["YEAR"].between(year_range[0], year_range[1])) &
    (df["RTRVL_GRDCD_NM"].isin(selected_grades)) &
    (df["PRDLST_TYPE"].isin(selected_types))
]

# 5. 헤더 및 핵심 KPI
st.title("국내 식품 회수·판매중지 위해 요인 분석")
st.markdown(
    "**핵심 질문:** 국내 식품 회수·판매중지 원인은 **식품 유형**에 따라 어떻게 다르며, "
    "가장 위험한 **1등급 회수**는 실제로 어떤 원인에서 발생하는가?"
)
st.caption("출처: 식품의약품안전처 식품안전나라 Open API (I0490, 식품의 회수 및 판매중지 정보) | 집계 기준: 공고 등록일(CRET_DTM)")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바 필터를 조정해 주세요.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
total_cnt = len(filtered)
grade1_cnt = (filtered["RTRVL_GRDCD_NM"] == "1등급").sum()
grade1_ratio = (grade1_cnt / total_cnt * 100) if total_cnt > 0 else 0
top_reason = filtered["REASON_CAT"].value_counts().index[0]
top_type = filtered["PRDLST_TYPE"].value_counts().index[0]

col1.metric("선택 조건 회수 건수", f"{total_cnt:,}건")
col2.metric("1등급(최고위해) 비중", f"{grade1_ratio:.1f}%", f"{grade1_cnt}건")
col3.metric("최다 회수 사유", top_reason)
col4.metric("최다 회수 식품유형", top_type)

st.divider()

# 6. 차트 1: 식품유형 x 회수사유 히트맵 (Seaborn)
st.subheader("1. 식품 유형별 주요 회수 사유 구조 (Heatmap)")
top_n_types = filtered["PRDLST_TYPE"].value_counts().head(7).index
ct_type = pd.crosstab(
    filtered[filtered["PRDLST_TYPE"].isin(top_n_types)]["PRDLST_TYPE"],
    filtered[filtered["PRDLST_TYPE"].isin(top_n_types)]["REASON_CAT"]
).loc[top_n_types]

fig1, ax1 = plt.subplots(figsize=(10, 4.5))
sns.heatmap(ct_type, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5, ax=ax1)
ax1.set_xlabel("회수 사유 카테고리")
ax1.set_ylabel("식품 유형 (상위 7개)")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
st.pyplot(fig1)

# 7. 차트 2 & 3 나란히 배치
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("2. 회수 등급별 사유 비중 (Stacked Bar)")
    grade_order = [g for g in ["1등급", "2등급", "3등급"] if g in filtered["RTRVL_GRDCD_NM"].unique()]
    if grade_order:
        ct_grade = pd.crosstab(
            filtered[filtered["RTRVL_GRDCD_NM"].isin(grade_order)]["RTRVL_GRDCD_NM"],
            filtered[filtered["RTRVL_GRDCD_NM"].isin(grade_order)]["REASON_CAT"],
            normalize="index"
        ).loc[grade_order] * 100

        fig2, ax2 = plt.subplots(figsize=(6.5, 4.5))
        ct_grade.plot(kind="bar", stacked=True, colormap="tab10", ax=ax2)
        ax2.set_ylabel("비중 (%)")
        ax2.set_xlabel("회수 등급")
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=0)
        ax2.legend(title="회수 사유", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)
    else:
        st.info("1~3등급 데이터를 선택하면 등급별 비중 차트가 표시됩니다.")

with right_col:
    st.subheader("3. 제조·판매업체 지역별 회수 건수 Top 10")
    sido_counts = filtered["SIDO"].value_counts().head(10)
    fig3, ax3 = plt.subplots(figsize=(6.5, 4.5))
    sns.barplot(x=sido_counts.values, y=sido_counts.index, palette="Blues_r", ax=ax3)
    ax3.set_xlabel("회수 건수")
    ax3.set_ylabel("시도")
    for i, v in enumerate(sido_counts.values):
        ax3.text(v + 0.5, i, str(v), va="center", fontsize=9)
    plt.tight_layout()
    st.pyplot(fig3)

# 8. 데이터 한계 및 원본 테이블 확인
st.divider()
with st.expander("데이터 해석 시 유의사항 및 한계점"):
    st.markdown("""
    - **기간 편중:** 공개 API 데이터는 최근 2년(2025~2026년) 공고가 전체의 72% 이상을 차지하며, 과거 연도 데이터는 일부 누락되어 있어 연도별·계절별 추세 일반화에는 한계가 있습니다.
    - **분류 기준:** 서술형 텍스트(`RTRVLPRVNS`)를 핵심 키워드 기반으로 7개 범주로 재분류했으며, 복합 사유가 기재된 경우 우선순위에 따라 대표 사유 1개로 집계했습니다.
    """)

with st.expander("필터링된 상세 데이터 보기"):
    show_cols = ["CRET_DTM", "RTRVL_GRDCD_NM", "PRDLST_TYPE", "PRDTNM", "REASON_CAT", "RTRVLPRVNS", "BSSHNM", "SIDO"]
    st.dataframe(filtered[show_cols].rename(columns={
        "CRET_DTM": "등록일시", "RTRVL_GRDCD_NM": "회수등급", "PRDLST_TYPE": "식품유형",
        "PRDTNM": "제품명", "REASON_CAT": "사유분류", "RTRVLPRVNS": "원본회수사유",
        "BSSHNM": "업체명", "SIDO": "지역"
    }), use_container_width=True)