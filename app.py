import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(
    page_title="What Triggers a Class 1 Food Recall?",
    layout="wide"
)

# 2. 한글 폰트 설정
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

filtered = df[
    (df["YEAR"].between(year_range[0], year_range[1])) &
    (df["RTRVL_GRDCD_NM"].isin(selected_grades)) &
    (df["PRDLST_TYPE"].isin(selected_types))
]

# 5. 헤더
st.title("What Triggers a Class 1 Food Recall?")
st.markdown("##### 식품 유형 및 회수 등급별 국내 식품 위해 요인 분석")
st.caption("출처: 식품의약품안전처 식품안전나라 Open API (I0490) | 집계 기준: 공고 등록일(CRET_DTM)")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바 필터를 조정해 주세요.")
    st.stop()

# 6. 핵심 KPI + 동적 결론 요약 박스
total_cnt = len(filtered)
grade1_df = filtered[filtered["RTRVL_GRDCD_NM"] == "1등급"]
grade1_cnt = len(grade1_df)
grade1_ratio = (grade1_cnt / total_cnt * 100) if total_cnt > 0 else 0
top_reason = filtered["REASON_CAT"].value_counts().index[0]
top_reason_pct = filtered["REASON_CAT"].value_counts(normalize=True).iloc[0] * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("선택 조건 총 회수 건수", f"{total_cnt:,}건")
col2.metric("1등급(최고위해) 비중", f"{grade1_ratio:.1f}%", f"{grade1_cnt}건")
col3.metric("전체 1위 회수 사유", top_reason, f"{top_reason_pct:.1f}%")
if not grade1_df.empty:
    g1_top = grade1_df["REASON_CAT"].value_counts().index[0]
    g1_top_pct = grade1_df["REASON_CAT"].value_counts(normalize=True).iloc[0] * 100
    col4.metric("1등급 1위 원인", g1_top, f"1등급 중 {g1_top_pct:.1f}%")
else:
    col4.metric("1등급 1위 원인", "해당 없음")

# 핵심 결론 박스 (한눈에 결과 파악)
if not grade1_df.empty:
    st.info(
        f"**핵심 분석 결과 ({year_range[0]}~{year_range[1]}년, {total_cnt:,}건 기준):** "
        f"① 식품 유형마다 주된 위해 요인이 뚜렷하게 다릅니다(예: 농산물→잔류농약, 축산물→미생물, 건강기능식품→품질·함량). "
        f"② 대중의 통념과 달리 가장 위험한 **1등급 회수({grade1_cnt}건)**의 최대 원인은 식중독균이 아니라 "
        f"**'{g1_top}'({g1_top_pct:.1f}%)**입니다."
    )

st.divider()

# 7. 차트 1: 식품유형 x 회수사유 비율(%) 히트맵 (전체 폭)
st.subheader("1. 식품 유형별 위해 요인 구조 (유형 내 비중 %)")
st.caption("각 식품 유형의 합을 100%로 정규화하여, 유형별로 어떤 사고가 집중되는지 비교합니다.")

top_n_types = filtered["PRDLST_TYPE"].value_counts().head(7).index
sub_df = filtered[filtered["PRDLST_TYPE"].isin(top_n_types)]
ct_pct = pd.crosstab(sub_df["PRDLST_TYPE"], sub_df["REASON_CAT"], normalize="index").loc[top_n_types] * 100
ct_cnt = pd.crosstab(sub_df["PRDLST_TYPE"], sub_df["REASON_CAT"]).loc[top_n_types]

# 셀 라벨: "78%\n(29)" 형식
annot_labels = ct_pct.copy().astype(str)
for r in ct_pct.index:
    for c in ct_pct.columns:
        p, cnt = ct_pct.loc[r, c], ct_cnt.loc[r, c]
        annot_labels.loc[r, c] = f"{p:.0f}%\n({cnt})" if cnt > 0 else ""

fig1, ax1 = plt.subplots(figsize=(11, 4.2), constrained_layout=True)
sns.heatmap(
    ct_pct, annot=annot_labels, fmt="", cmap="YlOrRd",
    linewidths=0.6, vmin=0, vmax=85, cbar_kws={"label": "유형 내 비중 (%)"}, ax=ax1
)
ax1.set_xlabel("")
ax1.set_ylabel("")
plt.xticks(rotation=20, ha="right", fontsize=10)
plt.yticks(fontsize=10)
st.pyplot(fig1, use_container_width=True)

