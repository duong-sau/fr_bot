from pybitget import Client
import Config


def transfer_from_bitget_main_to_sub(code, amount, fromAccount='swap', toAccount='spot'):
    """
    Transfer USDT from one Bitget account to another Bitget account.
    :param from_account: The user ID of the account to transfer from.
    :param to_account: The user ID of the account to transfer to.
    """
    API_KEY = Config.bitget_api_key
    SECRET_KEY = Config.bitget_api_secret
    PASSPHRASE = Config.bitget_password
    main_account = "8385695013"
    sub_account = "3456170848"
    client = Client(API_KEY, SECRET_KEY, passphrase=PASSPHRASE)

    if fromAccount == 'swap' and toAccount == 'spot':
        fromType = "mix_usdt"
        toType = "spot"
        from_account = sub_account
        to_account = main_account
    elif fromAccount == 'spot' and toAccount == 'swap':
        fromType = "spot"
        toType = "mix_usdt"
        from_account = main_account
        to_account = sub_account
    else:
        raise ValueError("Invalid account types. Use 'swap' and 'spot' only.")
    coin = "USDT"
    if code != "USDT":
        raise ValueError("Only USDT transfers are supported in this function.")
    data = client.spot_sub_transfer(fromType, toType, amount, coin, clientOrderId=None, fromUserId=from_account, toUserId=to_account)
    return data
