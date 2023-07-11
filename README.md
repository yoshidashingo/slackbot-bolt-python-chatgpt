# slackbot-bolt-python-chatgpt

## Prerequisite
- Python 3.10
- Bolt for Python
- AWS Cloud9

## Make Local Python Environment
### AWS Cloud9
1. Login to AWS
1. Open AWS Cloud9 Console
1. Make an Cloud9 environment
1. Open Cloud9 IDE
### Make Repository
1. Githubで空のリポジトリをつくる
1. git cloneする
1. README.md と .gitignore を作成する

### GitHubを操作するためのローカル設定
1. 
> git config --global user.name "名前"                                              
> git config --global user.email メールアドレス

### Make Python Virtual Environment
1. python --version # Pythonバージョンの確認
1. pyenv install 3.10 # python 3.10 のインストール
1. pyenv local 3.10 # ローカルでのバージョンを指定
1. python --version # Pythonバージョンの確認
1. python -m venv .venv # 仮想環境の作成
1. source .venv/bin/activate # 仮想環境の有効化

## Setup Slack App
### Make a new Slack App
1. Name the app and create an app from scratch.
1. Get "Signing Secret" and write it to .env as "SLACK_SIGNING_SECRET" / Basic Information > App Credentials
1. Add an OAuth Scope to Bot Token. / OAuth&Permissions > Scopes > Bot Token Scopes
1. Select "chat:write" operation.
1. Install to Workspace. / OAuth&Permissions > OAuth Tokens for Your Workspace
1. Get "Bot User OAuth Token" and write it to .env as "SLACK_BOT_TOKEN" environmental variables.
1. Generate Token and Scopes with adding new scope "connections:write". / Basic Information > App-Level Tokens
1. To get "App-Level Token" here, click "generate", name this token, click add scope and select "connections:write" 
1. Get "App-Level Token" and write it to .env as "SLACK_APP_TOKEN" environmental variables.
### Enable Socket Mode
1. Enable Socket Mode / Socket Mode > Connect using Socket Mode

## Make App
### アプリをつくる
1. Install Packages
> pip install slack_bolt python-dotenv
1. Make app.py
```
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
```
1. ためしに実行してみる
> python app.py
→ :zap:️ Bolt app is running! 状態になればOK、停止する

### イベントを設定する
アプリがイベントをリッスンできるように設定する。ここではパブリックとプライベートのチャンネルのメッセージをリッスンさせたいので、`message.channels` と `message.groups` をリッスンさせる。
1. Slackボット機能の左パネルから Event Subscriptions を選択し、Enable Events をONにする
1. 「Subscribe to bot events」を開いて「Add Bot User Event」を押下し、「app_mention」を選択し、ページ右下で「Save Changes」を押下する。
1. イベントが追加(スコープの追加)になったのでアプリの再インストールが必要になる。画面上部の案内から「reinstall your app」を押下し、ワークスペースに再インストールする

### アクションを送信して応答する
1. app.py に以下のようにイベントに対するリスナー関数を追加する
```
@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    say(f"Hello <@{user}>!")
```
1. 再度実行してみる
> python app.py
1. チャンネルに /invite する
2. メンションしてメッセージを受け取る
→ Hello @ユーザー名!と表示されたらOK

### スレッド内で返信するようにする
1. 応答時のパラメーターにスレッドを指定する
```
@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    thread_ts = event["ts"]
    say(thread_ts=thread_ts, text=f"Hello <@{user}>!")
```

### OpenAI APIを呼び出す
1. ライブラリをインストールする
> pip install openai
1. 環境変数を指定するために .env ファイルに以下の値を指定する
> OPENAI_API_KEY= (OpenAI の設定ページから取得する)
> OPENAI_API_MODEL=gpt-3.5-turbo-16k-0613
> OPENAI_API_TEMPERATURE=0.5
1. ライブラリをインポートする
```
import openai
```
1. APIキーをセットする
```
openai.api_key = os.environ["OPENAI_API_KEY"]
```

### Chat Completion APIに回答させる
1. app.py を以下のとおりにする
```
@app.event("app_mention")
def handle_mention(event, say):
    thread_ts = event["ts"]
    message = event["text"]
    response = openai.ChatCompletion.create(
        model=os.environ["OPENAI_API_MODEL"],
        messages=[
            {"role": "user", "content": message},
        ],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        stream=True
    )
    say(thread_ts=thread_ts, text=response.choices[0]["message"]["content"].strip())
```
1. 再度実行してみる
> python app.py
2. メンションしてメッセージを受け取る
→ OpenAIのレスポンスが表示されたらOK

### ストリーミングで応答する
1. Python標準のAny型をimportしたり、timeライブラリをimportし、投稿の更新間隔を定数定義する。
```
from typing import Any
import time
CHAT_UPDATE_INTERVAL_SEC = 1
```

