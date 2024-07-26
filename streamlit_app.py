import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

def japanese_era_to_ad(year_string):
    era_to_ad = {
        '令和': 2018,
        '平成': 1988,
        '昭和': 1925,
        '大正': 1911,
        '明治': 1867
    }
    for era, start_year in era_to_ad.items():
        if era in year_string:
            year = int(year_string.replace(era, '').strip())
            return start_year + year
    return None

def parse_japanese_date(date_string):
    pattern = r'(令和|平成|昭和|大正|明治)\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日'
    match = re.search(pattern, date_string)
    if match:
        era, year, month, day = match.groups()
        year = japanese_era_to_ad(f"{era}{year}")
        if year:
            return datetime(year, int(month), int(day))
    return None

def extract_latest_directors(text):
    lines = text.split('\n')
    director_pattern = r'(代表)?取締役\s*(.+)'
    date_pattern = r'(令和|平成|昭和|大正|明治)\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日(.*?登記)?'
    
    # 最新の登記日を見つける
    latest_registration_date = None
    for line in lines:
        date_match = re.search(date_pattern, line)
        if date_match and '登記' in date_match.group():
            date = parse_japanese_date(date_match.group())
            if date and (latest_registration_date is None or date > latest_registration_date):
                latest_registration_date = date

    if latest_registration_date is None:
        return []

    # 最新の登記日に関連する取締役情報を抽出
    directors = []
    for i, line in enumerate(lines):
        director_match = re.search(director_pattern, line)
        if director_match:
            role = '代表取締役' if director_match.group(1) else '取締役'
            name = director_match.group(2).strip()
            
            # 次の数行を確認して日付情報を探す
            for j in range(i+1, min(i+5, len(lines))):
                date_match = re.search(date_pattern, lines[j])
                if date_match:
                    date = parse_japanese_date(date_match.group())
                    if date and date == latest_registration_date:
                        directors.append({
                            'name': name,
                            'role': role,
                            'appointment_date': date_match.group()
                        })
                    break

    return directors

def analyze_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    
    directors = extract_latest_directors(text)
    
    df = pd.DataFrame(directors)
    return df, text

def dataframe_to_markdown(df):
    if df.empty:
        return "取締役情報が見つかりませんでした。"
    
    markdown = "| " + " | ".join(df.columns) + " |\n"
    markdown += "| " + " | ".join(["---" for _ in df.columns]) + " |\n"
    
    for _, row in df.iterrows():
        markdown += "| " + " | ".join(str(cell) for cell in row) + " |\n"
    
    return markdown

def generate_report(df):
    report = f"""
# 取締役会構成分析

## 1. データソース

分析に使用したデータは、アップロードされたPDFファイルの登記簿謄本（全部事項）です。

## 2. 最新の取締役一覧

{dataframe_to_markdown(df)}

## 3. 取締役会の構成

1. 取締役数：{len(df)}名
2. 代表取締役：{'あり' if any(df['role'] == '代表取締役') else 'なし'}

## 4. 法的観点

1. 取締役の員数：
   - 会社法上、取締役会設置会社では3名以上の取締役が必要
   - 現在の取締役数（{len(df)}名）は、{'この要件を満たしています' if len(df) >= 3 else 'この要件を満たしていません'}

2. 代表取締役：
   - 会社法上、取締役会設置会社では代表取締役を選定する必要があります
   - {'代表取締役が選定されています' if any(df['role'] == '代表取締役') else '代表取締役の選定が確認できません'}

## 5. 注意事項

この分析は、アップロードされたPDFファイルの最新の登記情報に基づいています。
    """
    return report

st.title('登記簿謄本分析アプリ')

uploaded_file = st.file_uploader("登記簿謄本（全部事項）のPDFをアップロードしてください", type="pdf")

if uploaded_file is not None:
    df, extracted_text = analyze_pdf(uploaded_file)
    if not df.empty:
        report = generate_report(df)
        st.markdown(report)
    else:
        st.error("PDFから最新の取締役情報を抽出できませんでした。PDFの内容を確認してください。")
        st.subheader("抽出されたテキスト（デバッグ用）")
        st.text(extracted_text)
