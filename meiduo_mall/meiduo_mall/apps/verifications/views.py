import random,logging
from django.views import View
from django_redis import get_redis_connection
from django import http
from celery_tasks.sms import constants
from verifications.libs.captcha.captcha import captcha
from meiduo_mall.utils.response_code import *
from celery_tasks.sms.tasks import send_sms_code
# Create your views here.
# 创建日志输出器
logger = logging.getLogger('django')
class SMSCodeView(View):
    '''短信验证码'''
    def get(self,request,mobile):
        '''
        :param request:请求对象
        :param mobile: 手机号
        :return: JSON
        '''
        #接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        #校验参数
        if not ([image_code_client,uuid]):
            return http.HttpResponseForbidden('缺少必传参数')

        #创建连接到redis的对象
        redis_conn = get_redis_connection('verify_code')

        # 判断用户是否频繁发送短信验证码
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})

        # 提取图像验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图形验证码失效'})#返回4001
        # 删除图形验证码,避免恶意测试
        redis_conn.delete('img_%s' % uuid)
        #对比图形验证码
        image_code_server = image_code_server.decode()#将bytes转字符串,再比较
        if image_code_server.lower()!=image_code_client.lower():#先转小写,再比较
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'输入图片验证码有误'})

        #生成短信验证码:6位随机数字
        sms_code = '%06d' % random.randint(0,999999)
        #创建日志生成器
        logger = logging.getLogger('django')
        logger.info(sms_code) # 手动的输出日志,记录短信验证码

        # #保存短信验证码
        # redis_conn.setex('sms_%s' % mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        # # 重新写入send_flag
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 创建redis管道
        pl = redis_conn.pipeline()
        # 将命令添加到队列中
        # 保存短信验证码
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行
        pl.execute()


        #发送短信验证码
        #CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES//60],constants.SEND_SMS_TEMPLATE_ID)
        send_sms_code.delay(mobile, sms_code)  # 千万不要忘记写delay

        # 响应结果
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg': '发送短信成功'})



class ImageCodeView(View):
    """图形验证码"""

    def get(self, request, uuid):
        """
        :param uuid: 通用唯一识别码，用于唯一标识该图形验证码属于哪个用户的
        :return: image/jpg
        """
        # 实现主体业务逻辑：生成，保存，响应图形验证码
        # 生成图形验证码
        text, image = captcha.generate_captcha()

        # 保存图形验证码
        redis_conn = get_redis_connection('verify_code')
        # redis_conn.setex('key', 'expires', 'value')
        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        print("图形验证码是:  "+text)

        # 响应图形验证码
        return http.HttpResponse(image, content_type='image/jpg')