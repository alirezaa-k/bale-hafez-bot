import httpx


class BaleAPI:
    def __init__(self, token):
        self.base = f"https://tapi.bale.ai/bot{token}"
        self.client = httpx.AsyncClient(timeout=45)

    async def close(self):
        await self.client.aclose()

    async def call(self, method, payload=None):
        response = await self.client.post(
            f"{self.base}/{method}",
            json=payload or {},
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok", True):
            raise RuntimeError(data)

        return data

    async def get_updates(self, offset=None, timeout=30):
        payload = {
            "timeout": timeout
        }

        if offset is not None:
            payload["offset"] = offset

        return await self.call(
            "getUpdates",
            payload
        )

    async def send_message(
        self,
        chat_id,
        text,
        reply_markup=None
    ):
        payload = {
            "chat_id": chat_id,
            "text": text
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await self.call(
            "sendMessage",
            payload
        )

    async def send_invoice(
        self,
        chat_id,
        title,
        description,
        payload,
        provider_token,
        currency,
        prices,
        start_parameter=None
    ):
        invoice = {
            "chat_id": chat_id,
            "title": title,
            "description": description,
            "payload": payload,
            "provider_token": provider_token,
            "currency": currency,
            "prices": prices,
        }

        if start_parameter:
            invoice["start_parameter"] = start_parameter

        return await self.call(
            "sendInvoice",
            invoice
        )

    async def answer_pre_checkout_query(
        self,
        pre_checkout_query_id,
        ok=True,
        error_message=None
    ):
        payload = {
            "pre_checkout_query_id": pre_checkout_query_id,
            "ok": ok,
        }

        if error_message:
            payload["error_message"] = error_message

        return await self.call(
            "answerPreCheckoutQuery",
            payload
        )

    async def get_me(self):
        return await self.call(
            "getMe"
        )
