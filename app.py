import streamlit as st
import pdfplumber
import os
import pandas as pd
from pathlib import Path

# --- 설정 및 UI 스타일 (모바일 & GPT-Mix 스타일) ---
st.set_page_config(page_title="HCMS 분석 시스템", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto+Sans+KR', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    
    /* 모바일 가로폭 최적화 */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* 헤더 디자인 */
    .main-header { 
        background: white; padding: 15px; border-radius: 12px; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 15px; 
        text-align: center; border-top: 4px solid #004A7C; 
    }
    .main-title { color: #004A7C; font-size: 1.3rem; font-weight: 800; margin: 0; }
    .sub-title { color: #64748B; font-size: 0.85rem; margin-top: 3px; font-weight: 600; }
    .quote-text { font-size: 0.7rem; color: #94A3B8; margin-top: 8px; font-style: italic; }
    
    /* 모바일 토글 스위치 폰트 잘림 방지 */
    div[data-testid="stMarkdownContainer"] p { font-size: 13px !important; font-weight: 600; }
    
    /* 결과 카드 디자인 (사이즈 축소) */
    .info-card { 
        background: white; padding: 12px; border-radius: 10px; 
        box-shadow: 0 1px 5px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; 
        margin-bottom: 10px; min-height: 80px;
    }
    .card-title { 
        font-size: 11px; font-weight: 700; color: #475569; 
        border-bottom: 1px solid #F1F5F9; padding-bottom: 4px; margin-bottom: 8px; 
    }
    .result-text { font-size: 12.5px; color: #1E293B; line-height: 1.5; }
    .check-item { 
        font-size: 12px; font-weight: 600; color: #0F172A; 
        margin-bottom: 4px; padding: 4px 8px; background: #F1F5F9; border-radius: 5px;
    }
    
    /* 하단 제작자 문구 (샤인골드 & 20% 업) */
    .footer { 
        text-align: right; font-size: 14.5px; font-weight: 700; 
        color: #D4AF37; margin-top: 20px; padding-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 로직: 데이터베이스 ---
# 건설 직종별 DB
JOB_DB = {
    "도장": ["유기용제(톨루엔/자일렌)", "요10종", "LFT(간기능)", "CBC(일반)"],
    "수장": ["유기용제(접착제)", "소음", "요10종", "순음청력검사"],
    "미장": ["시멘트분진", "결정형산화규소", "흉부X-ray", "PFT(폐기능)"],
    "방수": ["유기용제(에폭시)", "이소시아네이트", "요10종", "LFT(간기능)"],
    "용접": ["용접흄", "망간", "소음", "흉부X-ray", "순음청력검사", "EKG(심전도)"],
    "철근": ["소음", "진동", "순음청력검사", "악력검사"],
    "비계": ["소음", "분진", "순음청력검사", "흉부X-ray"]
}

# 물질별 DB (CAS 기반 매핑용)
AGENT_DB = {
    "메탄올": ["노출지표(소변)", "요10종", "LFT(간기능)", "시력검사"],
    "벤젠": ["CBC(정밀)", "요10종", "LFT(간기능)", "혈액검사"],
    "톨루엔": ["노출지표(소변)", "요10종", "LFT(간기능)"],
    "소음": ["순음청력검사", "이비인후과진찰"],
    "분진": ["흉부X-ray", "PFT(폐기능)"],
    "자외선": ["시력검사"],
    "2-부톡시에탄올": ["요10종", "CBC(일반)", "LFT(간기능)"]
}

def analyze_data(text, query, pre, vib, out):
    # 기초검사는 항상 포함
    items = ["신장", "체중", "혈압(기초)"]
    detected = []
    content = (text + " " + query).lower()
    
    # 1. 직종/물질 분석
    for k, v in JOB_DB.items():
        if k in content: 
            detected.append(k)
            items.extend(v)
    for k, v in AGENT_DB.items():
        if k in content: 
            detected.append(k)
            items.extend(v)
    
    # 2. 옵션 처리
    if out: 
        detected.append("실외작업")
        items.append("시력검사")
    if vib:
        detected.append("진동기계")
        items.extend(["악력검사", "통각검사"])
        
    # 3. 배치전/후 소음 검사 구간 분리
    final_items = []
    for item in set(items):
        if "순음청력" in item:
            if pre: final_items.append("순음청력(500Hz~6000Hz)")
            else: final_items.append("순음청력(2000,3000,4000Hz)")
        else:
            final_items.append(item)
            
    return sorted(final_items), list(set(detected))

# --- 화면 구성 ---
# 상단 타이틀
st.markdown("""
    <div class="main-header">
        <p class="main-title">물질안전보건자료(MSDS) 분석시스템</p>
        <p class="sub-title">MSDS 검진항목 자동안내 시스템</p>
        <div class="quote-text">"내가 너희를 편하게 할지니 너만 잘났다고 자만하지 말지어다. By Doksa"</div>
    </div>
""", unsafe_allow_html=True)

# 로고 이미지
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

# 입력 섹션
with st.container():
    uploaded_file = st.file_uploader("📂 MSDS PDF 업로드", type="pdf")
    search_query = st.text_input("🔍 수기 검색 (직종 또는 물질명)", placeholder="ex. 도장공, 메탄올, 소음...")
    
    # 모바일에서 글자가 잘리지 않도록 컬럼 배치
    t1, t2, t3 = st.columns(3)
    with t1: is_pre = st.toggle("배치전", value=True)
    with t2: is_vib = st.toggle("진동", value=False)
    with t3: is_out = st.toggle("실외", value=False)

# 분석 실행
raw_text = ""
if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        raw_text = " ".join([p.extract_text() for p in pdf.pages if p.extract_text()])

res_items, res_hazards = analyze_data(raw_text, search_query, is_pre, is_vib, is_out)

st.markdown("---")

# 결과 출력 (모바일 최적화 레이아웃)
c_left, c_right = st.columns([1, 1])

with c_left:
    st.markdown(f"""
        <div class="info-card">
            <div class="card-title">⚠️ 유해인자 정보</div>
            <div class="result-text"><b>{", ".join(res_hazards) if res_hazards else "미검출"}</b></div>
        </div>
    """, unsafe_allow_html=True)

with c_right:
    items_html = "".join([f'<div class="check-item">✅ {i}</div>' for i in res_items])
    st.markdown(f"""
        <div class="info-card">
            <div class="card-title">🩺 권장 검사항목</div>
            <div class="result-text">{items_html}</div>
        </div>
    """, unsafe_allow_html=True)

# 하단 푸터
st.markdown('<div class="footer">Made by 전형철 with Python & Google</div>', unsafe_allow_html=True)
