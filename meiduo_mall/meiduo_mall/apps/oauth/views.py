from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django import http

from carts.utils import merge_carts_cookies_redis
from meiduo_mall.utils.response_code import RETCODE
from oauth.models import OAuthQQUser
import logging,re
from django_redis import get_redis_connection
from oauth.utils import generate_access_token,check_access_token
from users.models import User
#创建日志输出器


logger = logging.getLogger('django')

class QQAuthUserView(View):

    '''处理qq登陆回调  oauth_callback'''
    def get(self,request):
        #处理qq登陆，获取code
        code = request.GET.get('code')
        if not code:
            return http.HttpResponseForbidden('获取code失败')

        try:
            #使用code获取access_token
            #创建工具对象
            oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET, redirect_uri=settings.QQ_REDIRECT_URI)
            #使用code获取access_token
            access_token = oauth.get_access_token(code)
            #使用access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0认证失败')
        try :
            # 使用openid判断该用户qq有没有绑定梅多商城用户名
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 未绑定,重定向到首页
            access_token_openid = generate_access_token(openid)#使用序列化方法加密
            contest = {'access_token_openid':access_token_openid}

            return render(request, 'oauth_callback.html',contest)
        else :
            # 已绑定,oauth_user.user表示从qq登陆模型类对象中找到对应的用户模型类对象
            login(request,oauth_user.user)
            next = request.GET.get('state')#返回到上一页
            response = redirect(next)
            #将用户名写入到cookies
            response.set_cookie('username',oauth_user.user.username,max_age=3600*24*15)
            # 用户登录成功，合并cookie购物车到redis购物车
            response = merge_carts_cookies_redis(request=request, user=oauth_user.user, response=response)
            #响应qq登陆结果
            return response

    def post(self, request):
        """美多商城用户绑定到openid"""
        # 接收参数
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        access_token_openid = request.POST.get('access_token_openid')

        # 校验参数
        # 判断参数是否齐全
        if not all([mobile, pwd, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', pwd):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断短信验证码是否一致
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg':'无效的短信验证码'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})
        # 判断openid是否有效：错误提示放在sms_code_errmsg位置
        openid = check_access_token(access_token_openid)
        if not openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': 'openid已失效'})

        #使用手机号查询对应的账号是否存在
        try:
            user=User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            #如果不存在
            user = User.objects.create_user(username=mobile,password=pwd,mobile=mobile)
        else:
            if not user.check_password(pwd):
                return render(request,'oauth_callback.html',{'account_errmsg':'账号或密码错误'})
        try:
            oauth_qq_user=OAuthQQUser.objects.create(user=user,openid=openid)
        except Exception as e:
            logger.error(e)
            return render(request,'oauth_callback.html',{'qq_login_errmsg':'绑定失败'})
        #如果存在，需要校验密码
        login(request, oauth_qq_user.user)
        next = request.GET.get('state')
        response = redirect(next)
        # 将用户名写入到cookies
        response.set_cookie('username', oauth_qq_user.user.username, max_age=3600 * 24 * 15)

        # 用户登录成功，合并cookie购物车到redis购物车
        response = merge_carts_cookies_redis(request=request, user=user, response=response)

        # 响应qq登陆结果
        return response


class QQAuthURLView(View):#这个请求会生成code
    '''提供qq登陆扫码页面'''

    def get(self,request):
        #接受next
        next = request.GET.get('next')

        #创建工具类
        oauth=OAuthQQ(client_id=settings.QQ_CLIENT_ID,client_secret=settings.QQ_CLIENT_SECRET,redirect_uri=settings.QQ_REDIRECT_URI,state=next)

        #生成QQ登陆扫码链接地址
        login_url=oauth.get_qq_url()

        #响应
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','login_url':login_url})

