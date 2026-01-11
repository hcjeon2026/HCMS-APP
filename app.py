import streamlit as st
import pdfplumber
import os
import pandas as pd
from pathlib import Path

# --- 설정 및 UI 스타일 (가독성 강화 버전) ---
st.set_page_config(page_title="HCMS 분석 시스템", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto+Sans+KR', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    
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
    
    /* ⭐ 토글스위치 텍스트 가독성 핵심 수정 ⭐ */
    div[data-testid="stMarkdownContainer"] p { 
        font-size: 13.5px !important; 
        font-weight: 700 !important; 
        color: #1E293B !important;
        background-color: #E2E8F0; /* 연한 회색 배경색 추가 */
        padding: 2px 6px;
        border-radius: 4px;
        display: inline-block;
        white-space: nowrap;
    }
    
    /* 결과 카드 디자인 */
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
    
    .footer { 
        text-align: right; font-size: 14.5px; font-weight: 700; 
        color: #D4AF37; margin-top: 20px; padding-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터베이스 (기존 동일) ---
JOB_DB = {
    "도장": ["유기용제(톨루엔/자일렌)", "요10종", "LFT(간기능)", "CBC(일반)"],
    "수장": ["유기용제(접착제)", "소음", "요10종", "순음청력검사"],
    "미장": ["시멘트분진", "결정형산화규소", "흉부X-ray", "PFT(폐기능)"],
    "방수": ["유기용제(에폭시)", "이소시아네이트", "요10종", "LFT(간기능)"],
    "용접": ["용접흄", "망간", "소음", "흉부X-ray", "순음청력검사", "EKG(심전도)"]
}

AGENT_DB = {
    "메탄올": ["노출지표(소변)", "요10종", "LFT(간기능)", "시력검사"],
    "벤젠": ["CBC(정밀)", "요10종", "LFT(간기능)", "혈액검사"],
    "소음": ["순음청력검사", "이비인후과진찰"],
    "분진": ["흉부X-ray", "PFT(폐기능)"],
    "자외선": ["시력검사"]
}

def analyze_data(text, query, pre, vib, out):
    items = ["신장", "체중", "혈압"]
    detected = []
    content = (text + " " + query).lower()
    
    for k, v in JOB_DB.items():
        if k in content: detected.append(k); items.extend(v)
    for k, v in AGENT_DB.items():
        if k in content: detected.append(k); items.extend(v)
    
    if out: items.append("시력검사(자외선)"); detected.append("실외작업")
    if vib: items.extend(["악력검사", "통각검사"]); detected.append("진동기계")
    
    final_items = []
    for item in set(items):
        if "순음청력" in item:
            final_items.append(f"순음청력({'500~6000Hz' if pre else '2,3,4kHz'})")
        else: final_items.append(item)
            
    return sorted(final_items), list(set(detected))

# --- 화면 구성 ---
st.markdown('<div class="main-header"><p class="main-title">MSDS 분석시스템</p><p class="sub-title">MSDS 검진항목 자동안내 시스템</p></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"): st.image("logo.png")

# 입력 섹션
with st.container():
    uploaded_file = st.file_uploader("📂 MSDS PDF 업로드", type="pdf")
    search_query = st.text_input("🔍 수기 검색", placeholder="ex. 도장공, 메탄올...")
    
    # 폰트 배경색이 적용된 토글 영역
    t1, t2, t3 = st.columns(3)
    with t1: is_pre = st.toggle("배치전", value=True)
    with t2: is_vib = st.toggle("진동", value=False)
    with t3: is_out = st.toggle("실외", value=False)

raw_text = ""
if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        raw_text = " ".join([p.extract_text() for p in pdf.pages if p.extract_text()])

res_items, res_hazards = analyze_data(raw_text, search_query, is_pre, is_vib, is_out)

st.markdown("---")
c_l, c_r = st.columns(2)

with c_l:
    st.markdown(f'<div class="info-card"><div class="card-title">⚠️ 유해인자</div><div class="result-text">{", ".join(res_hazards) if res_hazards else "검색결과 없음"}</div></div>', unsafe_allow_html=True)

with c_r:
    items_html = "".join([f'<div class="check-item">✅ {i}</div>' for i in res_items])
    st.markdown(f'<div class="info-card"><div class="card-title">🩺 검사항목</div><div class="result-text">{items_html}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="footer">Made by 전형철 with Python & Google</div>', unsafe_allow_html=True)

