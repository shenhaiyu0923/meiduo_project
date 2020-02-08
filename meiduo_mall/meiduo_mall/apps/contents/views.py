from django.shortcuts import render
from django.views import View
from goods.models import GoodsChannelGroup,GoodsChannel,GoodsCategory#组别，一级分类，详细分类
from _collections import OrderedDict
from contents.models import Content,ContentCategory  #广告类别，内容
from contents.utils import *
# Create your views here.


class IndexView(View):
    """首页广告"""

    def get(self, request):
        """提供首页广告页面"""
        # 查询并展示所有的商品分类
        #准备商品分类对应的字典
        categories = get_categories()

        # 查询首页广告数据
        #查询所有的广告类别
        contents = OrderedDict()
        content_categories= ContentCategory.objects.all()
        for content_category in content_categories:
            # 一查多
            contents[content_category.key] = content_category.content_set.filter(status=True).order_by('sequence')#查询出未下架的广告并排序
            print(contents[content_category.key])
        # 构造上下文
        context = {
            'categories':categories,
            'contents':contents,
        }
        return render(request, 'index.html',context)