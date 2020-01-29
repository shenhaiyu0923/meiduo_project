from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django import http
import re,json,logging
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from users.models import User
from meiduo_mall.utils.views import LoginRequiredJSONMixin
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_email
from users.utils import generate_verify_email_url
# Create your views here.

logger=logging.getLogger('django')

class EmailView(LoginRequiredJSONMixin,View):
    '''添加邮箱'''
    def put(self,request):
        #bodu是bytes类型，要转成字符串
        json_str = request.body.decode()
        json_dict=json.loads(json_str)#将json转换成字符串
        email = json_dict.get('email')

        # 校验参数
        if not email:
            return http.HttpResponseForbidden('缺少email参数')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        try:
            #将用户传入的邮箱保存到用户数据库的email字段中
            request.user.email=email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,'errmsg':'添加邮箱失败'})

        #发送邮箱验证
        verify_url = generate_verify_email_url(request.user)
        print(verify_url)
        send_verify_email.delay(email,verify_url)

        #响应结果
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})




# class UserInfoView(View):
#     '''用户中心'''
#     def get(self,request):
#         '''提供用户中心页面'''
#         if request.user.is_authenticated:#django 自带判断用户是否登陆方法
#             return render(request,'user_center_info.html')
#         else:
#             return redirect(reverse('users:login'))




class UserInfoView(LoginRequiredMixin, View):
    '''用户中心'''

    def get(self, request):
        '''提供个人信息页面'''
        '''提供用户中心页面'''
        # if request.user.is_authenticated:#django 自带判断用户是否登陆方法
        #     return render(request,'user_center_info.html')
        # else:
        #     return redirect(reverse('users:login'))
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html', context=context)

#退出登陆
class LogoutView(View):
    '''实现退出登陆'''
    def get(self,request):
        #清除session
        logout(request)
        response = redirect(reverse('contents:index'))
        response.delete_cookie('username')
        return response


class LoginView(View):
    '''用户名登陆'''
    def get(self,request):
        '''
        提供登陆页面
        :param request:请求对象
        :return: 登陆页面
        '''
        return render(request,'login.html')
    def post(self,request):
        '''
        实现登陆逻辑
        :param request: 请求对象
        :return: 登陆结果
        '''
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
        '''校验参数'''
        #判断参数是否齐全
        if not all([username,password]):
            return http.HttpResponseForbidden('缺少必填参数')

        #判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

        #判断密码是否是8-20位数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        #认证用户登陆
        user = authenticate(username=username,password=password)
        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})

        # 状态保持
        login(request, user)
        # 使用remembered确定状态保持周期（实现记住登录）
        if remembered != 'on':
            # 没有记住登录：状态保持在浏览器会话结束后就销毁
            request.session.set_expiry(0) # 单位是秒
        else:
            # 记住登录：状态保持周期为两周:默认是两周
            request.session.set_expiry(None)

        response = redirect(reverse('contents:index'))

        #响应结果
        #先取出next
        next = request.GET.get('next')
        if next:
            #重定向到next
            response=redirect(next)
        else:
            response = redirect(reverse('contents:index'))
        #为了实现右上角显示用户名。需要将用户名写进cookie中
        #response.set-cookie('key',value,'expiry')
        response.set_cookie('username',user.username,max_age=3600 * 24 * 15)#缓存15天

        # 响应结果:重定向到首页
        return response

class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """
        :param mobile: 手机号
        :return: JSON
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class UsernameCountView(View):
    """判断用户名是否重复注册"""

    def get(self, request, username):
        """
        :param username: 用户名
        :return: JSON
        """
        # 实现主体业务逻辑：使用username查询对应的记录的条数(filter返回的是满足条件的结果集)
        count = User.objects.filter(username=username).count()
        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """提供用户注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """实现用户注册业务逻辑"""
        # 接收参数：表单参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 校验参数：前后端的校验需要分开，避免恶意用户越过前端逻辑发请求，要保证后端的安全，前后端的校验逻辑相同
        # 判断参数是否齐全:all([列表])：会去校验列表中的元素是否为空，只要有一个为空，返回false
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        if re.match(r'^\d{1,90}$', username):
            return http.HttpResponseForbidden('用户名不能是纯数字')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        #连接redis数据库
        redis_conn = get_redis_connection('verify_code')
        # 判断短信验证码是否输入正确
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': '短信验证码已失效'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})
        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 保存注册数据：是注册业务的核心
        # return render(request, 'register.html', {'register_errmsg': '注册失败'})
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg':'注册失败'})

        # 实现状态保持
        login(request, user)

        # 响应结果：重定向到首页
        # return http.HttpResponse('注册成功，重定向到首页')
        # return redirect('/')
        # reverse('contents:index') == '/'
        return redirect(reverse('contents:index'))
