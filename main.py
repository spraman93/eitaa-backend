from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

pending_auth = {}
active_clients = {}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Eitaa Manager Backend is running"
    }


@app.get("/status")
async def status():
    return {
        "status": "ok",
        "pending_auth": list(pending_auth.keys()),
        "active_clients": list(active_clients.keys())
    }


# =========================================================
# SEND CODE
# =========================================================

@app.post("/auth/send-code")
async def send_code(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "send-code",
                "message": "شماره موبایل وارد نشده است"
            }

        old_auth = pending_auth.get(phone)

        if old_auth:
            try:
                await old_auth["client"].__aexit__(None, None, None)
            except Exception:
                pass

            pending_auth.pop(phone, None)

        old_client = active_clients.get(phone)

        if old_client:
            try:
                await old_client.__aexit__(None, None, None)
            except Exception:
                pass

            active_clients.pop(phone, None)

        client = await EitaaClient.create(
            require_auth=False
        )

        await client.__aenter__()

        challenge = await client.auth.request_code(
            phone,
            settings=OtpCodeSettings()
        )

        pending_auth[phone] = {
            "client": client,
            "challenge": challenge
        }

        return {
            "status": "ok",
            "message": "کد تأیید ارسال شد",
            "delivery": str(challenge.delivery),
            "next_delivery": str(challenge.next_delivery),
            "timeout_seconds": challenge.timeout_seconds
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "send-code",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# LOGIN
# =========================================================

@app.post("/auth/login")
async def login(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()
        code = str(data.get("code", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "login",
                "message": "شماره موبایل وارد نشده است"
            }

        if not code:
            return {
                "status": "error",
                "where": "login",
                "message": "کد تأیید وارد نشده است"
            }

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
                "where": "login",
                "message": "درخواست کد پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        active_clients[phone] = client

        pending_auth.pop(phone, None)

        return {
            "status": "ok",
            "message": "ورود به ایتا موفق بود"
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "login",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# RESEND CODE
# =========================================================

@app.post("/auth/resend-code")
async def resend_code(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "resend-code",
                "message": "شماره موبایل وارد نشده است"
            }

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
                "where": "resend-code",
                "message": "درخواست قبلی پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        new_challenge = await client.auth.resend_code(
            challenge.phone_number,
            challenge.phone_code_hash
        )

        pending_auth[phone] = {
            "client": client,
            "challenge": new_challenge
        }

        return {
            "status": "ok",
            "message": "کد مجدد درخواست شد",
            "delivery": str(new_challenge.delivery),
            "next_delivery": str(new_challenge.next_delivery),
            "timeout_seconds": new_challenge.timeout_seconds
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "resend-code",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# تبدیل مقدار به متن ساده
# =========================================================

def safe_text(value):
    if value is None:
        return ""

    try:
        return str(value)
    except Exception:
        return ""


# =========================================================
# استخراج اطلاعات چت‌ها
# =========================================================

def extract_chats(result):
    output = []

    # ساختار معمول نتیجه dialogs.list
    dialogs = result.get("dialogs", [])
    chats = result.get("chats", [])
    users = result.get("users", [])

    # تبدیل chats به دیکشنری بر اساس id
    chats_map = {}

    if isinstance(chats, list):
        for chat in chats:

            try:
                chat_id = getattr(chat, "id", None)

                if chat_id is None and isinstance(chat, dict):
                    chat_id = chat.get("id")

                if chat_id is not None:
                    chats_map[str(chat_id)] = chat

            except Exception:
                pass

    # تبدیل users به دیکشنری بر اساس id
    users_map = {}

    if isinstance(users, list):
        for user in users:

            try:
                user_id = getattr(user, "id", None)

                if user_id is None and isinstance(user, dict):
                    user_id = user.get("id")

                if user_id is not None:
                    users_map[str(user_id)] = user

            except Exception:
                pass

    # پردازش dialogs
    if isinstance(dialogs, list):

        for dialog in dialogs:

            try:

                peer = getattr(dialog, "peer", None)

                if peer is None and isinstance(dialog, dict):
                    peer = dialog.get("peer")

                chat_id = None

                if peer is not None:

                    chat_id = getattr(peer, "channel_id", None)

                    if chat_id is None:
                        chat_id = getattr(peer, "chat_id", None)

                    if chat_id is None:
                        chat_id = getattr(peer, "user_id", None)

                    if isinstance(peer, dict):

                        if chat_id is None:
                            chat_id = peer.get("channel_id")

                        if chat_id is None:
                            chat_id = peer.get("chat_id")

                        if chat_id is None:
                            chat_id = peer.get("user_id")

                # اگر از peer شناسه پیدا نشد
                if chat_id is None:

                    chat_id = getattr(dialog, "id", None)

                    if chat_id is None and isinstance(dialog, dict):
                        chat_id = dialog.get("id")

                chat = None

                if chat_id is not None:
                    chat = chats_map.get(str(chat_id))

                    if chat is None:
                        chat = users_map.get(str(chat_id))

                # نوع گفتگو
                kind = "unknown"

                if chat is not None:

                    chat_kind = getattr(chat, "kind", None)

                    if chat_kind is None and isinstance(chat, dict):
                        chat_kind = chat.get("kind")

                    if chat_kind is not None:
                        kind = safe_text(chat_kind)

                # نام
                title = ""

                if chat is not None:

                    title_value = getattr(chat, "title", None)

                    if title_value is None and isinstance(chat, dict):
                        title_value = chat.get("title")

                    if title_value:
                        title = safe_text(title_value)

                    if not title:

                        first_name = getattr(chat, "first_name", None)

                        if first_name is None and isinstance(chat, dict):
                            first_name = chat.get("first_name")

                        last_name = getattr(chat, "last_name", None)

                        if last_name is None and isinstance(chat, dict):
                            last_name = chat.get("last_name")

                        title = (
                            safe_text(first_name)
                            + " "
                            + safe_text(last_name)
                        ).strip()

                # username
                username = ""

                if chat is not None:

                    username_value = getattr(chat, "username", None)

                    if username_value is None and isinstance(chat, dict):
                        username_value = chat.get("username")

                    username = safe_text(username_value)

                # اضافه کردن
                output.append({
                    "id": safe_text(chat_id),
                    "title": title,
                    "username": username,
                    "kind": kind
                })

            except Exception:
                pass

    return output


# =========================================================
# CHATS
# =========================================================

@app.post("/chats")
async def chats(request: Request):

    try:

        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "chats",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "chats",
                "message": "حساب وارد نشده است"
            }

        # دریافت گفتگوها
        result = await client.dialogs.list(
            limit=100
        )

        # استخراج اطلاعات ساده
        items = extract_chats(result)

        return {
            "status": "ok",
            "where": "chats",
            "message": "لیست گفتگوها دریافت شد",
            "count": len(items),
            "data": items
        }

    except Exception as e:

        return {
            "status": "error",
            "where": "chats",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# GROUPS
# =========================================================

@app.post("/chats/groups")
async def groups(request: Request):

    try:

        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "groups",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "groups",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.groups(
            limit=100
        )

        items = extract_chats(result)

        return {
            "status": "ok",
            "where": "groups",
            "message": "لیست گروه‌ها دریافت شد",
            "count": len(items),
            "data": items
        }

    except Exception as e:

        return {
            "status": "error",
            "where": "groups",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# CHANNELS
# =========================================================

@app.post("/chats/channels")
async def channels(request: Request):

    try:

        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "channels",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "channels",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.channels(
            limit=100
        )

        items = extract_chats(result)

        return {
            "status": "ok",
            "where": "channels",
            "message": "لیست کانال‌ها دریافت شد",
            "count": len(items),
            "data": items
        }

    except Exception as e:

        return {
            "status": "error",
            "where": "channels",
            "error_type": type(e).__name__,
            "message": str(e)
                    }
