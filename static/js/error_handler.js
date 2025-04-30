/**
 * エラーハンドリングのための共通JavaScript関数
 */

// フラッシュメッセージを表示するための関数
function showFlashMessage(message, category = 'info', duration = 5000) {
    const flashContainer = document.querySelector('.flash-messages') || createFlashContainer();
    const messageElement = document.createElement('li');
    messageElement.className = category;
    messageElement.textContent = message;
    
    flashContainer.appendChild(messageElement);
    
    // 一定時間後にメッセージを消す
    setTimeout(() => {
        messageElement.style.opacity = '0';
        setTimeout(() => {
            messageElement.remove();
            if (flashContainer.children.length === 0) {
                flashContainer.style.display = 'none';
            }
        }, 300);
    }, duration);
}

// フラッシュメッセージのコンテナを作成
function createFlashContainer() {
    const container = document.createElement('ul');
    container.className = 'flash-messages';
    document.body.insertBefore(container, document.body.firstChild);
    return container;
}

// APIエラーを処理する関数
async function handleApiError(response) {
    if (!response.ok) {
        let errorMessage;
        try {
            const data = await response.json();
            errorMessage = data.error || '予期せぬエラーが発生しました。';
        } catch (e) {
            errorMessage = '通信エラーが発生しました。';
        }
        showFlashMessage(errorMessage, 'danger');
        throw new Error(errorMessage);
    }
    return response;
}

// フォームのバリデーションエラーを処理する関数
function handleFormValidationError(form, errors) {
    // 既存のエラー表示をクリア
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
    
    // 各エラーメッセージを表示
    Object.entries(errors).forEach(([field, message]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('error-field');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = message;
            input.parentNode.insertBefore(errorDiv, input.nextSibling);
        }
    });
}

// ネットワークエラーを処理する関数
function handleNetworkError() {
    showFlashMessage('ネットワーク接続エラーが発生しました。', 'danger');
}

// グローバルエラーハンドラーの設定
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showFlashMessage('予期せぬエラーが発生しました。', 'danger');
});

// Promiseの未処理エラーを捕捉
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showFlashMessage('非同期処理でエラーが発生しました。', 'danger');
});

// フォームのバリデーション関数
function validateForm(formElement) {
    const errors = {};
    
    // 必須フィールドのチェック
    formElement.querySelectorAll('[required]').forEach(input => {
        if (!input.value.trim()) {
            errors[input.name] = `${input.getAttribute('data-label') || input.name}は必須です。`;
        }
    });
    
    // 数値フィールドのチェック
    formElement.querySelectorAll('[type="number"]').forEach(input => {
        if (input.value) {
            const min = parseInt(input.getAttribute('min'));
            const max = parseInt(input.getAttribute('max'));
            const value = parseInt(input.value);
            
            if (isNaN(value)) {
                errors[input.name] = '数値を入力してください。';
            } else if (min !== null && value < min) {
                errors[input.name] = `${min}以上の値を入力してください。`;
            } else if (max !== null && value > max) {
                errors[input.name] = `${max}以下の値を入力してください。`;
            }
        }
    });
    
    return errors;
}

// エクスポート
window.ErrorHandler = {
    showFlashMessage,
    handleApiError,
    handleFormValidationError,
    handleNetworkError,
    validateForm
}; 