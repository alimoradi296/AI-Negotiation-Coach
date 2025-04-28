# conversation.py - مدیریت گفتگو و جلسه مذاکره

from typing import Dict, List, Optional
import time
import json
from datetime import datetime
from enum import Enum
from .agents import (
    Agent, ConservativeInvestor, RiskyInvestor,
    Competitor, Evaluator, AgentRole
)


class SessionPhase(Enum):
    INTRODUCTION = "introduction"
    FINANCIAL_QUESTIONS = "financial_questions"
    COMPETITIVE_CHALLENGE = "competitive_challenge"
    FINAL_NEGOTIATION = "final_negotiation"
    COMPLETED = "completed"


class ConversationManager:
    """مدیریت جلسه مذاکره و هماهنگی بین عوامل"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agents: Dict[AgentRole, Agent] = {}
        self.current_phase = SessionPhase.INTRODUCTION
        self.phase_start_time = time.time()
        self.session_start_time = time.time()
        self.conversation_log: List[Dict] = []
        self.phase_durations = {
            SessionPhase.INTRODUCTION: 120,  # 2 minutes
            SessionPhase.FINANCIAL_QUESTIONS: 180,  # 3 minutes
            SessionPhase.COMPETITIVE_CHALLENGE: 180,  # 3 minutes
            SessionPhase.FINAL_NEGOTIATION: 120,  # 2 minutes
        }
        self.user_profile = {
            "investment_requested": 50_000_000_000,  # 50 میلیارد تومان
            "equity_offered": 30,  # درصد سهام پیشنهادی
            "final_investment": 0,
            "final_equity": 0,
            "deal_closed": False
        }
        self.initialize_agents()

    def initialize_agents(self):
        """ایجاد و مقداردهی اولیه عوامل"""
        self.agents[AgentRole.CONSERVATIVE_INVESTOR] = ConservativeInvestor(self.api_key)
        self.agents[AgentRole.RISKY_INVESTOR] = RiskyInvestor(self.api_key)
        self.agents[AgentRole.COMPETITOR] = Competitor(self.api_key)
        self.agents[AgentRole.EVALUATOR] = Evaluator(self.api_key)

    def get_current_speaker(self) -> AgentRole:
        """تعیین اینکه کدام عامل باید صحبت کند"""
        if self.current_phase == SessionPhase.INTRODUCTION:
            # در مرحله معرفی، ابتدا کاربر صحبت می‌کند
            return None
        elif self.current_phase == SessionPhase.FINANCIAL_QUESTIONS:
            # در مرحله سوالات مالی، سرمایه‌گذار محتاط اولویت دارد
            return AgentRole.CONSERVATIVE_INVESTOR
        elif self.current_phase == SessionPhase.COMPETITIVE_CHALLENGE:
            # در مرحله چالش رقابتی، رقیب صحبت می‌کند
            return AgentRole.COMPETITOR
        elif self.current_phase == SessionPhase.FINAL_NEGOTIATION:
            # در مرحله نهایی، هر دو سرمایه‌گذار مشارکت دارند
            return AgentRole.RISKY_INVESTOR
        return None

    def check_phase_transition(self) -> bool:
        """بررسی و انتقال به مرحله بعدی در صورت نیاز"""
        current_time = time.time()
        elapsed_time = current_time - self.phase_start_time

        if self.current_phase in self.phase_durations:
            if elapsed_time >= self.phase_durations[self.current_phase]:
                return self.transition_to_next_phase()

        return False

    def transition_to_next_phase(self) -> bool:
        """انتقال به مرحله بعدی"""
        phase_order = [
            SessionPhase.INTRODUCTION,
            SessionPhase.FINANCIAL_QUESTIONS,
            SessionPhase.COMPETITIVE_CHALLENGE,
            SessionPhase.FINAL_NEGOTIATION,
            SessionPhase.COMPLETED
        ]

        current_index = phase_order.index(self.current_phase)
        if current_index < len(phase_order) - 1:
            self.current_phase = phase_order[current_index + 1]
            self.phase_start_time = time.time()

            # اعلام تغییر مرحله
            transition_message = self.get_phase_transition_message()
            self.add_system_message(transition_message)
            return True

        return False

    def get_phase_transition_message(self) -> str:
        """پیام انتقال بین مراحل"""
        messages = {
            SessionPhase.FINANCIAL_QUESTIONS: "حالا به بخش سوالات مالی می‌رویم. آقای محمدی، لطفا سوالات خود را مطرح کنید.",
            SessionPhase.COMPETITIVE_CHALLENGE: "اکنون آقای رضایی از استارتاپ رقیب وارد بحث می‌شود.",
            SessionPhase.FINAL_NEGOTIATION: "زمان مذاکره نهایی فرا رسیده است. هر دو سرمایه‌گذار آماده تصمیم‌گیری هستند.",
            SessionPhase.COMPLETED: "جلسه به پایان رسید. در حال آماده‌سازی گزارش نهایی..."
        }
        return messages.get(self.current_phase, "")

    def process_user_input(self, user_message: str) -> List[Dict]:
        """پردازش ورودی کاربر و تولید پاسخ‌های عوامل"""
        responses = []

        # ثبت پیام کاربر
        self.add_user_message(user_message)

        # بررسی انتقال فاز
        if self.check_phase_transition():
            responses.append({
                "agent": "system",
                "message": self.get_phase_transition_message(),
                "timestamp": time.time()
            })

        # دریافت پاسخ از عوامل فعال در این مرحله
        active_agents = self.get_active_agents()

        for agent_role in active_agents:
            agent = self.agents[agent_role]

            # ارسال زمینه به عامل
            context = self.get_agent_context(agent_role)

            # دریافت پاسخ
            response = agent.generate_response(user_message, context)

            responses.append({
                "agent": agent.name,
                "role": agent_role.value,
                "message": response,
                "state": agent.state.value,
                "satisfaction": agent.satisfaction_level,
                "timestamp": time.time()
            })

            # ثبت در لاگ
            self.add_agent_message(agent.name, response)

        # ارزیابی توسط عامل ارزیاب
        if self.current_phase != SessionPhase.COMPLETED:
            evaluator = self.agents[AgentRole.EVALUATOR]
            evaluation = evaluator.evaluate_response(
                user_message,
                {r["agent"]: r["message"] for r in responses}
            )

            if evaluation["feedback"]:
                responses.append({
                    "agent": evaluator.name,
                    "role": "evaluator",
                    "message": evaluation["feedback"],
                    "type": "evaluation",
                    "timestamp": time.time()
                })

        # در مرحله نهایی، بررسی بسته شدن معامله
        if self.current_phase == SessionPhase.FINAL_NEGOTIATION:
            self.check_deal_closure(user_message, responses)

        return responses

    def get_active_agents(self) -> List[AgentRole]:
        """تعیین عوامل فعال در مرحله جاری"""
        active_agents = []

        if self.current_phase == SessionPhase.INTRODUCTION:
            # در معرفی همه گوش می‌دهند
            active_agents = [AgentRole.CONSERVATIVE_INVESTOR, AgentRole.RISKY_INVESTOR,AgentRole.EVALUATOR]
        elif self.current_phase == SessionPhase.FINANCIAL_QUESTIONS:
            active_agents = [AgentRole.CONSERVATIVE_INVESTOR,AgentRole.EVALUATOR]
        elif self.current_phase == SessionPhase.COMPETITIVE_CHALLENGE:
            active_agents = [AgentRole.COMPETITOR,AgentRole.EVALUATOR]
        elif self.current_phase == SessionPhase.FINAL_NEGOTIATION:
            active_agents = [AgentRole.CONSERVATIVE_INVESTOR, AgentRole.RISKY_INVESTOR,AgentRole.EVALUATOR]

        return active_agents

    def get_agent_context(self, agent_role: AgentRole) -> Dict:
        """دریافت زمینه مناسب برای هر عامل"""
        context = {
            "current_phase": self.current_phase.value,
            "elapsed_time": time.time() - self.session_start_time,
            "phase_time": time.time() - self.phase_start_time,
            "user_profile": self.user_profile,
            "other_agents_states": {}
        }

        # اضافه کردن وضعیت سایر عوامل
        for role, agent in self.agents.items():
            if role != agent_role:
                context["other_agents_states"][role.value] = {
                    "state": agent.state.value,
                    "satisfaction": agent.satisfaction_level
                }

        return context

    def check_deal_closure(self, user_message: str, responses: List[Dict]):
        """بررسی بسته شدن معامله"""
        # کلمات کلیدی برای تشخیص توافق
        agreement_keywords = ["موافقم", "قبول", "توافق", "می‌پذیرم", "باشه", "خوبه"]

        # بررسی پیام کاربر برای اعداد
        import re
        numbers = re.findall(r'\d+', user_message)

        # اگر کاربر اعداد جدیدی پیشنهاد داده
        if numbers:
            for num in numbers:
                num = int(num)
                if num > 1000000000:  # احتمالا مبلغ سرمایه است
                    self.user_profile["final_investment"] = num
                elif num <= 100:  # احتمالا درصد سهام است
                    self.user_profile["final_equity"] = num

        # بررسی توافق سرمایه‌گذاران
        conservative_agrees = False
        risky_agrees = False

        for response in responses:
            if response["role"] == AgentRole.CONSERVATIVE_INVESTOR.value:
                if any(keyword in response["message"].lower() for keyword in agreement_keywords):
                    conservative_agrees = True
            elif response["role"] == AgentRole.RISKY_INVESTOR.value:
                if any(keyword in response["message"].lower() for keyword in agreement_keywords):
                    risky_agrees = True

        # اگر حداقل یک سرمایه‌گذار موافق باشد و مبلغ مشخص شده باشد
        if (conservative_agrees or risky_agrees) and self.user_profile["final_investment"] > 0:
            self.user_profile["deal_closed"] = True
            self.current_phase = SessionPhase.COMPLETED

    def add_user_message(self, message: str):
        """افزودن پیام کاربر به لاگ"""
        self.conversation_log.append({
            "sender": "user",
            "message": message,
            "timestamp": time.time(),
            "phase": self.current_phase.value
        })

    def add_agent_message(self, agent_name: str, message: str):
        """افزودن پیام عامل به لاگ"""
        self.conversation_log.append({
            "sender": agent_name,
            "message": message,
            "timestamp": time.time(),
            "phase": self.current_phase.value
        })

    def add_system_message(self, message: str):
        """افزودن پیام سیستم به لاگ"""
        self.conversation_log.append({
            "sender": "system",
            "message": message,
            "timestamp": time.time(),
            "phase": self.current_phase.value
        })

    def get_session_summary(self) -> Dict:
        """دریافت خلاصه جلسه"""
        total_duration = time.time() - self.session_start_time

        # محاسبه میزان موفقیت
        success_rate = 0
        if self.user_profile["deal_closed"]:
            # محاسبه درصد موفقیت براساس مبلغ و سهام
            investment_ratio = self.user_profile["final_investment"] / self.user_profile["investment_requested"]
            equity_ratio = self.user_profile["equity_offered"] / self.user_profile["final_equity"] if self.user_profile[
                                                                                                          "final_equity"] > 0 else 0

            success_rate = (investment_ratio * 0.6 + equity_ratio * 0.4) * 100

        summary = {
            "duration": total_duration,
            "phase_reached": self.current_phase.value,
            "deal_closed": self.user_profile["deal_closed"],
            "final_investment": self.user_profile["final_investment"],
            "final_equity": self.user_profile["final_equity"],
            "success_rate": success_rate,
            "agents_satisfaction": {
                role.value: agent.satisfaction_level
                for role, agent in self.agents.items()
            },
            "message_count": len(self.conversation_log)
        }

        return summary

    def get_final_report(self) -> Dict:
        """دریافت گزارش نهایی جلسه"""
        evaluator = self.agents[AgentRole.EVALUATOR]
        evaluation_report = evaluator.generate_final_report()

        session_summary = self.get_session_summary()

        final_report = {
            "session_info": {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": session_summary["duration"],
                "total_messages": session_summary["message_count"]
            },
            "negotiation_result": {
                "deal_closed": session_summary["deal_closed"],
                "investment_requested": self.user_profile["investment_requested"],
                "investment_secured": session_summary["final_investment"],
                "equity_offered": self.user_profile["equity_offered"],
                "equity_given": session_summary["final_equity"],
                "success_rate": session_summary["success_rate"]
            },
            "performance_evaluation": evaluation_report,
            "agents_feedback": {
                role.value: {
                    "final_state": agent.state.value,
                    "satisfaction": agent.satisfaction_level,
                    "notes": agent.notes
                }
                for role, agent in self.agents.items()
            },
            "conversation_log": self.conversation_log
        }

        return final_report

    def export_report(self, format: str = "json") -> str:
        """خروجی گزارش در فرمت‌های مختلف"""
        report = self.get_final_report()

        if format.lower() == "json":
            return json.dumps(report, ensure_ascii=False, indent=2)
        elif format.lower() == "text":
            return self._format_text_report(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_text_report(self, report: Dict) -> str:
        """فرمت‌بندی گزارش به صورت متنی"""
        text = f"""
