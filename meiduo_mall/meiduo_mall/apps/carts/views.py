from django.shortcuts import render
from django import http
from django.views import View
from goods.models import SKU
import json
# Create your views here.

class CartsView(View):
    '''购物车管理'''
    def post(self,request):
        '''保存购物车'''
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')

        # 校验参数
        #判断参数是否齐全
        if not all(sku_id,count):
            return http.HttpResponseForbidden('缺少必填参数')
        try:
            SKU.objects.get(sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')
        # 校验是否收是数字
        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count错误')
        # 校验是否被勾选：bool
        if selected:
            if isinstance(selected,bool):
                return http.HttpResponseForbidden('参数selected错误')

        # 判断用户是否登陆

        # 如果用户已登陆，操作redis购物车

        # 如果未登陆，操作cookie购物车

        # 响应结果
        pass