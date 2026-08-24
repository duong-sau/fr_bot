"""
Xác thực API key/secret của một sàn bằng một lệnh chỉ-đọc (fetch_balance), dựng client
ccxt theo đúng cách ADLControl/Transfer.py đang dựng (apiKey/secret/password +
options['defaultType']='swap') — không tạo lệnh, không chuyển tiền.

Lưu ý quan trọng: KHÔNG dùng fr_ccxt.CCXTWrapper.get_future_account_balance() ở đây.
Wrapper đó thử lần lượt params={'type': 'future'}/'futures'/'swap'/{} để tương thích
nhiều sàn, nhưng với Gate.io, params={'type': 'future'} trả về response "thành công"
toàn None/rỗng MÀ KHÔNG xác thực chữ ký — nghĩa là dùng wrapper đó để verify sẽ báo
"OK" ngay cả với key/secret sai (đã kiểm chứng thủ công). Gọi fetch_balance() thẳng,
không override params, để chắc chắn request đi tới endpoint có ký (signed) và
AuthenticationError được raise đúng khi key sai.
"""
import ccxt


def verify_exchange_credentials(exchange_name: str, api_key: str, api_secret: str, password: str | None = None):
    """
    Trả về (ok: bool, message: str).
    """
    if not api_key or not api_secret:
        return False, "Thiếu api_key/api_secret."

    ex_cls = getattr(ccxt, exchange_name.lower(), None)
    if ex_cls is None:
        return False, f"ccxt không hỗ trợ sàn '{exchange_name}'."

    config = {'apiKey': api_key, 'secret': api_secret, 'enableRateLimit': True}
    if password:
        config['password'] = password

    try:
        client = ex_cls(config)
        client.options['defaultType'] = 'swap'
        client.fetch_balance()
        return True, "OK"
    except ccxt.AuthenticationError as e:
        return False, f"Sai API key/secret/passphrase hoặc thiếu quyền: {e}"
    except ccxt.PermissionDenied as e:
        return False, f"Key thiếu quyền cần thiết (vd Futures/Read): {e}"
    except ccxt.NetworkError as e:
        return False, f"Không kết nối được tới sàn (kiểm tra mạng/IP whitelist): {e}"
    except Exception as e:
        return False, f"Lỗi khi xác thực: {e}"
