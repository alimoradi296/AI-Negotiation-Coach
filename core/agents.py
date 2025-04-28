# agents.py - مدیریت عوامل هوش مصنوعی

from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
from langchain_openai import ChatOpenAI
from abc import ABC, abstractmethod
import time


class AgentRole(Enum):
    CONSERVATIVE_INVESTOR = "conservative_investor"
    RISKY_INVESTOR = "risky_investor"
    COMPETITOR = "competitor"
    EVALUATOR = "evaluator"


class AgentState(Enum):
    NEUTRAL = "neutral"
    INTERESTED = "interested"
    SKEPTICAL = "skeptical"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"


class Agent(ABC):
    """کلاس پایه برای همه عوامل"""

    def __init__(self, name: str, role: AgentRole, api_key: str):
        self.name = name
        self.role = role
        self.state = AgentState.NEUTRAL
        self.conversation_history: List[Dict] = []
        self.client = ChatOpenAI(model="gpt-4o-mini", base_url="https://api.avalai.ir/v1",api_key=api_key,temperature=0.7,                max_tokens=300)
        self.satisfaction_level = 50  # 0-100
        self.notes: List[str] = []

    @abstractmethod
    def get_system_prompt(self) -> str:
        """پرامپت سیستم برای هر عامل"""
        pass

    def generate_response(self, user_message: str, context: Dict) -> str:
        """تولید پاسخ براساس پیام کاربر و زمینه"""

        # به‌روزرسانی تاریخچه مکالمه
        self.conversation_history.append({"role": "user", "content": user_message})

        # آماده‌سازی پرامپت با زمینه
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "system",
             "content": f"Current state: {self.state.value}\nSatisfaction: {self.satisfaction_level}%"}
        ]
        messages.extend(self.conversation_history[-10:])  # حداکثر 10 پیام آخر

        # فراخوانی API
        try:
            response = self.client.invoke(
                messages,

            )

            ai_response = response.content
            self.conversation_history.append({"role": "assistant", "content": ai_response})

            # به‌روزرسانی وضعیت براساس پاسخ
            self.update_state(user_message, ai_response)

            return ai_response

        except Exception as e:
            return f"خطا در تولید پاسخ: {str(e)}"

    def update_state(self, user_message: str, ai_response: str):
        """به‌روزرسانی وضعیت عامل براساس مکالمه"""
        # این متد در کلاس‌های فرزند با منطق خاص هر عامل پیاده‌سازی می‌شود
        pass


class ConservativeInvestor(Agent):
    """سرمایه‌گذار محتاط - آقای محمدی"""

    def __init__(self, api_key: str):
        super().__init__("آقای محمدی", AgentRole.CONSERVATIVE_INVESTOR, api_key)
        self.required_metrics = {
            "cac": False,  # Cost of Customer Acquisition
            "ltv": False,  # Lifetime Value
            "burn_rate": False,
            "market_share": False,
            "risk_assessment": False
        }

    def get_system_prompt(self) -> str:
        return """شما آقای محمدی، یک سرمایه‌گذار محتاط با ۲۰ سال تجربه در سرمایه‌گذاری فناوری هستید.

ویژگی‌های شما:
- بسیار دقیق و جزئی‌نگر هستید
- روی اعداد و ارقام مالی تمرکز دارید
- به دنبال ROI مشخص و برنامه‌های عملیاتی هستید
- از ریسک‌های بالا اجتناب می‌کنید

در این جلسه:
- درباره مدل مالی، هزینه‌ها و درآمدها سوال کنید
- اگر پاسخ‌ها مبهم باشند، سخت‌گیرتر شوید
- اگر اعداد دقیق ارائه شود، نرم‌تر برخورد کنید
- در صورت نبود برنامه مشخص، تمایل به سرمایه‌گذاری را از دست دهید"""

    def update_state(self, user_message: str, ai_response: str):
        """به‌روزرسانی وضعیت براساس کیفیت پاسخ‌های مالی"""

        # بررسی کلمات کلیدی مالی در پاسخ کاربر
        financial_keywords = ["cac", "ltv", "هزینه", "درآمد", "سود", "بازگشت سرمایه", "roi"]
        has_numbers = any(char.isdigit() for char in user_message)
        has_financial_terms = any(keyword in user_message.lower() for keyword in financial_keywords)

        if has_numbers and has_financial_terms:
            self.satisfaction_level = min(100, self.satisfaction_level + 10)
            if self.satisfaction_level > 70:
                self.state = AgentState.INTERESTED
        else:
            self.satisfaction_level = max(0, self.satisfaction_level - 5)
            if self.satisfaction_level < 30:
                self.state = AgentState.SKEPTICAL


