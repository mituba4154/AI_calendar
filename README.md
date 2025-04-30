# スクールタスクプランナー

## 概要

学校の課題・タスク・教科を一元管理できるWebアプリケーションです。

*   レスポンシブデザインでPC/スマホ両対応。
*   ユーザー管理はCLIコマンドで行います（Webからの新規登録はできません）。
*   セキュリティ・運用・拡張性を考慮した設計です。

## ディレクトリ構成

```text
.
├── app.py                  # Flaskアプリ起動スクリプト
├── app/
│   ├── __init__.py         # アプリファクトリ・CLIコマンド
│   ├── config.py           # 設定
│   ├── extensions.py       # DB初期化
│   ├── forms.py            # WTForms（未使用の場合あり）
│   ├── models.py           # DBモデル
│   ├── routes.py           # ルーティング・Webロジック
│   ├── utils.py            # ユーティリティ
│   └── templates/          # HTMLテンプレート
│       ├── dashboard.html
│       ├── tasks.html
│       ├── ...
│   └── static/
│       └── style.css       # CSS（レスポンシブ・一貫デザイン）
├── instance/
│   └── database.db         # SQLite DB（.gitignore推奨）
├── requirements.txt        # 必要パッケージ
├── .gitignore              # DB・環境ファイル除外
├── README.md               # このファイル
├── start.bat/.sh           # 起動スクリプト
├── stop.bat/.sh            # 停止スクリプト
├── install.bat/.sh         # セットアップスクリプト
└── その他ログ/設定ファイル

セットアップ方法
仮想環境の作成・有効化
python -m venv venv
Use code with caution.
Bash
Windowsの場合:
venv\Scripts\activate
Use code with caution.
Bash
macOS/Linuxの場合:
source venv/bin/activate
Use code with caution.
Bash
パッケージインストール
pip install -r requirements.txt
Use code with caution.
Bash
データベース初期化
初回起動時に instance/database.db が自動で作成されます。
サーバー起動
Windowsの場合:
start.bat
Use code with caution.
Bash
macOS/Linuxの場合:
sh start.sh
Use code with caution.
Bash
または、直接実行:
python app.py
Use code with caution.
Bash
デフォルトで http://localhost:53833 でアクセスできます。
ユーザー管理（CLIコマンド）
ユーザー作成
flask create-user メールアドレス
Use code with caution.
Bash
例:
flask create-user user@example.com
Use code with caution.
Bash
パスワード入力を求められます（6文字以上）。
ユーザー一覧
flask list-users
Use code with caution.
Bash
ユーザー削除
flask delete-user メールアドレス
Use code with caution.
Bash
主な機能
ダッシュボード: 期限が近い課題を表示、AIによるおすすめ機能（APIキー設定時）。
課題一覧: テーブル形式表示。スマートフォンではカード形式表示に自動で切り替え。
課題管理: 課題の登録、編集、削除機能。
教科管理: 教科の追加、削除機能。
カレンダー: FullCalendarライブラリを使用した課題の視覚的な表示。
設定: パスワード変更、AI機能のためのAPIキー設定案内。
レスポンシブUI: スマートフォン、タブレット、PCなど、様々な画面サイズで快適に利用可能。
セキュリティ・運用上の注意
CSRF保護: 現在は意図的に無効化されています（テンプレートから {{ csrf_token() }} は削除済み）。必要に応じて Flask-WTF などを導入してください。
パスワード: データベースにはハッシュ化されたパスワードが保存されます。
SECRET_KEY: 本番環境で運用する際は、app/config.py 内の SECRET_KEY を必ず推測困難で安全な値に変更してください。
HTTPS: 本番運用時はHTTPS化を強く推奨します。HTTPS化後に app/config.py で SESSION_COOKIE_SECURE=True を設定してください。
データベースファイル: instance/database.db は .gitignore に含まれており、Gitリポジトリには含まれません。
アカウント登録: Webインターフェースからの新規アカウント登録はできません。管理者がCLIコマンドを使用してユーザーを作成する必要があります。
よくある質問
Q. DBファイルをGitに含めたくない
A. .gitignore ファイルに instance/database.db の行を追加してください（デフォルトで追加済みのはずです）。
Q. スマートフォンでUI表示が崩れる
A. app/static/style.css を最新版に置き換えて、ブラウザのキャッシュをクリアしてみてください。
Q. ログイン試行回数制限やCSRF対策を強化したい
A. Flask-Limiter や Flask-WTF といったFlask拡張機能の導入を検討してください。これらを利用するには、コードの追加・修正が必要です。