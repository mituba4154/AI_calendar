#課題管理webアプリ

#構成

flask+python

flask create-user メールアドレス　でアカウントを作れます

それ以外の使い方？しらん
UIみてフィーリングで頑張れ


まとめ
app/init.py（CSRF有効化）

app/routes.py（ブルートフォース対策）

templates/login.htmlなどのフォーム（{{ csrf_token() }}追加）