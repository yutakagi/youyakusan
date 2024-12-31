import streamlit as st
import whisper
import os
import subprocess
from pathlib import Path

## 一時保存フォルダ
UPLOAD_FOLDER = "uploads"
## exist_ok=Trueを指定することで、フォルダが既に存在してもエラーが発生しません。
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

st.title("動画からテキスト変換アプリ")
st.write("動画ファイルをアップロードしてください。音声を抽出してテキストに変換します。")

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
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

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

# 結果を表示
st.subheader("変換結果")
st.text_area("テキスト", text, height=300)

# テキストダウンロード
st.download_button(
    label="テキストをダウンロード",
    data=text,
    file_name="transcription.txt",
    mime="text/plain"
)

os.remove(video_path)
os.remove(audio_path)