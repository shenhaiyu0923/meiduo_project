from django.shortcuts import render
from django.views import View
# Create your views here.

class CartsView(View):
    '''购物车管理'''
    def post(self,request):
        '''保存购物车'''
        # 接收参数

        # 校验参数

        # 判断用户是否登陆

        # 如果用户已登陆，操作redis购物车

        # 如果未登陆，操作cookie购物车

        # 响应结果
        pass