class RiskyInvestor(Agent):
    """سرمایه‌گذار ریسک‌پذیر - خانم اکبری"""

    def __init__(self, api_key: str):
        super().__init__("خانم اکبری", AgentRole.RISKY_INVESTOR, api_key)
        self.innovation_score = 0
        self.vision_clarity = 0

    def get_system_prompt(self) -> str:
        return """شما خانم اکبری، یک سرمایه‌گذار ریسک‌پذیر و علاقه‌مند به نوآوری هستید.

ویژگی‌های شما:
- به دنبال ایده‌های نوآورانه و disruptive هستید
- روی پتانسیل بازار و رشد تمرکز دارید
- از ایده‌های جسورانه استقبال می‌کنید
- به چشم‌انداز بلندمدت اهمیت می‌دهید

در این جلسه:
- درباره نوآوری و تمایز از رقبا سوال کنید
- به دنبال چشم‌انداز ۵ ساله و پتانسیل جهانی باشید
- اگر ایده کپی باشد، علاقه خود را از دست دهید
- از پاسخ‌های خلاقانه و آینده‌نگرانه استقبال کنید"""

    def update_state(self, user_message: str, ai_response: str):
        """به‌روزرسانی وضعیت براساس میزان نوآوری و چشم‌انداز"""

        innovation_keywords = ["نوآوری", "جدید", "متفاوت", "انقلاب", "تغییر", "آینده", "هوش مصنوعی"]
        vision_keywords = ["چشم‌انداز", "جهانی", "رشد", "توسعه", "بازار", "میلیون", "میلیارد"]

        has_innovation = any(keyword in user_message.lower() for keyword in innovation_keywords)
        has_vision = any(keyword in user_message.lower() for keyword in vision_keywords)

        if has_innovation:
            self.innovation_score += 1
            self.satisfaction_level = min(100, self.satisfaction_level + 15)

        if has_vision:
            self.vision_clarity += 1
            self.satisfaction_level = min(100, self.satisfaction_level + 10)

        if self.satisfaction_level > 75:
            self.state = AgentState.INTERESTED
        elif self.satisfaction_level < 40:
            self.state = AgentState.SKEPTICAL


class Competitor(Agent):
    """استارتاپ رقیب - آقای رضایی"""

    def __init__(self, api_key: str):
        super().__init__("آقای رضایی", AgentRole.COMPETITOR, api_key)
        self.aggression_level = 50

    def get_system_prompt(self) -> str:
        return """شما آقای رضایی، بنیان‌گذار یک استارتاپ رقیب با ۳۰ میلیون کاربر هستید.

ویژگی‌های شما:
- رقابتی و چالش‌برانگیز هستید
- سعی می‌کنید موقعیت رقیب را تضعیف کنید
- از موفقیت‌های خود صحبت می‌کنید
- نقاط ضعف صنعت را می‌شناسید

در این جلسه:
- ادعاهای رقیب را به چالش بکشید
- از موفقیت‌ها و تجربه خود بگویید
- اگر پاسخ‌های قوی بشنوید، کمی عقب بنشینید
- در صورت ضعف رقیب، تهاجمی‌تر شوید"""

    def update_state(self, user_message: str, ai_response: str):
        """به‌روزرسانی وضعیت براساس قدرت پاسخ‌های رقیب"""

        defensive_keywords = ["اما", "ولی", "شاید", "فکر می‌کنم", "احتمالا"]
        strong_keywords = ["قطعا", "مطمئن", "ثابت شده", "داده‌ها نشان", "تجربه کرده‌ایم"]

        is_defensive = any(keyword in user_message.lower() for keyword in defensive_keywords)
        is_strong = any(keyword in user_message.lower() for keyword in strong_keywords)

        if is_defensive:
            self.aggression_level = min(100, self.aggression_level + 10)
            self.state = AgentState.AGGRESSIVE
        elif is_strong:
            self.aggression_level = max(0, self.aggression_level - 10)
            if self.aggression_level < 30:
                self.state = AgentState.NEUTRAL


