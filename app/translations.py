"""
メッセージの多言語対応を管理するモジュール
"""

# 日本語メッセージ
ja = {
    'errors': {
        'unexpected': '予期せぬエラーが発生しました。',
        'db_error': 'データベース操作中にエラーが発生しました。',
        'invalid_input': '入力値が不正です。',
        'permission_denied': '権限がありません。',
        'not_found': '指定されたリソースが見つかりません。',
        'login_required': 'ログインが必要です。',
        'invalid_password': 'パスワードが正しくありません。',
        'password_mismatch': '確認用パスワードが一致しません。',
        'password_too_short': 'パスワードは6文字以上必要です。',
        'invalid_period': '時間目は1から8の間で指定してください。',
        'title_required': '課題名は必須です。',
        'subject_exists': '既に登録済みの教科です。',
        'subject_name_required': '教科名を入力してください。',
        'task_create_failed': '課題の登録中にエラーが発生しました。',
        'task_update_failed': '課題の更新中にエラーが発生しました。',
        'task_delete_failed': '課題の削除中にエラーが発生しました。',
        'too_many_attempts': 'パスワード変更の試行回数が多すぎます。再度ログインしてください。'
    },
    'success': {
        'password_changed': 'パスワードを変更しました。新しいパスワードで再度ログインしてください。',
        'task_created': '新しい課題を登録しました。',
        'task_updated': '課題を更新しました。',
        'task_deleted': '課題「{title}」を削除しました。',
        'subject_created': '教科「{name}」を登録しました。',
        'subject_deleted': '教科「{name}」を削除しました。'
    },
    'warnings': {
        'debug_mode': 'デバッグモードが有効です。',
        'api_key_required': 'この機能を使用するにはAPIキーの設定が必要です。'
    }
}

# 英語メッセージ（必要に応じて追加）
en = {
    'errors': {
        'unexpected': 'An unexpected error occurred.',
        'db_error': 'A database error occurred.',
        'invalid_input': 'Invalid input.',
        'permission_denied': 'Permission denied.',
        'not_found': 'Resource not found.',
        'login_required': 'Login required.',
        'invalid_password': 'Invalid password.',
        'password_mismatch': 'Passwords do not match.',
        'password_too_short': 'Password must be at least 6 characters.',
        'invalid_period': 'Period must be between 1 and 8.',
        'title_required': 'Title is required.',
        'subject_exists': 'Subject already exists.',
        'subject_name_required': 'Subject name is required.',
        'task_create_failed': 'Failed to create task.',
        'task_update_failed': 'Failed to update task.',
        'task_delete_failed': 'Failed to delete task.',
        'too_many_attempts': 'Too many password change attempts. Please log in again.'
    },
    'success': {
        'password_changed': 'Password changed successfully. Please log in with your new password.',
        'task_created': 'New task created successfully.',
        'task_updated': 'Task updated successfully.',
        'task_deleted': 'Task "{title}" deleted successfully.',
        'subject_created': 'Subject "{name}" created successfully.',
        'subject_deleted': 'Subject "{name}" deleted successfully.'
    },
    'warnings': {
        'debug_mode': 'Debug mode is enabled.',
        'api_key_required': 'API key configuration is required for this feature.'
    }
}

# デフォルトの言語を日本語に設定
current_lang = ja

def get_message(category, key, **kwargs):
    """
    指定されたカテゴリとキーに対応するメッセージを取得します。
    
    Args:
        category (str): メッセージのカテゴリ（'errors', 'success', 'warnings'）
        key (str): メッセージのキー
        **kwargs: メッセージ内の変数を置換するための引数
    
    Returns:
        str: フォーマットされたメッセージ
    """
    try:
        message = current_lang[category][key]
        return message.format(**kwargs) if kwargs else message
    except KeyError:
        return f"Message not found: {category}.{key}" 