st.divider()

# 8. 차트 2 & 3: 크기/비율 완전 통일 (6.5 x 4.5, constrained_layout)
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("2. 회수 등급별 사유 비중 (%)")
    st.caption("1등급(최고위해)과 3등급(일반위해)의 원인 구조 차이를 비교합니다.")

    grade_order = [g for g in ["1등급", "2등급", "3등급"] if g in filtered["RTRVL_GRDCD_NM"].unique()]
    if grade_order:
        ct_grade = pd.crosstab(
            filtered[filtered["RTRVL_GRDCD_NM"].isin(grade_order)]["RTRVL_GRDCD_NM"],
            filtered[filtered["RTRVL_GRDCD_NM"].isin(grade_order)]["REASON_CAT"],
            normalize="index"
        ).loc[grade_order] * 100

        fig2, ax2 = plt.subplots(figsize=(6.5, 4.5), constrained_layout=True)
        ct_grade.plot(kind="barh", stacked=True, colormap="tab10", width=0.55, ax=ax2)

        # 막대 내부에 10% 이상 항목 퍼센트 표시
        for container in ax2.containers:
            labels = [f"{v.get_width():.0f}%" if v.get_width() >= 10 else "" for v in container]
            ax2.bar_label(container, labels=labels, label_type="center", color="white", fontsize=9, fontweight="bold")

        ax2.set_xlim(0, 100)
        ax2.set_xlabel("비중 (%)")
        ax2.set_ylabel("")
        ax2.invert_yaxis()  # 1등급이 맨 위로 오게
        ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=8.5)
        st.pyplot(fig2, use_container_width=True)
    else:
        st.info("1~3등급 데이터를 선택하면 등급별 비중 차트가 표시됩니다.")

with right_col:
    st.subheader("3. 1등급(최고위해) 회수 원인 순위")
    st.caption("생명·건강 위해도가 가장 높은 1등급 회수 건의 실제 원인 분포입니다.")

    if not grade1_df.empty:
        g1_counts = grade1_df["REASON_CAT"].value_counts()
        fig3, ax3 = plt.subplots(figsize=(6.5, 4.5), constrained_layout=True)
        sns.barplot(x=g1_counts.values, y=g1_counts.index, color="#D9534F", ax=ax3)
        ax3.set_xlabel("1등급 회수 건수 (건)")
        ax3.set_ylabel("")
        ax3.set_xlim(0, g1_counts.max() * 1.18)
        for i, v in enumerate(g1_counts.values):
            pct = v / len(grade1_df) * 100
            ax3.text(v + 0.8, i, f"{v}건 ({pct:.1f}%)", va="center", fontsize=9.5, fontweight="bold")
        st.pyplot(fig3, use_container_width=True)
    else:
        st.info("사이드바에서 '1등급'을 포함하면 1등급 원인 순위가 표시됩니다.")

# 9. 한계점 및 원본 데이터
st.divider()
with st.expander("데이터 해석 시 유의사항 및 한계점"):
    st.markdown("""
    - **기간 편중:** 공개 API 데이터는 최근 2년(2025~2026년) 공고가 전체의 72% 이상을 차지하며 과거 연도 공고는 일부 누락되어 있어, 시계열·계절성 일반화에는 한계가 있습니다.
    - **분류 기준:** 서술형 텍스트(`RTRVLPRVNS`)를 핵심 키워드 기반 7개 범주로 재분류했으며, 복합 사유가 기재된 경우 대표 사유 1개로 집계했습니다.
    """)

with st.expander("필터링된 상세 데이터 보기"):
    show_cols = ["CRET_DTM", "RTRVL_GRDCD_NM", "PRDLST_TYPE", "PRDTNM", "REASON_CAT", "RTRVLPRVNS", "BSSHNM"]
    st.dataframe(filtered[show_cols].rename(columns={
        "CRET_DTM": "등록일시", "RTRVL_GRDCD_NM": "회수등급", "PRDLST_TYPE": "식품유형",
        "PRDTNM": "제품명", "REASON_CAT": "사유분류", "RTRVLPRVNS": "원본회수사유",
        "BSSHNM": "업체명"
    }), use_container_width=True)
