import streamlit as st
import google.generativeai as genai
import yt_dlp
import os
import time
import json
import re

# --- [Page Configuration] ---
st.set_page_config(page_title="Shika's Youtube Converter", page_icon="🎬")

st.title("🎬 Shika's Youtube Converter")
st.markdown("Generates Blog/Twitter content instantly.")

# --- [Sidebar] ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.markdown("[Get API Key](https://aistudio.google.com/app/apikey)")
    target_lang = st.selectbox("Output Language", ["Korean", "English", "Japanese", "Spanish"])

# --- [Helper: Video ID Extractor] ---
def extract_video_id(url):
    """Extracts the video ID from various YouTube URL formats."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

# --- [Core: Invidious Proxy Fetcher] ---
def get_transcript_via_proxy(video_id):
    """
    Fetches captions using Invidious instances (Public Proxies).
    Tries multiple servers in case one is down.
    """
    # List of public Invidious instances
    instances = [
        "https://inv.tux.pizza",
        "https://vid.puffyan.us",
        "https://invidious.projectsegfau.lt",
        "https://inv.us.projectsegfau.lt",
        "https://invidious.fdn.fr"
    ]
    
    print(f"Target Video ID: {video_id}")
    
    for instance in instances:
        try:
            print(f"Trying proxy: {instance}...")
            # 1. Get Video Info (to find caption tracks)
            info_url = f"{instance}/api/v1/videos/{video_id}"
            response = requests.get(info_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                captions = data.get("captions", [])
                
                # 2. Find the best caption (Korean -> English -> Auto)
                selected_caption = None
                
                # Priority 1: Korean
                for cap in captions:
                    if cap["language"] == "Korean" or cap["code"] == "ko":
                        selected_caption = cap
                        break
                
                # Priority 2: English (if no Korean)
                if not selected_caption:
                    for cap in captions:
                        if cap["language"] == "English" or cap["code"] == "en":
                            selected_caption = cap
                            break
                
                # Priority 3: First available (Auto-generated)
                if not selected_caption and captions:
                    selected_caption = captions[0]
                
                if selected_caption:
                    # 3. Download the actual text (VTT/JSON)
                    # The URL in Invidious API is usually relative, so we append domain
                    cap_url = instance + selected_caption["url"]
                    cap_res = requests.get(cap_url)
                    
                    if cap_res.status_code == 200:
                        return cap_res.text  # Return the raw caption text
        except Exception as e:
            print(f"Failed with {instance}: {e}")
            continue # Try next instance
            
    return None

# --- [Gemini Analysis] ---
def analyze_text(text_data, api_key, lang):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Analyze the following YouTube transcript (VTT/JSON format) and create:
    1. [Blog Post] Title, Intro, Body, Conclusion.
    2. [Twitter Thread] 3-5 tweets.
    3. [Fact Check] Key numbers/facts.
    
    Target Language: {lang}
    
    [Transcript Data]:
    {text_data[:80000]}
    """
    return model.generate_content(prompt).text

# --- [Main UI] ---
url = st.text_input("🔗 Enter YouTube URL")
btn = st.button("Generate Content")

if btn:
    if not api_key:
        st.error("🔑 API Key Required")
    elif not url:
        st.error("⚠️ Enter a URL")
    else:
        video_id = extract_video_id(url)
        if not video_id:
            st.error("❌ Invalid URL")
        else:
            status = st.empty()
            status.text("🚀 Connecting to Proxy Server...")
            
            # 1. Fetch via Proxy
            transcript_text = get_transcript_via_proxy(video_id)
            
            if transcript_text:
                status.text("✅ Transcript found! Analyzing with Gemini...")
                try:
                    # 2. Analyze
                    result = analyze_text(transcript_text, api_key, target_lang)
                    status.empty()
                    st.success("Success!")
                    st.markdown(result)
                except Exception as e:
                    st.error(f"Gemini Error: {e}")
            else:
                st.error("❌ Failed to fetch transcript. The video might not have captions, or all proxies are busy.")