گزارش جلسه مذاکره جذب سرمایه
===========================
تاریخ: {report['session_info']['date']}
مدت زمان: {report['session_info']['duration']:.0f} ثانیه

نتیجه مذاکره
------------
وضعیت: {'موفق' if report['negotiation_result']['deal_closed'] else 'ناموفق'}
سرمایه درخواستی: {report['negotiation_result']['investment_requested']:,} تومان
سرمایه جذب شده: {report['negotiation_result']['investment_secured']:,} تومان
سهام پیشنهادی: {report['negotiation_result']['equity_offered']}%
سهام نهایی: {report['negotiation_result']['equity_given']}%
درصد موفقیت: {report['negotiation_result']['success_rate']:.1f}%

ارزیابی عملکرد
--------------
امتیاز کل: {report['performance_evaluation']['total_score']}
درصد: {report['performance_evaluation']['percentage']:.1f}%
رتبه: {report['performance_evaluation']['grade']}

نقاط قوت:
{self._format_list(report['performance_evaluation']['strengths'])}

نقاط ضعف:
{self._format_list(report['performance_evaluation']['weaknesses'])}

توصیه‌ها:
{self._format_list(report['performance_evaluation']['recommendations'])}

رضایت عوامل
------------
"""

        for agent, feedback in report['agents_feedback'].items():
            text += f"{agent}: {feedback['satisfaction']}% ({feedback['final_state']})\n"

        return text

    def _format_list(self, items: List[str]) -> str:
        """فرمت‌بندی لیست برای گزارش متنی"""
        return "\n".join(f"- {item}" for item in items)


class NegotiationSession:
    """کلاس اصلی برای مدیریت جلسه مذاکره"""

    def __init__(self, api_key: str):
        self.conversation_manager = ConversationManager(api_key)
        self.is_active = True

    def start_session(self):
        """شروع جلسه مذاکره"""
        welcome_message = """
