import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="그래프 분석",
    layout="wide"
)


class SurveyAnalyzer:
    """설문 정제 데이터 분석 및 시각화 지원 클래스"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.score_cols = [c for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6R"] if c in self.df.columns]

    def get_summary_metrics(self) -> dict:
        """주요 요약 지표 산출"""
        valid_count = len(self.df)
        avg_time = self.df["AI사용시간"].mean() if "AI사용시간" in self.df.columns else 0.0

        if self.score_cols:
            avg_ethics = self.df[self.score_cols].mean().mean()
        else:
            avg_ethics = 0.0

        return {
            "valid_count": valid_count,
            "avg_time": avg_time,
            "avg_ethics": avg_ethics
        }

    def get_college_counts(self) -> pd.DataFrame:
        """단과대학별 응답자 수 산출"""
        if "소속단과대학" in self.df.columns:
            counts = self.df["소속단과대학"].value_counts().sort_index()
            return pd.DataFrame({"정제_후": counts})
        return pd.DataFrame()

    def get_group_stats(self, group_col: str) -> pd.DataFrame:
        """집단별 인원 수 및 문항 평균 집계 (소수점 둘째자리)"""
        if group_col not in self.df.columns or not self.score_cols:
            return pd.DataFrame()

        grouped = self.df.groupby(group_col)
        count_series = grouped.size().rename("인원수")
        mean_df = grouped[self.score_cols].mean()
        overall_mean = mean_df.mean(axis=1).rename("종합평균")

        result = pd.concat([count_series, mean_df, overall_mean], axis=1)
        return result.round(2)


def render_summary_section(analyzer: SurveyAnalyzer):
    """1. 요약 지표 영역 렌더링"""
    metrics = analyzer.get_summary_metrics()

    st.subheader("1. 요약 지표")
    col1, col2, col3 = st.columns(3)
    col1.metric("유효 응답", f"{metrics['valid_count']}명")
    col2.metric("평균 AI 사용 시간", f"{metrics['avg_time']:.1f}분")
    col3.metric("AI 윤리의식 평균", f"{metrics['avg_ethics']:.2f}점")
    st.markdown("---")


def render_comparison_section(analyzer: SurveyAnalyzer):
    """2. 정제 전후 단과대학별 응답자 수 비교 영역 렌더링"""
    st.subheader("2. 정제 전후 비교")

    clean_counts = analyzer.get_college_counts()

    # 세션에 원본 데이터가 남아있는 경우 연동, 없는 경우 정제 데이터 단독 표시
    if "raw_df" in st.session_state and "소속단과대학" in st.session_state["raw_df"].columns:
        raw_counts = st.session_state["raw_df"]["소속단과대학"].value_counts().rename("정제_전")
        comp_df = pd.concat([raw_counts, clean_counts["정제_후"]], axis=1).fillna(0)
    else:
        comp_df = clean_counts.rename(columns={"정제_후": "응답자수"})

    st.write("단과대학별 응답자 수 비교 (가로 막대 차트)")
    # 한글 범주 레이블 표기를 위해 가로 막대 차트 사용
    st.bar_chart(comp_df, horizontal=True)
    st.markdown("---")


def render_tab_demographics(df: pd.DataFrame):
    """탭 1: 응답자 구성 렌더링"""
    col1, col2 = st.columns(2)

    with col1:
        st.write("성별 분포")
        if "성별" in df.columns:
            gender_counts = df["성별"].value_counts()
            st.bar_chart(gender_counts, horizontal=True)

    with col2:
        st.write("학년별 분포")
        if "학년" in df.columns:
            grade_counts = df["학년"].value_counts().sort_index()
            st.bar_chart(grade_counts, horizontal=True)

    st.write("단과대학별 분포")
    if "소속단과대학" in df.columns:
        college_counts = df["소속단과대학"].value_counts().sort_index()
        st.bar_chart(college_counts, horizontal=True)


def render_tab_items(df: pd.DataFrame, score_cols: list):
    """탭 2: 문항별 평균 점수 렌더링"""
    st.write("문항별 평균 점수")
    if score_cols:
        item_means = df[score_cols].mean()
        # 한글/문항 이름 식별을 위해 가로 막대 차트로 표시
        st.bar_chart(item_means, horizontal=True)
        st.dataframe(pd.DataFrame(item_means.round(2), columns=["평균점수"]), use_container_width=True)
    else:
        st.info("분석 가능한 문항 컬럼(Q1~Q6R)이 존재하지 않습니다.")


def render_tab_group_comparison(analyzer: SurveyAnalyzer):
    """탭 3: 집단 비교 (학년별, 단과대학별) 렌더링"""
    st.write("학년별 평균 및 인원 수")
    grade_stats = analyzer.get_group_stats("학년")
    if not grade_stats.empty:
        st.dataframe(grade_stats, use_container_width=True)
        # 학년별 종합평균 가로 막대 차트
        st.bar_chart(grade_stats[["종합평균"]], horizontal=True)

    st.write("단과대학별 평균 및 인원 수")
    college_stats = analyzer.get_group_stats("소속단과대학")
    if not college_stats.empty:
        st.dataframe(college_stats, use_container_width=True)
        # 단과대학별 종합평균 가로 막대 차트
        st.bar_chart(college_stats[["종합평균"]], horizontal=True)


def render_tab_time_and_score(df: pd.DataFrame, score_cols: list):
    """탭 4: 사용 시간과 점수 관계 렌더링"""
    st.write("AI 사용 시간 구간별 평균 점수")
    if "AI사용시간" in df.columns and score_cols:
        # 시간 구간 분할 (30분 단위)
        bins = [0, 30, 60, 120, 240, 1000]
        labels = ["30분이하", "31~60분", "61~120분", "121~240분", "240분초과"]
        temp_df = df.copy()
        temp_df["사용시간구간"] = pd.cut(temp_df["AI사용시간"], bins=bins, labels=labels, include_lowest=True)

        time_group = temp_df.groupby("사용시간구간", observed=False)[score_cols].mean()
        time_group["종합평균"] = time_group.mean(axis=1)

        st.dataframe(time_group.round(2), use_container_width=True)
        # 구간별 종합 점수 가로 막대 차트
        st.bar_chart(time_group[["종합평균"]], horizontal=True)
    else:
        st.info("AI사용시간 데이터 또는 문항 점수 데이터가 부족합니다.")


def main():
    st.title("그래프 분석")

    # 세션 상태 확인 및 데이터 로드 분기
    clean_df = None
    if "clean_df" in st.session_state:
        clean_df = st.session_state["clean_df"]
    else:
        st.warning("정제된 데이터가 세션에 없습니다. 아래에서 정제된 CSV 파일을 직접 업로드하십시오.")
        uploaded_file = st.file_uploader("정제된 CSV 파일 업로드", type=["csv"])
        if uploaded_file is not None:
            clean_df = pd.read_csv(uploaded_file)
            st.session_state["clean_df"] = clean_df

    if clean_df is None:
        return

    # 분석 클래스 인스턴스화
    analyzer = SurveyAnalyzer(clean_df)

    # 1. 요약 지표
    render_summary_section(analyzer)

    # 2. 정제 전후 비교
    render_comparison_section(analyzer)

    # 3. 4개 탭 분석 영역
    st.subheader("3. 상세 분석")
    tab1, tab2, tab3, tab4 = st.tabs([
        "응답자 구성",
        "문항별 평균",
        "집단 비교",
        "사용 시간과 점수"
    ])

    with tab1:
        render_tab_demographics(clean_df)

    with tab2:
        render_tab_items(clean_df, analyzer.score_cols)

    with tab3:
        render_tab_group_comparison(analyzer)

    with tab4:
        render_tab_time_and_score(clean_df, analyzer.score_cols)


if __name__ == "__main__":
    main()