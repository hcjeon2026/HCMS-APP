import streamlit as st
import pdfplumber
import os
from pathlib import Path

# --- 0. 경로 및 초기 설정 ---
BASE_DIR = Path(os.getcwd())
LOGO_PATH = BASE_DIR / "logo.png"

st.set_page_config(page_title="HCMS 특수건강검진 자동안내", layout="centered")

# --- 1. UI 스타일 디자인 (컴팩트 & 프로페셔널) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto+Sans+KR', sans-serif; }
    .block-container { max-width: 750px; padding-top: 1.5rem; }
    .stApp { background-color: #F8FAFC; }
    .main-header { background: white; padding: 12px 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #004A7C; }
    .main-title { color: #004A7C; font-size: 20px; font-weight: 800; margin: 0; }
    .sub-title { color: #64748B; font-size: 12px; margin: 0; }
    
    .stTextInput input { border-radius: 12px !important; height: 38px !important; border: 1px solid #CBD5E1 !important; }
    .stButton button { border-radius: 12px; background-color: #004A7C; color: white; height: 38px !important; width: 100%; font-weight: 700; }
    
    .info-card { background: white; padding: 15px; border-radius: 12px; min-height: 140px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; }
    .card-title { font-size: 14px; font-weight: 700; color: #1E293B; border-bottom: 2px solid #F1F5F9; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
    .card-badge { font-size: 9px; background: #E0F2FE; color: #0369A1; padding: 2px 8px; border-radius: 10px; font-weight: 700; }
    
    .result-content { font-size: 13px; color: #334155; line-height: 1.5; }
    .material-highlight { color: #2563EB; font-weight: 700; background: #EFF6FF; padding: 2px 4px; border-radius: 4px; }
    .check-item { margin-bottom: 5px; font-size: 12.5px; font-weight: 600; color: #0F172A; }
    .footer { text-align: center; font-size: 10px; color: #94A3B8; margin-top: 30px; border-top: 1px solid #E2E8F0; padding-top: 10px; }
    </style>

    """, unsafe_allow_html=True)
# 모바일 환경 최적화 스타일 추가
st.markdown("""
    <style>
    /* 모바일에서 글자 크기 최적화 */
    @media (max-width: 640px) {
        .main-title { font-size: 1.1rem !important; }
        .sub-title { font-size: 0.75rem !important; }
        .check-item { width: 100% !important; } /* 리스트를 한 줄에 하나씩 */
        .info-card { padding: 10px; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 상단 헤더 ---
with st.container():
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    h1, h2 = st.columns([1, 8])
    with h1:
        if LOGO_PATH.exists(): st.image(str(LOGO_PATH), width=45)
    with h2:
        st.markdown('<p class="main-title">HCMS 특수건강검진 자동안내 시스템</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">전형철 보건관리자님을 위한 건설업 공종별 유해인자 통합 분석</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. 입력 섹션 ---
with st.container():
    c_in, c_btn = st.columns([5, 1])
    with c_in:
        search_input = st.text_input("검색어 입력", placeholder="직종(도장공, 미장공, 수장공 등) 또는 유해물질 입력", label_visibility="collapsed")
    with c_btn:
        st.button("조회")

    t1, t2, t3 = st.columns(3)
    with t1: is_pre = st.toggle("배치전 검진", value=True)
    with t2: is_vibration = st.toggle("진동작업", value=False)
    with t3: is_outdoor = st.toggle("실외(자외선)", value=False)

    uploaded_file = st.file_uploader("MSDS PDF 업로드 (선택사항)", type="pdf", label_visibility="collapsed")

# --- 4. 분석 엔진 (직종별 유해인자 전문 DB 적용) ---
def run_analysis(text, query):
    content = (text + " " + query).lower()
    items = ["신장", "체중", "혈압(공통)"]
    detected_hazards = []
    
    # [건설업 직종별 전문 DB] - KOSHA 및 보건관리 지침 기준
    job_db = {
        "도장": ["유기용제(톨루엔/자일렌)", "이소시아네이트", "요10종", "LFT(간기능)", "CBC(혈액)", "PFT(폐활량)"],
        "페인트": ["유기용제(톨루엔/자일렌)", "이소시아네이트", "요10종", "LFT(간기능)", "CBC(혈액)"],
        "수장": ["유기용제(접착제)", "소음", "요10종", "LFT(간기능)", "청력검사"],
        "내장": ["유기용제(접착제)", "소음", "요10종", "LFT(간기능)", "청력검사"],
        "미장": ["시멘트분진", "산화규소(결정체)", "흉부X-ray", "PFT(폐활량)"],
        "조적": ["시멘트분진", "산화규소(결정체)", "소음", "흉부X-ray", "PFT(폐활량)", "청력검사"],
        "견출": ["시멘트분진", "산화규소(결정체)", "소음", "흉부X-ray", "PFT(폐활량)", "청력검사"],
        "타일": ["시멘트분진", "산화규소", "유기용제(접착제)", "흉부X-ray", "PFT(폐활량)", "요10종"],
        "방수": ["유기용제", "이소시아네이트", "시멘트분진", "요10종", "LFT(간기능)", "PFT(폐활량)", "흉부X-ray"],
        "용접": ["용접흄", "망간/니켈", "소음", "흉부X-ray", "LFT(간기능)", "CBC(혈액)", "요10종", "청력검사"],
        "철근": ["소음", "금속흄", "청력검사", "흉부X-ray"],
        "목공": ["목분진", "소음", "흉부X-ray", "PFT(폐활량)", "청력검사"],
        "형틀": ["소음", "시멘트분진", "청력검사", "흉부X-ray", "PFT(폐활량)"],
        "비계": ["소음", "청력검사"],
        "전기": ["소음", "청력검사"],
        "설비": ["소음", "용접흄", "청력검사", "흉부X-ray"],
        "철거": ["광물성분진", "석면(의심)", "소음", "흉부X-ray", "PFT(폐활량)", "청력검사"],
        "야간": ["야간작업", "심혈관계문진", "혈당/콜레스테롤"]
    }

    # 입력값에 따른 매칭
    for job_key, res_list in job_db.items():
        if job_key in content:
            detected_hazards.append(job_key)
            items.extend(res_list)

    # 개별 유해물질 매칭 (기존 로직 유지)
    material_db = {
        "벤젠": ["요10종", "LFT", "CBC정밀"], "납": ["요10종", "CBC일반", "혈중연농도"],
        "소음": ["청력검사"], "분진": ["흉부X-ray", "PFT"]
    }
    for mat, vals in material_db.items():
        if mat in content:
            detected_hazards.append(mat)
            items.extend(vals)
    
    if is_outdoor: items.append("시력검사(자외선)")
    if is_vibration: items.extend(["악력검사", "통각검사"])
    
    return list(set(items)), list(set(detected_hazards))

# --- 5. 결과 표시 (카드 내부 삽입) ---
raw_text = ""
if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        raw_text = "".join([p.extract_text() for p in pdf.pages if p.extract_text()])

final_items, detected = run_analysis(raw_text, search_input)

res_l, res_r = st.columns(2)

with res_l:
    card_html = '<div class="info-card"><div class="card-title">분석된 유해인자 <span class="card-badge">직종/물질</span></div><div class="result-content">'
    if not (search_input or uploaded_file or is_outdoor or is_vibration):
        card_html += '<p style="color:#94A3B8;">분석할 데이터를 입력하세요.</p>'
    else:
        results = []
        if detected: results.extend(detected)
        if is_outdoor: results.append("실외작업")
        if is_vibration: results.append("진동작업")
        card_html += f"분석 결과: <span class='material-highlight'>{', '.join(results) if results else '수기 데이터'}</span><br><br>"
        card_html += "※ 해당 직종의 주요 노출 인자를 바탕으로 구성되었습니다."
    card_html += '</div></div>'
    st.markdown(card_html, unsafe_allow_html=True)

with res_r:
    card_html = '<div class="info-card"><div class="card-title">권장 검사항목 <span class="card-badge">별표24 기준</span></div><div class="result-content">'
    if not final_items or not (search_input or uploaded_file or is_outdoor or is_vibration):
        card_html += '<p style="color:#94A3B8;">표시할 항목이 없습니다.</p>'
    else:
        for item in sorted(final_items):
            card_html += f'<div class="check-item">✅ {item}</div>'
    card_html += '</div></div>'
    st.markdown(card_html, unsafe_allow_html=True)

st.markdown('<div class="footer">HCMS Health Management Support System | Made by 전형철 with Gemini 2026</div>', unsafe_allow_html=True)