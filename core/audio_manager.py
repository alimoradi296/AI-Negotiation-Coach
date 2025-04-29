# audio_manager.py - مدیریت صدا برای برنامه مذاکره

import os
import requests
import json
import base64
import streamlit as st
from time import time


class AudioManager:
    """مدیریت ورودی و خروجی صوتی"""

    def __init__(self):
        # تنظیمات API
        self.STT_ENDPOINT = os.getenv("STT_ENDPOINT", "https://partai.gw.isahab.ir/speechRecognition/v1/base64")
        self.TTS_ENDPOINT = os.getenv("TTS_ENDPOINT", "https://partai.gw.isahab.ir/TextToSpeech/v1/speech-synthesys")
        self.STT_API_KEY = os.getenv("STT_API_KEY", "Gateway 5c1ea0b8-7dc9-5f36-8f96-c4deff201a1d")
        self.TTS_API_KEY = os.getenv("TTS_API_KEY", "Gateway a7f37b14-d0a1-5b52-a6f0-d0baef9e1b67")
        
        # Speaker settings for different agents
        self.speaker_map = {
            "آقای محمدی": 2,  # Male voice 1
            "خانم اکبری": 0,  # Female voice
            "آقای رضایی": 1,  # Male voice 2
            "دکتر کریمی": 3,  # Male voice 3
            "system": 3        # System voice
        }
        
        # Initialize audio queue
        if 'audio_queue' not in st.session_state:
            st.session_state.audio_queue = []
        if 'current_audio' not in st.session_state:
            st.session_state.current_audio = None
        if 'audio_playing' not in st.session_state:
            st.session_state.audio_playing = False
        if 'last_queue_update' not in st.session_state:
            st.session_state.last_queue_update = time()

    def speech_to_text(self, audio_base64, language="fa"):
        """تبدیل صدا به متن"""
        url = self.STT_ENDPOINT
        payload = json.dumps({"language": language, "data": audio_base64})
        headers = {
            'gateway-token': self.STT_API_KEY,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            result = response.json()
            
            # Debug response
            print("STT Response:", result)
            
            # Parse response based on the provided structure
            if result.get("data", {}).get("status") == "success":
                return result["data"]["data"]
            else:
                st.error("خطا در تبدیل صدا به متن: پاسخ نامعتبر")
                return None
        except Exception as e:
            st.error(f"خطا در درخواست STT: {str(e)}")
            return None

    def text_to_speech(self, text, speaker=3, speed=1):
        """تبدیل متن به صدا"""
        url = self.TTS_ENDPOINT
        payload = json.dumps({
            "data": text, 
            "filePath": "true", 
            "base64": "1", 
            "checksum": "1",
            "speaker": str(speaker), 
            "speed": str(speed)
        })
        headers = {
            'Content-Type': 'application/json', 
            'gateway-token': self.TTS_API_KEY
        }
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            result = response.json()
            
            if result["data"]["status"] == "success":
                file_url = result["data"]["data"].get("filePath")
                if file_url:
                    if not file_url.startswith(('http://', 'https://')):
                        file_url = f"https://{file_url}"
                    audio_response = requests.get(file_url, headers={'gateway-token': self.TTS_API_KEY})
                    audio_response.raise_for_status()
                    return audio_response.content
                else:
                    st.error("No filePath found in TTS response.")
                    return None
            else:
                st.error("TTS API returned unsuccessful status.")
                return None
        except Exception as e:
            st.error(f"خطا در درخواست TTS: {str(e)}")
            return None

    def enqueue_audio(self, agent_name, message_text):
        """افزودن یک فایل صوتی به صف پخش و نمایش کنترل دستی"""
        speaker = self.speaker_map.get(agent_name, 3)
        audio_bytes = self.text_to_speech(message_text, speaker=speaker)
        
        if audio_bytes:
            unique_id = f"audio_{len(st.session_state.audio_queue)}_{time()}"
            audio_item = {
                "id": unique_id,
                "agent": agent_name,
                "data": audio_bytes,
                "played": False
            }
            
            # Add to queue for sequential auto-play
            st.session_state.audio_queue.append(audio_item)
            st.session_state.last_queue_update = time()
            
            # Also display individual audio control
            audio_base64 = base64.b64encode(audio_bytes).decode()
            with st.expander(f"صدای {agent_name}", expanded=False):
                st.audio(audio_bytes, format="audio/mp3")
                
            return True
        return False

    def get_next_audio(self):
        """دریافت بعدی فایل صوتی از صف پخش"""
        if not st.session_state.audio_queue:
            return None
            
        # Find the first unplayed audio
        for i, audio_item in enumerate(st.session_state.audio_queue):
            if not audio_item["played"]:
                st.session_state.audio_queue[i]["played"] = True
                return audio_item
                
        return None

    def render_audio_player(self):
        """نمایش پلیر صوتی برای پخش صف"""
        # First check if we need to update the audio player for auto-play
        if st.session_state.audio_autoplay and not st.session_state.audio_playing and st.session_state.audio_queue:
            next_audio = self.get_next_audio()
            if next_audio:
                audio_bytes = next_audio["data"]
                audio_base64 = base64.b64encode(audio_bytes).decode()
                audio_html = f"""
                    <audio id="{next_audio['id']}" onended="this.parentNode.removeChild(this)" autoplay>
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                        مرورگر شما از پخش صوت پشتیبانی نمی‌کند.
                    </audio>
                    <script>
                        var audio = document.getElementById("{next_audio['id']}");
                        audio.onplay = function() {{ 
                            window.parent.postMessage({{
                                type: "streamlit:setComponentValue",
                                value: true
                            }}, "*");
                        }};
                        audio.onended = function() {{ 
                            window.parent.postMessage({{
                                type: "streamlit:setComponentValue",
                                value: false
                            }}, "*");
                        }};
                    </script>
                """
                st.session_state.audio_container = st.empty()
                st.session_state.audio_container.markdown(audio_html, unsafe_allow_html=True)
                st.session_state.audio_playing = True
                st.session_state.current_audio = next_audio["id"]
            
        # Check if we need to clear the audio container
        if st.session_state.audio_playing and not st.session_state.current_audio:
            st.session_state.audio_container.empty()
            st.session_state.audio_playing = False

    def clear_audio_queue(self):
        """پاک کردن صف صوتی"""
        st.session_state.audio_queue = []
        st.session_state.audio_playing = False
        st.session_state.current_audio = None