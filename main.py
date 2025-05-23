# main.py - نقطه ورود اصلی برنامه با رابط کاربری Streamlit و قابلیت صوتی

import os
import sys
import json
import streamlit as st
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
import time
import base64

# اضافه کردن مسیر پروژه به sys.path برای import ماژول‌ها
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.conversation import NegotiationSession, SessionPhase
from core.audio_manager import AudioManager

# تنظیمات صفحه
st.set_page_config(
    page_title="کارگاه مذاکره جذب سرمایه",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# استایل‌های CSS سفارشی
st.markdown("""
<style>
    .agent-message {
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .conservative {
        background-color: #e3f2fd;
        border-left: 5px solid #1976d2;
    }
    .risky {
        background-color: #e8f5e9;
        border-left: 5px solid #388e3c;
    }
    .competitor {
        background-color: #ffebee;
        border-left: 5px solid #d32f2f;
    }
    .evaluator {
        background-color: #fff3e0;
        border-left: 5px solid #f57c00;
    }
    .system {
        background-color: #f5f5f5;
        border-left: 5px solid #757575;
    }
    .user-message {
        background-color: #f0f4f8;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 5px solid #2196f3;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .phase-indicator {
        text-align: center;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .audio-container {
        margin: 10px 0;
        padding: 5px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


class StreamlitNegotiationApp:
    """اپلیکیشن مذاکره با رابط کاربری Streamlit و قابلیت صوتی"""

    def __init__(self):
        # بارگذاری متغیرهای محیطی
        load_dotenv()

        # مدیر صوتی
        self.audio_manager = AudioManager()

        # تنظیمات اولیه session state
        if 'session' not in st.session_state:
            st.session_state.session = None
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'api_key' not in st.session_state:
            st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
        if 'session_active' not in st.session_state:
            st.session_state.session_active = False
        if 'final_report' not in st.session_state:
            st.session_state.final_report = None
        if 'voice_mode' not in st.session_state:
            st.session_state.voice_mode = False
        if 'last_audio' not in st.session_state:
            st.session_state.last_audio = None
        if 'audio_autoplay' not in st.session_state:
            st.session_state.audio_autoplay = True

        # ایجاد پوشه گزارشات
        self.report_dir = "reports"
        os.makedirs(self.report_dir, exist_ok=True)

    def render_sidebar(self):
        """رندر کردن سایدبار"""
        with st.sidebar:
            st.title("⚙️ تنظیمات")

            # تنظیم API Key
            api_key = st.text_input(
                "OpenAI API Key",
                value=st.session_state.api_key,
                type="password"
            )

            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key
                st.success("API Key ذخیره شد")

            st.divider()

            # فعال/غیرفعال کردن حالت صوتی
            st.session_state.voice_mode = st.checkbox(
                "فعال کردن پشتیبانی صوتی", 
                value=st.session_state.voice_mode
            )

            if st.session_state.voice_mode:
                st.session_state.audio_autoplay = st.checkbox(
                    "پخش خودکار پاسخ‌های صوتی", 
                    value=st.session_state.audio_autoplay
                )

            st.divider()

            # دکمه شروع/پایان جلسه
            if not st.session_state.session_active:
                if st.button("🚀 شروع جلسه جدید", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("لطفا ابتدا API Key را وارد کنید")
                    else:
                        self.start_new_session()
            else:
                if st.button("🛑 پایان جلسه", use_container_width=True):
                    self.end_session()

            st.divider()

            # نمایش وضعیت جلسه
            if st.session_state.session_active and st.session_state.session:
                st.subheader("📊 وضعیت جلسه")
                phase_colors = {
                    SessionPhase.INTRODUCTION: "#bbdefb",
                    SessionPhase.FINANCIAL_QUESTIONS: "#c8e6c9",
                    SessionPhase.COMPETITIVE_CHALLENGE: "#ffcdd2",
                    SessionPhase.FINAL_NEGOTIATION: "#ffe0b2",
                    SessionPhase.COMPLETED: "#f5f5f5"
                }
                current_phase = st.session_state.session.conversation_manager.current_phase
                st.markdown(
                    f"""<div class="phase-indicator" style="background-color: {phase_colors[current_phase]}">
                    مرحله فعلی: {current_phase.value}
                    </div>""",
                    unsafe_allow_html=True
                )

                # نمایش زمان سپری شده
                elapsed_time = time.time() - st.session_state.session.conversation_manager.session_start_time
                st.metric("زمان سپری شده", f"{elapsed_time:.0f} ثانیه")

                # نمایش میله پیشرفت
                progress = min(elapsed_time / 600, 1.0)  # 10 دقیقه کل
                st.progress(progress)

    def start_new_session(self):
        """شروع جلسه جدید"""
        try:
            st.session_state.session = NegotiationSession(st.session_state.api_key)
            st.session_state.session_active = True
            st.session_state.messages = []
            st.session_state.final_report = None
            st.session_state.last_audio = None
            
            # پاک کردن صف صوتی
            self.audio_manager.clear_audio_queue()

            # پیام خوش‌آمدگویی
            welcome_msg = st.session_state.session.start_session()
            st.session_state.messages.append({
                "agent": "system",
                "message": welcome_msg,
                "timestamp": time.time()
            })

            st.success("جلسه جدید شروع شد!")
            st.rerun()

        except Exception as e:
            st.error(f"خطا در شروع جلسه: {str(e)}")

    def end_session(self):
        """پایان جلسه و تولید گزارش"""
        if st.session_state.session:
            try:
                st.session_state.final_report = st.session_state.session.get_final_report()
                st.session_state.session_active = False
                self.save_report(st.session_state.final_report)
                self.audio_manager.clear_audio_queue()
                st.success("جلسه به پایان رسید. گزارش ذخیره شد.")
                st.rerun()
            except Exception as e:
                st.error(f"خطا در پایان جلسه: {str(e)}")

    def save_report(self, report: Dict):
        """ذخیره گزارش جلسه"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ذخیره گزارش JSON
        json_path = os.path.join(self.report_dir, f"report_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # ذخیره گزارش متنی
        text_path = os.path.join(self.report_dir, f"report_{timestamp}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(st.session_state.session.export_report("text"))

        return json_path, text_path

    def render_message(self, message: Dict):
        """رندر کردن یک پیام"""
        agent = message.get("agent", "")
        content = message.get("message", "")
        role = message.get("role", "")

        # تعیین کلاس CSS بر اساس نقش
        css_class = "agent-message "
        icon = ""

        if role == "conservative_investor":
            css_class += "conservative"
            icon = "👔"
        elif role == "risky_investor":
            css_class += "risky"
            icon = "🚀"
        elif role == "competitor":
            css_class += "competitor"
            icon = "⚔️"
        elif role == "evaluator" or message.get("type") == "evaluation":
            css_class += "evaluator"
            icon = "💡"
        elif agent == "system":
            css_class += "system"
            icon = "ℹ️"
        else:
            css_class = "user-message"
            icon = "👤"

        # نمایش پیام
        st.markdown(
            f"""<div class="{css_class}">
            <strong>{icon} {agent}:</strong> {content}
            </div>""",
            unsafe_allow_html=True
        )

        # اگر حالت صوتی فعال است و پیام از عوامل است، صدا را به صف اضافه کنید
        if st.session_state.voice_mode and agent != "شما" and agent != "system":
            self.audio_manager.enqueue_audio(agent, content)

    def render_chat_interface(self):
        """رندر کردن رابط چت"""
        # نمایش پیام‌ها
        for message in st.session_state.messages:
            self.render_message(message)

        # اگر حالت صوتی فعال است، پخش کننده صوتی را نمایش دهید
        if st.session_state.voice_mode:
            self.audio_manager.render_audio_player()

        # ورودی کاربر - متنی یا صوتی
        if st.session_state.session_active:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                user_input = st.chat_input("پیام خود را وارد کنید...")
            
            with col2:
                if st.session_state.voice_mode:
                    recorded_audio = st.audio_input("ضبط صدا")
                else:
                    recorded_audio = None

            # پردازش ورودی متنی
            if user_input:
                self.process_user_input(user_input)

            # پردازش ورودی صوتی
            if recorded_audio and recorded_audio != st.session_state.last_audio:
                with st.spinner("در حال پردازش صدا..."):
                    st.session_state.last_audio = recorded_audio
                    audio_bytes = recorded_audio.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    
                    # نمایش پیام برای دیباگ
                    st.info("در حال ارسال صدا برای تبدیل به متن...")
                    
                    transcribed_text = self.audio_manager.speech_to_text(audio_base64)
                    if transcribed_text:
                        # Get result from the transcribed data structure
                        text_result = transcribed_text.get("result", "")
                        if text_result:
                            st.info(f"متن تشخیص داده شده: {text_result}")
                            self.process_user_input(text_result)
                        else:
                            st.error("متنی تشخیص داده نشد. لطفا دوباره تلاش کنید.")
                    else:
                        st.error("خطا در تشخیص گفتار. لطفا دوباره تلاش کنید یا از ورودی متنی استفاده نمایید.")

    def process_user_input(self, user_input: str):
        """پردازش ورودی کاربر"""
        # افزودن پیام کاربر
        st.session_state.messages.append({
            "agent": "شما",
            "message": user_input,
            "timestamp": time.time()
        })

        # پردازش پاسخ
        try:
            responses = st.session_state.session.process_input(user_input)

            # افزودن پاسخ‌های عوامل
            for response in responses:
                st.session_state.messages.append(response)

            # بررسی پایان جلسه
            if not st.session_state.session.is_session_active():
                self.end_session()

            st.rerun()

        except Exception as e:
            st.error(f"خطا در پردازش پیام: {str(e)}")

    def render_final_report(self):
        """نمایش گزارش نهایی"""
        if st.session_state.final_report:
            report = st.session_state.final_report

            st.header("📊 گزارش نهایی جلسه مذاکره")

            # نتیجه مذاکره
            negotiation = report["negotiation_result"]
            evaluation = report["performance_evaluation"]

            col1, col2, col3 = st.columns(3)

            with col1:
                status = "✅ موفق" if negotiation["deal_closed"] else "❌ ناموفق"
                st.metric("وضعیت مذاکره", status)

            with col2:
                st.metric(
                    "سرمایه جذب شده",
                    f"{negotiation['investment_secured']:,} تومان"
                )

            with col3:
                st.metric(
                    "درصد موفقیت",
                    f"{negotiation['success_rate']:.1f}%"
                )

            st.divider()

            # ارزیابی عملکرد
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 ارزیابی عملکرد")
                st.metric("امتیاز کل", f"{evaluation['total_score']} از 100")
                st.metric("رتبه", evaluation['grade'])

                # نمودار معیارها
                metrics_data = evaluation['metrics']
                st.bar_chart(metrics_data)

            with col2:
                st.subheader("💪 نقاط قوت")
                for strength in evaluation['strengths']:
                    st.success(strength)

                st.subheader("⚠️ نقاط ضعف")
                for weakness in evaluation['weaknesses']:
                    st.warning(weakness)

            st.divider()

            # توصیه‌ها
            st.subheader("📝 توصیه‌های بهبود")
            for recommendation in evaluation['recommendations']:
                st.info(recommendation)

            # دانلود گزارش
            st.divider()
            col1, col2 = st.columns(2)

            with col1:
                json_str = json.dumps(report, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 دانلود گزارش JSON",
                    data=json_str,
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            with col2:
                text_report = st.session_state.session.export_report("text")
                st.download_button(
                    label="📥 دانلود گزارش متنی",
                    data=text_report,
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

    def run(self):
        """اجرای اصلی برنامه"""
        st.title("🤝 کارگاه مذاکره جذب سرمایه")
        st.markdown("---")

        # رندر سایدبار
        self.render_sidebar()

        # نمایش محتوای اصلی
        if st.session_state.session_active:
            self.render_chat_interface()
        elif st.session_state.final_report:
            self.render_final_report()
        else:
            # صفحه خوش‌آمدگویی
            st.markdown("""
            ## خوش آمدید به کارگاه مذاکره جذب سرمایه!

            در این کارگاه تعاملی، شما در نقش بنیان‌گذار یک استارتاپ EdTech قرار می‌گیرید 
            که قصد جذب ۵۰ میلیارد تومان سرمایه دارید.

            ### 👥 افراد حاضر در جلسه:
            1. **آقای محمدی** - سرمایه‌گذار محتاط
            2. **خانم اکبری** - سرمایه‌گذار ریسک‌پذیر
            3. **آقای رضایی** - بنیان‌گذار استارتاپ رقیب
            4. **دکتر کریمی** - ارزیاب مذاکره

            ### ⏱️ مراحل جلسه:
            1. **معرفی** (۲ دقیقه) - معرفی استارتاپ و ایده
            2. **سوالات مالی** (۳ دقیقه) - پاسخ به سوالات مالی و فنی
            3. **چالش رقابتی** (۳ دقیقه) - مواجهه با چالش‌های رقیب
            4. **مذاکره نهایی** (۲ دقیقه) - مذاکره شرایط نهایی

            ### 🎯 هدف:
            - جذب حداکثر سرمایه با حداقل واگذاری سهام
            - کسب امتیاز بالا در ارزیابی عملکرد

            برای شروع، از منوی سمت چپ API Key خود را وارد کرده و دکمه "شروع جلسه جدید" را بزنید.
            """)

            # نمایش تصویر یا انیمیشن
            st.image("https://via.placeholder.com/800x400?text=Negotiation+Workshop", use_container_width=True)


def main():
    """تابع اصلی برای اجرای برنامه"""
    app = StreamlitNegotiationApp()
    app.run()


if __name__ == "__main__":
    main()

