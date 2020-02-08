from django import http
from django.shortcuts import render
from contents.utils import *
# Create your views here.
from goods.models import GoodsCategory
from django.views import View

class ListView(View):
    '''商品列表页'''
    def get(self,request,category_id,page_num):
        '''查询并渲染商品列表页'''

        # 校验category_id的范围
        try:
            GoodsCategory.objects.get(id = category_id)
        except GoodsCategory.DoesNotexist:
            return http.HttpResponseForbidden('参数category_id不存在')

        # 查询商品分类
        categories = get_categories()

        # 构造上下文
        contents = {
            'categories':categories
        }
        return render(request,'list.html',contents)