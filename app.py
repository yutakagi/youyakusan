import streamlit as st
import whisper
import os
import subprocess
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3


# user_idの仮置き（認証を入れるまで）
user_id = "みさと"

# # OpenAIクライアントのインスタンスを作成
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# システムメッセージで指示を設定
instructions = "あなたは「みさとん」です。「私はみさとん。ぼちぼち要約しますさかいに〜」といって、コテコテの関西弁で内容を要約してください"


## 一時保存フォルダ
UPLOAD_FOLDER = "uploads"
## exist_ok=Trueを指定することで、フォルダが既に存在してもエラーが発生しません。
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

st.title("動画ヨウヤクさん")
st.write("動画ファイルをアップロードしてください。音声を抽出してテキストに変換します。")

## 履歴のリセット
if st.button("履歴をリセット"):
    try:
        conn = sqlite3.connect("summaries.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM summaries")
        conn.commit()
        conn.close()
        st.success("履歴が正常にリセットされました")
    except Exception as e:
        st.error(f"予期しないエラーが発生しました。{e}")


## ファイルアップロード機能
uploaded_file = st.file_uploader("動画をアップロード", type=["mp4", "avi", "mov", "mkv"])

## ffmpegで動画ファイルから音声データを抽出する関数
def extract_audio(video_path, output_audio_path):
    command = [
        "ffmpeg",
        "-y",
        "-i", video_path,      # 入力ファイル
        "-q:a", "0",           # 音声品質を最高に設定
        "-map", "a",           # 音声ストリームのみを抽出
        output_audio_path      # 出力ファイルパス
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,check=True)
    if result.returncode != 0:
        error_message = result.stderr.decode()
        st.error(f"ffmpeg エラー: {error_message}")
        raise subprocess.CalledProcessError(result.returncode, command)

## whisperで音声データをテキストに変換する関数
def transcribe_audio(audio_path):
    model = whisper.load_model("small")
    result = model.transcribe(audio_path)
    return result["text"]

## video_path初期化
video_path = None

# データベース接続
conn = sqlite3.connect('summaries.db')
cursor = conn.cursor()
# テーブル作成
cursor.execute('''
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY,
        user_id TEXT,
        upload_time TIMESTAMP,
        file_name TEXT,
        summary TEXT
    )
''')
conn.commit()
conn.close()

## ファイルアップロード後の処理
if uploaded_file is not None:
    # ファイルを一時保存
    video_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("動画ファイルのアップロードが完了しました。")
    # 音声抽出
    audio_path = os.path.splitext(video_path)[0] + ".wav"
    extract_audio(video_path, audio_path)
    st.info("音声の抽出が完了しました。")

    # テキスト変換
    with st.spinner("音声をテキストに変換中..."):
        text = transcribe_audio(audio_path)
    st.success("テキスト変換が完了しました。")

    # ChatGPT APIにリクエストを送信
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": text}
            ]
        )
    # 結果を表示
    st.subheader("ヨウヤクすると...")
    st.text_area("テキスト", completion.choices[0].message.content, height=300)

    # テキストダウンロード
    st.download_button(
        label="テキストをダウンロード",
        data=text,
        file_name="transcription.txt",
        mime="text/plain"
    )
    # データベース接続
    conn = sqlite3.connect('summaries.db')
    cursor = conn.cursor()

    # テーブル作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            upload_time TIMESTAMP,
            file_name TEXT,
            summary TEXT
        )
    ''')
    conn.commit()



    cursor.execute('''
        INSERT OR IGNORE INTO summaries (user_id, upload_time, file_name, summary)
        VALUES (?, datetime('now'), ?, ?)
    ''', (user_id, uploaded_file.name, completion.choices[0].message.content))
    conn.commit()
    conn.close()

    os.remove(video_path)
    os.remove(audio_path)
else:
    st.warning("動画ファイルをアップロードしてください")

## 履歴の取得と表示
conn = sqlite3.connect('summaries.db')
cursor = conn.cursor()
cursor.execute('SELECT upload_time, file_name, summary FROM summaries WHERE user_id = ?', (user_id,))
records = cursor.fetchall()

for record in records:
    st.expander(f"{record[0]} - {record[1]}").write(record[2])
