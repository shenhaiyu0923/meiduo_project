from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings
from . import constants

def check_access_token(access_token_openid):
    '''
    反解，反序列化access_token_openid
    :param access_token_openid: openid秘文
    :return: access_token_openid：openid 明文
    '''
    # 创建序列化器对象：序列化和反序列化的对象参数必须是一样的
    s = Serializer(settings.SECRET_KEY, constants.ACCESS_TOKEN_EXPIRES)
    # 反序列化openid秘文
    try:
        data = s.loads(access_token_openid)
    except BadData:#openid过期
        return None
    else:
        #返回openid明文
        return data.get('openid')

def generate_access_token(openid):
    '''
    签名，序列化openid
    :param openid: 明文openid
    :return: 密文openid

    '''
    #创建序列化对象
    # s=Serializer('密钥:越负责安全'，'过期时间')
    s = Serializer(settings.SECRET_KEY, constants.ACCESS_TOKEN_EXPIRES)

    #准备呆序列化的字典数据
    data = {'openid':openid}

    #调用dumps方法进行序列化：类型是bytes
    token = s.dumps(data)

    #返回序列化后的数据
    return token.decode()