خوش آمدید به کارگاه مذاکره جذب سرمایه!

شما در نقش بنیان‌گذار یک استارتاپ EdTech هستید که قصد جذب ۵۰ میلیارد تومان سرمایه دارید.
در این جلسه با سه نفر روبرو خواهید شد:
1. آقای محمدی - سرمایه‌گذار محتاط
2. خانم اکبری - سرمایه‌گذار ریسک‌پذیر
3. آقای رضایی - بنیان‌گذار استارتاپ رقیب

جلسه شامل ۴ مرحله است:
1. معرفی (۲ دقیقه)
2. سوالات مالی (۳ دقیقه)
3. چالش رقابتی (۳ دقیقه)
4. مذاکره نهایی (۲ دقیقه)

لطفا با معرفی کوتاه استارتاپ خود شروع کنید...
"""
        print(welcome_message)
        return welcome_message

    def process_input(self, user_input: str) -> List[Dict]:
        """پردازش ورودی کاربر"""
        if user_input.lower() in ["exit", "quit", "خروج"]:
            self.is_active = False
            return [{"agent": "system", "message": "جلسه به پایان رسید."}]

        return self.conversation_manager.process_user_input(user_input)

    def is_session_active(self) -> bool:
        """بررسی فعال بودن جلسه"""
        return self.is_active and self.conversation_manager.current_phase != SessionPhase.COMPLETED

    def get_final_report(self) -> Dict:
        """دریافت گزارش نهایی"""
        return self.conversation_manager.get_final_report()

    def export_report(self, format: str = "json") -> str:
        """خروجی گزارش"""
        return self.conversation_manager.export_report(format)