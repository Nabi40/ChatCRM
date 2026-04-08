import re
import uuid
from typing import Optional, Tuple

from django.db.models import Q

from .models import (
    UserProfile,
    Inventory,
    Order,
    RefundRequest,
    Complaint,
    ChatSession,
    ChatMessage,
)
from .llm import generate_human_reply


def clean_reply(text: str) -> str:
    bad_phrases = [
        "Best regards",
        "Regards",
        "[Your name]",
        "[Your company name]",
        "[Your company website",
        "Sincerely",
    ]

    for phrase in bad_phrases:
        text = text.replace(phrase, "")

    # remove extra new lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # join into clean sentence
    cleaned = " ".join(lines)

    return cleaned.strip()


def build_system_prompt() -> str:
    return (
        "You are a friendly e-commerce CRM chat assistant. "
        "Reply like a real human support agent in a chat window, not like an email. "
        "Keep replies short, clear, warm, and conversational. "
        "Do not write email-style closings. "
        "Do not include greetings like 'Best regards'. "
        "Do not include placeholders like [Your name] or [Company name]. "
        "Do not repeat unnecessary details. "
        "Use only the provided business facts. "
        "If information is missing, ask one short follow-up question. "
        "If unsure, politely suggest human handoff."
    )


def llm_reply(context: str) -> str:
    raw = generate_human_reply(build_system_prompt(), context)
    return clean_reply(raw)


def get_or_create_session(user: UserProfile, session_key: str = "") -> ChatSession:
    if session_key:
        session = ChatSession.objects.filter(session_key=session_key, user=user).first()
        if session:
            return session

    return ChatSession.objects.create(user=user, session_key=uuid.uuid4().hex)


def extract_order_id(message: str) -> Optional[str]:
    upper_message = message.upper()

    explicit = re.search(r"\bORD\d{4,10}\b", upper_message)
    if explicit:
        return explicit.group(0)

    loose = re.search(r"\b(?:ORD[-_ ]?)?(\d{4,10})\b", upper_message)
    if loose:
        return f"ORD{loose.group(1)}"

    return None


