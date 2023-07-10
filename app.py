import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import openai

load_dotenv()

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

openai.api_key = os.environ["OPENAI_API_KEY"]

@app.event("app_mention")
def handle_mention(event, say):
    # user = event["user"]
    # say(f"Hello <@{user}>!")

    # channel = event["channel"]
    thread_ts = event["ts"]
    # say(channel=channel, thread_ts=thread_ts, text=f"Hello <@{user}>!")
    # say(thread_ts=thread_ts, text=f"Hello <@{user}>!")

    message = event["text"]
    response = openai.ChatCompletion.create(
        model=os.environ["OPENAI_API_MODEL"],
        messages=[
            {"role": "user", "content": message},
        ],
    )
    # print(response) # これほかの方法で
    say(thread_ts=thread_ts, text=response.choices[0]["message"]["content"].strip())

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()