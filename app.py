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
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    process_before_response=True,
)

# ログ
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class SlackStreamingCallbackHandler(BaseCallbackHandler):
    last_send_time = time.time()
    message = ""
    message_context = ""
    message_blocks = ""

    def __init__(self, channel, ts, id_ts):
        self.channel = channel
        self.ts = ts
        self.id_ts = id_ts
        self.interval = CHAT_UPDATE_INTERVAL_SEC
        self.update_count = 0

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.message += token

        now = time.time()
        if now - self.last_send_time > self.interval:
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}\n\nTyping..."
            )
            self.last_send_time = now
            self.update_count += 1
            if self.update_count/10 > self.interval:
                self.interval = self.interval*2

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        add_ai_message(self.id_ts, self.message)
        # app.client.chat_update(channel=self.channel, ts=self.ts, text=self.message)
        self.message_context = "ChatGPT で生成される情報は不正確または不適切な場合がありますが、当社の見解を述べるものではありません。 <https://www.cydas.com/aiguide/|生成AI利用におけるガイドライン>"
        self.message_blocks = '''[
            {"type": "section", "text": {"type": "mrkdwn", "text": "''' + self.message + '''"}},
            {"type": "divider"},
            {"type": "context","elements": [{"type": "mrkdwn","text": "''' + self.message_context + '''"}]}
            ]
        '''
        app.client.chat_update(channel=self.channel, ts=self.ts, blocks=self.message_blocks)

def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub('<@.*>',"",event["text"])

    # 投稿の先頭(=Momentoキー)を示す：初回はevent["ts"],2回目以降はevent["thread_ts"]
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["thread_ts"]

    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True,
    )

    cache_name = os.environ["MOMENTO_CACHE"]
    ttl = timedelta(hours=1)
    history = MomentoChatMessageHistory.from_client_params(
        id_ts,
        cache_name,
        ttl,
    )

    messages = [
        SystemMessage(content="You are a good assistant.")
    ]
    cached_messages = history.messages
    if cached_messages:
        list(map(lambda i: messages.append(i), cached_messages))
    messages.append(HumanMessage(content=message))

    history.add_user_message(message)

    result = say("\n\nTyping...", thread_ts=thread_ts)
    ts = result["ts"]

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts, id_ts=id_ts)
    llm(messages, callbacks=[callback])

# botへの応答
# @app.event("app_mention")
def just_ack(ack):
    ack()

app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

def add_ai_message(thread_ts, ai_message):
    history = MomentoChatMessageHistory.from_client_params(
        thread_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=1),
    )
    history.add_ai_message(ai_message)


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