class Evaluator(Agent):
    """ارزیاب مذاکره - دکتر کریمی"""

    def __init__(self, api_key: str):
        super().__init__("دکتر کریمی", AgentRole.EVALUATOR, api_key)
        self.evaluation_metrics = {
            "technical_knowledge": 0,
            "communication_skills": 0,
            "negotiation_intelligence": 0,
            "emotional_control": 0,
            "creativity": 0
        }
        self.feedback_points: List[Dict] = []

    def get_system_prompt(self) -> str:
        return """شما دکتر کریمی، یک ارزیاب حرفه‌ای مذاکره با ۱۵ سال تجربه هستید.

        وظایف شما:
        - ارزیابی عملکرد شرکت‌کننده در جلسه
        - شناسایی نقاط قوت و ضعف
        - ارائه بازخورد سازنده و کاربردی
        - امتیازدهی براساس معیارهای مشخص

        در طول جلسه:
        - به جزئیات رفتاری توجه کنید
        - زمان پاسخ‌ها را در نظر بگیرید
        - کیفیت استدلال‌ها را بررسی کنید
        - نحوه مدیریت فشار را ارزیابی کنید"""


    def evaluate_response(self, user_message: str, agent_responses: Dict[str, str]) -> Dict:
        """ارزیابی پاسخ کاربر به عوامل مختلف"""

        evaluation = {
            "timestamp": time.time(),
            "user_message": user_message,
            "feedback": "",
            "scores": {}
        }

        # ارزیابی دانش فنی
        technical_terms = ["roi", "cac", "ltv", "بازار", "رشد", "هزینه", "درآمد"]
        technical_score = sum(1 for term in technical_terms if term in user_message.lower())
        self.evaluation_metrics["technical_knowledge"] += technical_score

        # ارزیابی مهارت‌های ارتباطی
        if len(user_message.split()) > 5 and len(user_message.split()) < 50:
            self.evaluation_metrics["communication_skills"] += 1

        # ارزیابی کنترل احساسات
        negative_emotions = ["ولی", "اما", "نه", "نمی‌توانم", "مشکل"]
        emotional_control = sum(1 for word in negative_emotions if word in user_message.lower())
        if emotional_control < 2:
            self.evaluation_metrics["emotional_control"] += 1

        # تولید بازخورد
        if technical_score > 2:
            evaluation["feedback"] = "استفاده خوب از اصطلاحات فنی و مالی"
        elif emotional_control > 2:
            evaluation["feedback"] = "سعی کنید کمتر از کلمات منفی استفاده کنید"
        else:
            evaluation["feedback"] = "پاسخ‌های خود را با داده‌های بیشتری پشتیبانی کنید"
        #evaluation["feedback"]+=str(agent_responses)
        self.feedback_points.append(evaluation)
        return evaluation

    def generate_final_report(self) -> Dict:
        """تولید گزارش نهایی ارزیابی"""

        total_score = sum(self.evaluation_metrics.values())
        max_possible_score = len(self.evaluation_metrics) * 20  # هر معیار حداکثر 20 امتیاز

        percentage = (total_score / max_possible_score) * 100

        # تعیین رتبه
        if percentage >= 90:
            grade = "A+"
        elif percentage >= 85:
            grade = "A"
        elif percentage >= 80:
            grade = "B+"
        elif percentage >= 75:
            grade = "B"
        elif percentage >= 70:
            grade = "C+"
        elif percentage >= 65:
            grade = "C"
        else:
            grade = "D"

        report = {
            "total_score": total_score,
            "percentage": percentage,
            "grade": grade,
            "metrics": self.evaluation_metrics,
            "strengths": self._identify_strengths(),
            "weaknesses": self._identify_weaknesses(),
            "recommendations": self._generate_recommendations(),
            "feedback_history": self.feedback_points
        }

        return report

    def _identify_strengths(self) -> List[str]:
        """شناسایی نقاط قوت"""
        strengths = []

        for metric, score in self.evaluation_metrics.items():
            if score > 15:  # بالاتر از 75%
                if metric == "technical_knowledge":
                    strengths.append("دانش فنی و کسب‌وکاری قوی")
                elif metric == "communication_skills":
                    strengths.append("مهارت‌های ارتباطی عالی")
                elif metric == "negotiation_intelligence":
                    strengths.append("هوش مذاکره بالا")
                elif metric == "emotional_control":
                    strengths.append("کنترل احساسات مناسب")
                elif metric == "creativity":
                    strengths.append("خلاقیت در ارائه راه‌حل‌ها")

        return strengths

    def _identify_weaknesses(self) -> List[str]:
        """شناسایی نقاط ضعف"""
        weaknesses = []

        for metric, score in self.evaluation_metrics.items():
            if score < 10:  # کمتر از 50%
                if metric == "technical_knowledge":
                    weaknesses.append("نیاز به تقویت دانش فنی و مالی")
                elif metric == "communication_skills":
                    weaknesses.append("بهبود مهارت‌های ارتباطی")
                elif metric == "negotiation_intelligence":
                    weaknesses.append("تقویت تکنیک‌های مذاکره")
                elif metric == "emotional_control":
                    weaknesses.append("مدیریت بهتر احساسات")
                elif metric == "creativity":
                    weaknesses.append("افزایش خلاقیت در پاسخ‌ها")

        return weaknesses

    def _generate_recommendations(self) -> List[str]:
        """تولید توصیه‌های بهبود"""
        recommendations = []

        if self.evaluation_metrics["technical_knowledge"] < 10:
            recommendations.append("مطالعه بیشتر در زمینه مدل‌های مالی استارتاپ‌ها")

        if self.evaluation_metrics["communication_skills"] < 10:
            recommendations.append("تمرین ارائه‌های کوتاه و مختصر")

        if self.evaluation_metrics["emotional_control"] < 10:
            recommendations.append("تمرین تکنیک‌های مدیریت استرس")

        recommendations.append("تمرین با سناریوهای مختلف برای افزایش اعتماد به نفس")
        recommendations.append("مطالعه موردی مذاکرات موفق در صنعت")

        return recommendations