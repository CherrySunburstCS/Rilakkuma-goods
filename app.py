import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="リラックマ新商品一覧", page_icon="🧸", layout="wide")

st.title("🧸 リラックマ(Rilakkuma) 最新新商品・イベント一覧表")
st.caption("ボタンを押した【リアルタイムの現在日時】を基準に、最新の公式ニュース・新商品記事を収集します。(APIキー不要・直接リンク)")

# ---------------------------------------------------------
# 2. リアルタイムRSSデータ収集関数 (本物のURL直行)
# ---------------------------------------------------------
def fetch_rilakkuma_goods_rss():
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)
    current_date_str = f"{now.year}年{now.month}月{now.day}日"

    # Google News RSS (リラックマ グッズ 新商品 キーワード)
    query = urllib.parse.quote("リラックマ グッズ OR 新商品 OR 一番くじ OR コラボ")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"

    req = urllib.request.Request(
        rss_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    goods_list = []

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            # RSSの各アイテムを解析
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source = item.find("source").text if item.find("source") is not None else "ニュース記事"

                # 出典元がタイトル末尾にある場合は分離
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source = parts[1]

                # 日付フォーマット変換
                date_str = "-"
                if pub_date:
                    try:
                        # GMT日付パース
                        dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                        date_str = dt.strftime("%Y年%m月%d日")
                    except Exception:
                        date_str = pub_date[:16]

                # カテゴリ簡易判定
                category = "公式・新商品"
                if "一番くじ" in title or "くじ" in title:
                    category = "一番くじ"
                elif "コラボ" in title or "カフェ" in title:
                    category = "コラボ・企画"
                elif "イベント" in title or "ポップアップ" in title:
                    category = "イベント"

                if title and "リラックマ" in title:
                    goods_list.append({
                        "category": category,
                        "title": title,
                        "source": source,
                        "release_date": date_str,
                        "direct_url": link
                    })
    except Exception as e:
        raise Exception(f"データ取得エラー: {e}")

    # サンエックス公式ショップの最新リラックマコーナーも追加
    goods_list.append({
        "category": "公式ショップ",
        "title": "サンエックスネットショップ リラックマ新商品特集コーナー",
        "source": "San-X 公式",
        "release_date": current_date_str,
        "direct_url": "https://shop.san-x.co.jp/character/rilakkuma"
    })

    df = pd.DataFrame(goods_list)
    return df, current_date_str

# ---------------------------------------------------------
# 3. 画面UI構成
# ---------------------------------------------------------
if st.button("🔄 最新新商品・お知らせ情報を一括取得", type="primary"):
    with st.spinner("現在日時を基準に、最新の公式・新商品記事を収集しています..."):
        try:
            df, fetched_date = fetch_rilakkuma_goods_rss()
            df = df.drop_duplicates(subset=["title"])
            st.session_state['goods_data'] = df
            st.session_state['last_updated'] = fetched_date
            st.success(f"【{fetched_date} 基準】最新情報の取得に成功しました！ ({len(df)}件)")
        except Exception as e:
            st.error(f"情報取得中にエラーが発生しました: {e}")

# データ表示部
if 'goods_data' in st.session_state:
    df = st.session_state['goods_data']
    updated_date = st.session_state.get('last_updated', '')

    col1, col2 = st.columns([1, 2])
    with col1:
        categories = ["全体"] + list(df['category'].dropna().unique())
        selected_category = st.selectbox("📌 分類フィルター", categories)
    with col2:
        search_query = st.text_input("🔍 キーワード絞り込み (タイトル・出典)", "")

    filtered_df = df.copy()
    if selected_category != "全体":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if search_query:
        mask = filtered_df['title'].str.contains(search_query, case=False, na=False) | filtered_df['source'].str.contains(search_query, case=False, na=False)
        filtered_df = filtered_df[mask]

    st.subheader(f"📋 最新新商品・記事リスト ({len(filtered_df)}件) - {updated_date} 取得")

    st.dataframe(
        filtered_df,
        column_config={
            "category": st.column_config.TextColumn("分類", width="small"),
            "title": st.column_config.TextColumn("商品・記事タイトル", width="large"),
            "source": st.column_config.TextColumn("メディア / 出典", width="medium"),
            "release_date": st.column_config.TextColumn("掲載日 / 日時", width="small"),
            "direct_url": st.column_config.LinkColumn("詳細直行リンク", display_text="記事ページを開く")
        },
        column_order=["category", "title", "source", "release_date", "direct_url"],
        use_container_width=True,
        hide_index=True
    )

    csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="💾 CSVファイルでダウンロード",
        data=csv_data,
        file_name=f"rilakkuma_goods_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )