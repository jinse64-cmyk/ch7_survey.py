import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="데이터 정제 | 설문 데이터 분석",
    page_icon="🧹",
    layout="wide"
)


# ----------------- 유틸리티 함수 -----------------
def parse_time_to_minutes(val):
    """'1시간 30분', '90분', '2시간', 45 등의 문자열을 분 단위 정수로 변환"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()

    # 이미 숫자만 들어있는 경우
    if re.fullmatch(r"^\d+(\.\d+)?$", val_str):
        return int(float(val_str))

    hours = 0
    minutes = 0
    h_match = re.search(r"(\d+)\s*시간", val_str)
    m_match = re.search(r"(\d+)\s*분", val_str)

    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))

    if not h_match and not m_match:
        digits = re.findall(r"\d+", val_str)
        return int(digits[0]) if digits else None

    return hours * 60 + minutes


def map_grade(val):
    """'1학년', '일학년', 1 등을 숫자(1, 2, 3, 4)로 통일"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    word_map = {"일": 1, "이": 2, "삼": 3, "사": 4}

    for k, v in word_map.items():
        if k in val_str:
            return v

    num_match = re.search(r"\d+", val_str)
    return int(num_match.group(0)) if num_match else val


def map_college(val):
    """단과대학 분류 매핑"""
    if pd.isna(val):
        return "기타"
    val_str = str(val).strip()
    if "인문" in val_str:
        return "인문대학"
    elif "사과" in val_str or "사회" in val_str:
        return "사회과학대학"
    elif "경통" in val_str or "경제" in val_str:
        return "경제통상대학"
    elif "경영" in val_str:
        return "경영대학"
    elif "사범" in val_str:
        return "사범대학"
    return "기타"


# ----------------- 사이드바 설정 -----------------
st.sidebar.header("⚙️ 정제 파라미터 설정")

outlier_range = st.sidebar.slider(
    "AI 사용 시간 허용 범위 (분)",
    min_value=0,
    max_value=720,
    value=(0, 360),
    step=10,
    help="설정한 최소~최대 분(min) 범위를 벗어나는 행은 이상치로 제거됩니다."
)

na_action = st.sidebar.radio(
    "결측치(빈칸) 처리 방식",
    options=["그대로 두기", "행 삭제"],
    index=0
)

# ----------------- 메인 화면 -----------------
st.title("🧹 구글 설문 데이터 정제")
st.markdown("구글 설문지 결과 CSV 파일을 업로드하면 정해진 규칙에 따라 자동으로 정제합니다.")

uploaded_file = st.file_uploader("구글 설문지 CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    raw_df = pd.read_csv(uploaded_file)
    total_raw_count = len(raw_df)

    st.subheader(f"📋 원본 데이터 (응답자 수: {total_raw_count:,}명)")
    st.dataframe(raw_df, use_container_width=True)

    # 정제 복사본 생성
    df = raw_df.copy()
    cleaning_log = []

    # 1. 열 제목 축소
    col_mapping = [
        "타임스탬프", "성별", "학년", "소속단과대학", "AI사용시간",
        "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "서술형"
    ]
    if len(df.columns) >= len(col_mapping):
        rename_dict = {orig: new for orig, new in zip(df.columns[:len(col_mapping)], col_mapping)}
        df.rename(columns=rename_dict, inplace=True)
        cleaning_log.append({"단계": "1. 열제목 정리", "내용": f"앞선 {len(col_mapping)}개 열을 표준 규격명으로 변경"})
    else:
        cleaning_log.append({"단계": "1. 열제목 정리", "내용": "열 개수가 기준보다 적어 원본 이름을 유지했습니다."})

    # 2. 중복 제거 (타임스탬프 제외 나머지 열 일치 여부)
    non_ts_cols = [c for c in df.columns if c != "타임스탬프"]
    before_dup = len(df)
    df.drop_duplicates(subset=non_ts_cols, keep="first", inplace=True)
    cleaning_log.append({"단계": "2. 중복 제거", "내용": f"{before_dup - len(df)}개 행 제거 (타임스탬프 제외 일치 행)"})

    # 3. 학년 표기 통일
    if "학년" in df.columns:
        df["학년"] = df["학년"].apply(map_grade)
        cleaning_log.append({"단계": "3. 학년 표기", "내용": "숫자(1, 2, 3...) 형식으로 통일"})

    # 4. 단과대학 분류
    if "소속단과대학" in df.columns:
        df["소속단과대학"] = df["소속단과대학"].apply(map_college)
        cleaning_log.append({"단계": "4. 단과대학 분류", "내용": "규칙에 따라 단과대학명 재분류"})

    # 5. AI 사용시간 분 변환 및 이상치 필터링
    if "AI사용시간" in df.columns:
        df["AI사용시간"] = df["AI사용시간"].apply(parse_time_to_minutes)
        before_outlier = len(df)
        df = df[
            df["AI사용시간"].isna() |
            ((df["AI사용시간"] >= outlier_range[0]) & (df["AI사용시간"] <= outlier_range[1]))
            ]
        cleaning_log.append({
            "단계": "5. 이상치 필터링",
            "내용": f"허용 범위({outlier_range[0]}분 ~ {outlier_range[1]}분) 외 {before_outlier - len(df)}개 행 제거"
        })

    # 6. 결측치 확인 및 처리
    null_counts = df.isnull().sum()
    null_summary = ", ".join([f"{k}: {v}개" for k, v in null_counts.items() if v > 0]) or "결측치 없음"

    if na_action == "행 삭제":
        before_na = len(df)
        df.dropna(inplace=True)
        cleaning_log.append({"단계": "6. 결측치 처리", "내용": f"행 삭제 적용 ({before_na - len(df)}개 행 삭제됨)"})
    else:
        cleaning_log.append({"단계": "6. 결측치 처리", "내용": f"그대로 두기 유지 (열별 결측 현황: {null_summary})"})

    # 7. Q6R 역코딩 계산
    if "Q6" in df.columns:
        df["Q6"] = pd.to_numeric(df["Q6"], errors="coerce")
        df["Q6R"] = 6 - df["Q6"]
        cleaning_log.append({"단계": "7. 역코딩", "내용": "Q6R = 6 - Q6 컬럼 생성 완료"})

    # 세션 상태 저장
    st.session_state["clean_df"] = df

    st.markdown("---")
    st.subheader("📌 정제 요약 지표")

    # 카드 형태 메트릭 배치
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("원본 응답 수", f"{total_raw_count:,}명")
    m2.metric("정제 후 응답 수", f"{len(df):,}명", delta=f"{len(df) - total_raw_count}명")
    m3.metric("총 정제 단계", f"{len(cleaning_log)}단계")
    m4.metric("결측치 처리 모드", na_action)

    # 결측치 현황표 토글
    with st.expander("🔍 열별 결측치(빈칸) 상세 현황"):
        st.write(null_counts[null_counts > 0] if (null_counts > 0).any() else "모든 열에 빈칸이 없습니다.")

    # 정제 기록 표
    st.subheader("📝 데이터 정제 이력")
    st.table(pd.DataFrame(cleaning_log))

    # 정제된 데이터 표
    st.subheader("✨ 정제 완료 데이터")
    st.dataframe(df, use_container_width=True)

    # CSV 다운로드 버튼
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 정제된 데이터 CSV 다운로드",
        data=csv_bytes,
        file_name="survey_cleaned.csv",
        mime="text/csv"
    )
else:
    st.info("상단의 파일 업로더를 통해 구글 설문지 결과 CSV 파일을 업로드해주세요.")