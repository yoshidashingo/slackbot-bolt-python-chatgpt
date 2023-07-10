import os
import time
import re
from datetime import timedelta
from typing import Any
from dotenv import load_dotenv
from slack_bolt import App
import logging
import json
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
import openai
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.schema import LLMResult
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.memory import MomentoChatMessageHistory

CHAT_UPDATE_INTERVAL_SEC = 1

load_dotenv()

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
# app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    process_before_response=True,
)

# openai.api_key = os.environ["OPENAI_API_KEY"]

# ログ
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class SlackStreamingCallbackHandler(BaseCallbackHandler):
    last_send_time = time.time()
    message = ""

    def __init__(self, channel, ts):
        self.channel = channel
        self.ts = ts

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.message += token

        now = time.time()
        if now - self.last_send_time > CHAT_UPDATE_INTERVAL_SEC:
            self.last_send_time = now
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}..."
            )

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        # add_ai_message(self.ts, self.message)
        app.client.chat_update(channel=self.channel, ts=self.ts, text=self.message)

def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub('<@.*>',"",event["text"])

    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True,
    )

    cache_name = os.environ["MOMENTO_CACHE"]
    ttl = timedelta(hours=1)
    history = MomentoChatMessageHistory.from_client_params(
        thread_ts,
        cache_name,
        ttl,
    )

    # messages = [
    #     SystemMessage(content="You are a good assistant.")
    # ]
    # cached_messages = history.messages
    # if cached_messages:
    #     list(map(lambda i: messages.append(i), cached_messages))
    # messages.append(HumanMessage(content=" "))

    # history.add_user_message(message)
    # print(f"メッセージ追加後: {history.messages}")

    result = say("\n\nTyping...", thread_ts=thread_ts)
    ts = result["ts"]

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
    llm.predict(message, callbacks=[callback])

# botへの応答
# @app.event("app_mention")
def just_ack(ack):
    ack()

app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

# def add_ai_message(thread_ts, ai_message):
#     history = MomentoChatMessageHistory.from_client_params(
#         thread_ts,
#         os.environ["MOMENTO_CACHE"],
#         timedelta(hours=1),
#     )
#     history.add_ai_message(ai_message)


# アプリを起動します：ローカル起動
if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    
# AWS Lambda のエントリポイント
def handler(event, context):
    logger.info("handler called")
    header = event["headers"]
    logging.info(json.dumps(header))

    if "x-slack-retry-num" in header:
        logging.info("SKIP > x-slack-retry-num: " + header["x-slack-retry-num"])
        return 200
 
    # AWS Lambda 環境のリクエスト情報を app が処理できるよう変換してくれるアダプター
    slack_handler = SlackRequestHandler(app=app)
    # 応答はそのまま AWS Lambda の戻り値として返せます
    return slack_handler.handle(event, context)
