from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django import http
import re,json,logging
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection

from carts.utils import merge_carts_cookies_redis
from goods.models import SKU
from users.models import User, Address
from meiduo_mall.utils.views import LoginRequiredJSONMixin
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_email
from users.utils import generate_verify_email_url,check_verify_email_token
from . import constants
# Create your views here.

logger=logging.getLogger('django')

class UserBrowseHistory(LoginRequiredJSONMixin, View):
    '''用户浏览记录'''
    def post(self,request):
        '''保存商品浏览记录'''
        #接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        sku_id = json_dict.get('sku_id')

        #校验参数
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')

        # 保存sku_id到redis
        redis_conn = get_redis_connection('history')

        user = request.user
        pl = redis_conn.pipeline()
        # 先去重
        pl.lrem('history_%s' % user.id, 0, sku_id)
        # 再保存：最近浏览的商品在最前面
        pl.lpush('history_%s' % user.id, sku_id)
        # 最后截取
        pl.ltrim('history_%s' % user.id, 0, 4)
        # 执行
        pl.execute()

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

    def get(self, request):
        """查询用户商品浏览记录"""
        # 获取登录用户信息
        user = request.user
        # 创建连接到redis对象
        redis_conn = get_redis_connection('history')
        # 取出列表数据（核心代码）
        sku_ids = redis_conn.lrange('history_%s' % user.id, 0, -1) # (0, 4)

        # 将模型转字典
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})

class UpdateTitleAddressView(LoginRequiredJSONMixin,View):
    #更新地址标题
    def put(self,request,address_id):
        '''实现更新地址标题的逻辑'''
        #接收参数title
        json_dict=json.loads(request.body.decode())
        title = json_dict.get('title')
        #校验参数
        if not title:
            return http.HttpResponseForbidden('缺少title')
        #查询当前需要更新标题的地址
        try:
            #将新的标题覆盖给地址标题
            address = Address.objects.get(id=address_id)
            address.title=title
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新标题失败'})

            #响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '更新标题成功'})

class DefaultAddressView(LoginRequiredJSONMixin,View):
    '''设置默认地址'''
    def put(self,request,address_id):
        '''设置默认地址逻辑'''
        try:
            #查询出当前哪个地址作为登陆用户的默认地址
            address=Address.objects.get(id=address_id)
            #将指定地址设置为默认地址
            request.user.default_address=address
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})



class UpdateDestoryAddressView(LoginRequiredMixin,View):
    '''更新和删除地址'''
    def put(self,request,address_id):
        '''更新地址'''
        #接收参数
        json_str=request.body.decode()
        json_dict=json.loads(json_str)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        try:
            #使用最新的地址覆盖指定的旧的地址信息
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,'errmsg':'修改地址失败'})
        #响应新的地址给前端
        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'新增地址成功','address':address_dict})

        pass


    def delete(self,request,address_id):
        '''删除地址'''
        #实现指定地址删除的逻辑  is_delete=True
        try:
            address=Address.objects.get(id=address_id)
            address.is_deleted = True
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})
        #响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})



class AddressCreateView(LoginRequiredJSONMixin,View):
    '''新增地址'''
    def post(self,request):

        '''实现新增地址的逻辑'''
        #判断当前用户地址数量是否超过上限，
        #count = Address.objects.filter(user=request.user).count()
        count = request.user.addresses.count()#一查多，使用related_name查询
        if count > constants.USER_ADDRESS_COUNTS_LIMIT:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'超出用户地址上限'})

        #接收参数
        json_str=request.body.decode()
        json_dict=json.loads(json_str)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')


        #保存用户传入的地址信息
        try:
            address=Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            #如果登陆用户没有默认地址，我们需要指定默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR,'errmsg':'新增地址失败'})

        #响应新增地址结果，需要将新增的地址返回给前端
        # 新增地址成功，将新增的地址响应给前端实现局部刷新
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'新增地址成功','address':address_dict})

class AddressView(LoginRequiredMixin,View):
    '''用户收获地址'''
    def get(self,request):
        '''查询并展示用户地址信息'''

        #获取当前登陆用户对象
        login_user = request.user
        #使用当前登陆用户和is——deleted=false作为条件查询地址数据
        addresses = Address.objects.filter(user=request.user,is_deleted=False)

        #将用户地址模型列表转换成字典列表，因为JsonResponse和Vue.js不认识模型类型。只有django和jinja2模版引擎认识
        address_list = []
        for address in addresses:
            address_dict={
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            address_list.append(address_dict)

        #构造上下文
        context={
            'default_address_id': login_user.default_address_id or '0',#如果没有默认值，用0表示占位符，防止前端报错
            'addresses': address_list,
        }

        return render(request,'user_center_site.html',context)

class VerifyEmailView(View):
    '''验证邮箱'''
    def get(self,request):
        #接收参数
        token = request.GET.get('token')
        #校验参数
        if not token:
            return http.HttpResponseForbidden('缺少必填参数')
        #从token中提取用户信息user_id ==> user
        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseBadRequest('无效的token')
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活失败')

        return redirect(reverse('users:info'))


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


        # 用户登录成功，合并cookie购物车到redis购物车
        response = merge_carts_cookies_redis(request=request, user=user, response=response)
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
