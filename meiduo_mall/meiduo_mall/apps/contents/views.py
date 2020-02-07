from django.shortcuts import render
from django.views import View
from goods.models import GoodsChannelGroup,GoodsChannel,GoodsCategory#组别，一级分类，详细分类
from _collections import OrderedDict
from contents.models import Content,ContentCategory  #广告类别，内容
# Create your views here.


class IndexView(View):
    """首页广告"""

    def get(self, request):
        """提供首页广告页面"""
        # 查询并展示所有的商品分类
        #准备商品分类对应的字典
        # categories = {}
        categories = OrderedDict()# 有序·字典
        #查询所有的商品频道：37个一级分类
        # channels = GoodsChannel.objects.all()  # tb_goods_channel,无序

        # channels = GoodsChannel.objects.all().order_by('group_id','sequence')  # tb_goods_channel,有序

        channels = GoodsChannel.objects.order_by('group_id','sequence')  # tb_goods_channel,有序，简写
        # 遍历所有的频道
        for channel in channels:
            # 获取当前频道所在组
            group_id = channel.group_id
            #构造基本的数据框架,11个组
            if group_id not in categories:
                categories[group_id] = {'channels':[],'sub_cats':[]}

            cat1 = channel.category  # 当前频道的类别
            # 将cat1添加到channels
            categories[group_id]['channels'].append({
                'id':cat1.id,
                'name':cat1.name,
                'url':channel.url
            })
            # 查询二级和三级
            for cat2 in cat1.subs.all(): # 从一级类别找二级类别 cat2:生活服务
                cat2.sub_cats = [] # 给二级类别找一个三级类别的列表
                for cat3 in cat2.subs.all(): # 从二级类别找三级类别 cat3：代理代办
                    cat2.sub_cats.append(cat3)

                # 将二级类别添加到一级类别的sub_ats
                categories[group_id]['sub_cats'].append(cat2)

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