def find_order_for_message(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Optional[Order]:
    order_id = extract_order_id(message)

    if order_id:
        order = Order.objects.filter(user=user, order_id__iexact=order_id).first()
        if order:
            session.current_order = order
            session.save(update_fields=["current_order", "updated_at"])
            return order

    if session.current_order_id:
        return session.current_order

    return user.orders.order_by("-created_at").first()


def find_product_from_message(message: str) -> Optional[Inventory]:
    text = message.lower().strip()

    product = Inventory.objects.filter(
        Q(product_name__icontains=text) | Q(product_code__icontains=text)
    ).first()
    if product:
        return product

    for token in re.findall(r"[a-zA-Z0-9\-]+", text):
        product = Inventory.objects.filter(
            Q(product_name__icontains=token) | Q(product_code__icontains=token)
        ).first()
        if product:
            return product

    return None


def recent_history_text(session: ChatSession) -> str:
    messages = ChatMessage.objects.filter(session=session).order_by("-created_at")[:10]
    messages = list(reversed(messages))
    return "\n".join([f"{m.role}: {m.text}" for m in messages])


def detect_intent(message: str) -> str:
    text = message.lower().strip()

    if any(
        phrase in text
        for phrase in [
            "where is my order",
            "track my order",
            "track order",
            "order status",
            "status of my order",
            "delivery status",
            "shipped",
            "delivered yet",
            "when will it arrive",
            "where is it",
            "tracking",
        ]
    ):
        return "order_status"

    if any(word in text for word in ["cancel", "cancellation", "cancel it"]):
        return "cancellation"

    if any(word in text for word in ["refund", "return", "money back"]):
        return "refund"

    if any(
        word in text
        for word in [
            "product",
            "stock",
            "available",
            "availability",
            "price",
            "inventory",
            "t-shirt",
            "shirt",
            "jeans",
        ]
    ):
        return "product_inquiry"

    if any(
        word in text
        for word in [
            "complaint",
            "problem",
            "issue",
            "bad service",
            "damaged",
            "angry",
            "terrible",
            "wrong product",
        ]
    ):
        return "complaint"

    return "general_inquiry"


def handle_order_status(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    order = find_order_for_message(user, session, message)

    if not order:
        return (
            "order_status",
            "Sure — please share your order ID and I’ll check the status for you.",
        )

    context = f"""
Intent: order status
Customer: {user.name}
Order ID: {order.order_id}
Product: {order.product.product_name}
Quantity: {order.quantity}
Status: {order.status}
Delivery date: {order.delivery_date}
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a very short chat reply in 1 to 3 sentences.
No email format.
No signature.
No placeholders.
Sound natural and helpful.
""".strip()

    return "order_status", llm_reply(context)


def handle_cancellation(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    order = find_order_for_message(user, session, message)

    if not order:
        return (
            "cancellation",
            "Sure — please send me your order ID and I’ll check whether it can still be cancelled.",
        )

    cancellable_statuses = ["processing", "pending", "confirmed"]

    if order.status in cancellable_statuses:
        order.status = "cancelled"
        order.save(update_fields=["status"])

        context = f"""
Intent: cancellation
Customer: {user.name}
Order ID: {order.order_id}
Action taken: order cancelled successfully
Current order status: {order.status}
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a warm, natural support reply.
""".strip()

        return "cancellation", llm_reply(context)

    if order.status in ["shipped", "delivered"]:
        context = f"""
Intent: cancellation
Customer: {user.name}
Order ID: {order.order_id}
Current order status: {order.status}
Policy: shipped or delivered orders cannot be cancelled now. Suggest return/refund path if appropriate.
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a polite, human-like support reply.
""".strip()

        return "cancellation", llm_reply(context)

    return (
        "cancellation",
        "I’m not fully sure about this cancellation case, so let me connect you with a human agent for this.",
    )


def handle_refund(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    order = find_order_for_message(user, session, message)

    if not order:
        return (
            "refund",
            "I can help with that. Please send your order ID first so I can check refund eligibility.",
        )

    if order.status == "delivered":
        refund = RefundRequest.objects.create(
            order=order,
            reason=message,
            status="requested",
        )

        context = f"""
Intent: refund
Customer: {user.name}
Order ID: {order.order_id}
Order status: {order.status}
Refund request status: {refund.status}
Refund reason: {refund.reason}
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a natural, helpful support reply.
""".strip()

        return "refund", llm_reply(context)

    if order.status == "shipped":
        context = f"""
Intent: refund
Customer: {user.name}
Order ID: {order.order_id}
Order status: {order.status}
Policy: refund cannot be processed before delivery. Suggest waiting until delivery or contacting support if needed.
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a polite support reply.
""".strip()

        return "refund", llm_reply(context)

    return (
        "refund",
        "I’m not fully sure about this refund case, so let me connect you with a human agent for this.",
    )


def handle_product_inquiry(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    product = find_product_from_message(message)

    if not product:
        return (
            "product_inquiry",
            "I couldn’t find that product yet. Please share the product name or code, like t-shirt-01.",
        )

    context = f"""
Intent: product inquiry
Customer: {user.name}
Product code: {product.product_code}
Product name: {product.product_name}
Available quantity: {product.quantity}
Price: {product.price}
Description: {product.description or 'No details available'}
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write a friendly shopping support reply.
""".strip()

    return "product_inquiry", llm_reply(context)


def handle_complaint(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    order = find_order_for_message(user, session, message)

    Complaint.objects.create(
        user=user,
        order=order,
        message=message,
    )

    context = f"""
Intent: complaint
Customer: {user.name}
Order ID: {order.order_id if order else 'unknown'}
Complaint logged: yes
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Write an empathetic support reply and mention human handoff if needed.
""".strip()

    return "complaint", llm_reply(context)


def handle_general_inquiry(
    user: UserProfile,
    session: ChatSession,
    message: str,
) -> Tuple[str, str]:
    context = f"""
Intent: general inquiry
Customer: {user.name}
Conversation history:
{recent_history_text(session)}
Current user message: {message}

Reply as an e-commerce support assistant. If unsure, say a human agent can help.
""".strip()

    return "general_inquiry", llm_reply(context)


def process_chat(email: str, message: str, session_key: str = "") -> dict:
    user = UserProfile.objects.filter(email=email).first()

    if not user:
        return {
            "ok": False,
            "msg": "I couldn’t find your account with that email. Please register the customer in the system first.",
            "session_key": session_key or "",
        }

    session = get_or_create_session(user, session_key)

    ChatMessage.objects.create(
        session=session,
        role="user",
        text=message,
    )

    intent = detect_intent(message)
    session.last_intent = intent
    session.save(update_fields=["last_intent", "updated_at"])

    handlers = {
        "order_status": handle_order_status,
        "cancellation": handle_cancellation,
        "refund": handle_refund,
        "product_inquiry": handle_product_inquiry,
        "complaint": handle_complaint,
        "general_inquiry": handle_general_inquiry,
    }

    _, reply = handlers.get(intent, handle_general_inquiry)(user, session, message)

    ChatMessage.objects.create(
        session=session,
        role="assistant",
        text=reply,
    )

    return {
        "ok": True,
        "session_key": session.session_key,
        "intent": intent,
        "msg": reply,
    }