1. appクライアントの初期化パラメータを変更する
```
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    process_before_response=True,
)
```
1. LangChainのライブラリをimportする
```
import langchain
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.schema import LLMResult
```
1. 応答ストリームを受け取るCallbackハンドラークラスを定義する
```
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
        app.client.chat_update(channel=self.channel, ts=self.ts, text=self.message)
```
1. LangChainを使って操作をおこなうように変更する
```
    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True
    )
    
    # say(thread_ts=thread_ts, text=response.choices[0]["message"]["content"].strip())
    result = say("\n\nTyping...", thread_ts=thread_ts)
    ts = result["ts"]

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
    llm.predict(message, callbacks=[callback])
```

1. 実行して確認する
> python app.py
→ 回答がストリームで得られることを確認する
→ ※この時点ではSlackから最大4回呼び出されていることがわかります。これは3秒以内に完了しないとリトライするSlack側の仕様によります。

### Lazy handlerでSlackからリトライ呼び出しされる前に単純応答を返す
1. @app.event にLazyハンドラーを登録し、組み込みのack関数ではすばやく単純な応答を返すことで再送を防ぎます。
```
# botへの応答
# @app.event("app_mention")
def just_ack(ack):
    ack()

app.event("app_mention")(ack=just_ack, lazy=[handle_mention])
```
1. 実行して確認する
> python app.py
→ 回答がストリームで得られ1回だけ呼ばれることを確認する

### 会話履歴を利用する
1. boto3とMomentoをインストールする
> pip install boto3
> pip install momento

MomentoをLangChainのmemoryモジュールから利用します。
1. .env にAPIトークンを設定します。
```
MOMENTO_AUTH_TOKEN=xxxxxxxx
MOMENTO_CACHE=xxxxxxxx
#MOMENTO_TTL=1
```
1. memoryモジュールをimportします。各ロールメッセージもimportします。TTLを設定するためにtimedeltaもimportする。
```
from langchain.memory import MomentoChatMessageHistory
from datetime import timedelta
from langchain.schema import (
    HumanMessage,
    SystemMessage
)
```
1. TTLを指定して履歴クライアントを初期化する
```
    history = MomentoChatMessageHistory.from_client_params(
        thread_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=os.environ["MOMENTO_TTL"]),
    )
```
1. 


### AWS Lambdaに対応させる
1. Lambdaでログを有効にする
```
import logging
import json
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
```
```
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
```

2. Lambdaから呼び出されるエントリーポイントの関数を定義する
```
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
```
エントリーポイントの関数では、Lambdaのスピ��アップ時間が3秒かかった場合に単純応答が返せないことを想定し、再送を無視する制御を入れています。


## Deploy Pipeline
### requirements.txt を作成する
1. リポジトリにあげるために現在のライブラリ環境をrequirements.txtに出力します
> pip freeze > requirements.txt

### Serverless Framework をセットアップする
1. serverless.yml を作成する
- リポジトリ直下に serverless.yml ファイルを作成する
```
service: ChatGPTSlackFunction7
frameworkVersion: '3'

provider:
  name: aws
  region: ap-northeast-1
  stage: dev
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - lambda:InvokeFunction
          Resource: '*'

package:
  patterns:
    - '!.venv/**'
    - '!.env'
    - '!.gitignore'
    - '!.python-version'
    - '!.git/**'

functions:
  app:
    name: ChatGPTSlackFunction7-${sls:stage}-app
    handler: app.handler
    runtime: python3.10
    memorySize: 512
    timeout: 120
    url: true

plugins:
  - serverless-python-requirements
  - serverless-dotenv-plugin

```
1. Serverless Frameworkのインストール
> npm install -g serverless
1. プラグインのインストール
> serverless plugin install -n serverless-python-requirements
> serverless plugin install -n serverless-python-requirements
1. パッケージしてリリースする
> serverless deploy
1. 確認する
- 実行環境
- タイムアウト値
- 環境変数
- 関数URL

### Socket ModeからAWS Lambdaに切り替える
1. モードの切り替え
> 左のSocket Modeから「Enable Socket Mode」をOFFにして「Disable」を押下する
1. 関数URLを認証する
> 左のEvent Subscriptions の画面のEnable Events直下のRequest URLにLambda関数URLを入力してEnterを押下する
> 正しいURLを入力すると、Lambda内のBoltがURL確認のアクセスに対してHTTP200を返してくれます。
> たまに失敗することがあります。スピンアップの時間がかかりすぎている場合などにタイムアウトしている可能性があるため、何度かRetryしてみてください。
1. Slackbotに質問をして、正しく動くことを確認してください。

