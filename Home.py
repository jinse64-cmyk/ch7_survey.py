import streamlit as st

st.set_page_config(
    page_title="설문 데이터 분석 대시보드",
    page_icon="📊",
    layout="wide"
)

st.title("📊 설문 데이터 분석 대시보드")
st.markdown("---")

st.markdown("""
### 환영합니다!
본 대시보드는 구글 설문지 결과 데이터를 정제하고 심층 분석하기 위한 멀티페이지 애플리케이션입니다.

#### 🚀 사용 가이드
1. 왼쪽 사이드바의 **`1_데이터_정제`** 페이지로 이동합니다.
2. `survey_raw.csv` 파일을 업로드합니다.
3. 사이드바 설정(이상치 필터, 결측치 처리 방식)을 확인하고 정제를 완료합니다.
4. 정제된 데이터를 확인하고 다운로드하거나, 후속 분석 페이지에서 활용할 수 있습니다.
""")

if "clean_df" in st.session_state:
    st.success(f"현재 세션에 정제된 데이터가 준비되어 있습니다: 총 {len(st.session_state['clean_df'])}건")
else:
    st.info("아직 정제된 데이터가 없습니다. 사이드바의 **1_데이터_정제** 페이지에서 데이터를 업로드해주세요.")