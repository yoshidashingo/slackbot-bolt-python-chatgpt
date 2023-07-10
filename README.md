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
    )
    say(thread_ts=thread_ts, text=response.choices[0]["message"]["content"].strip())
```
1. 再度実行してみる
> python app.py
2. メンションしてメッセージを受け取る
→ OpenAIのレスポンスが表示されたらOK

### ぬるぬる応答する


### 会話履歴を利用する


### AWS Lambdaに対応させる


## Deploy Pipeline
### requirements.txt を作成する

### Serverless Framework をセットアップする
1. インストール
1. プラグインのインストール
1. serverless.yml を作成する
1. パッケージしてリリースする
1. 確認する
- 実行環境
- タイムアウト値
- 環境変数
- 関数URL

### Socket ModeからAWS Lambdaに切り替える
1. モードの切り替え
1. 関数URLを認証する
