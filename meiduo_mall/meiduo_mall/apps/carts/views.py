import base64
import pickle

from django.shortcuts import render
from django import http
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
import json
# Create your views here.
from meiduo_mall.utils.response_code import RETCODE


class CartsView(View):
    '''购物车管理'''
    def post(self,request):
        '''保存购物车'''
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected',True)

        # 校验参数
        #判断参数是否齐全
        if not all([sku_id,count]):
            return http.HttpResponseForbidden('缺少必填参数')
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')
        # 校验是否收是数字
        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count错误')
        # 校验是否被勾选：bool
        if selected:
            if not isinstance(selected,bool):
                return http.HttpResponseForbidden('参数selected错误')

        # 判断用户是否登陆
        user = request.user
        if user.is_authenticated:
            # 如果用户已登陆，操作redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 需要以增量计算的形式保存商品数量
            pl.hincrby('carts_%s' % user.id,sku_id,count)
            # 保存商品勾选状态
            if selected:
                pl.sadd('selected_%s' % user.id,sku_id)
            # 执行
            pl.execute()
            # 响应结果
            return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})
            pass
        else:
            # 如果用户未登录，操作cookie购物车
            # 获取cookie中的购物车数据，并且判断是否有购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                # 将 cart_str转成bytes类型的字符串
                cart_str_bytes = cart_str.encode()
                # 将cart_str_bytes转成bytes类型的字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_dict_bytes)
            else:
                cart_dict = {}

            # 判断当前要添加的商品在cart_dict中是否存在
            if sku_id in cart_dict:
                # 购物车已存在，增量计算
                origin_count = cart_dict[sku_id]['count']
                count += origin_count

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 将cart_dict转成bytes类型的字典
            cart_dict_bytes = pickle.dumps(cart_dict)
            # 将cart_dict_bytes转成bytes类型的字符串
            cart_str_bytes = base64.b64encode(cart_dict_bytes)
            # 将cart_str_bytes转成字符串
            cookie_cart_str = cart_str_bytes.decode()

            # 将新的购物车数据写入到cookie
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
            response.set_cookie('carts', cookie_cart_str)

            # 响应结果
            return response