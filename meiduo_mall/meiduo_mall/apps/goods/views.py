from datetime import datetime

from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django import http
# 分页器（有100万文字，需要制作成为一本书，先规定每页多少文字，然后得出一共多少页）
# 数据库中的记录就是文字，我们需要考虑在分页时每页记录的条数，然后得出一共多少页
from django.core.paginator import Paginator, EmptyPage
from meiduo_mall.utils.fastdfs.fdfs_storage import FastDFSStorage
from goods.models import GoodsCategory
from contents.utils import get_categories
from goods.utils import get_breadcrumb
from goods.models import SKU,GoodsVisitCount
# Create your views here.
from meiduo_mall.utils.response_code import RETCODE

class DetailVisitView(View):
    """统计分类商品的访问量"""

    def post(self, request, category_id):
        # 接收参数和校验参数
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('category_id 不存在')

        # 获取当天的日期
        t = timezone.localtime()
        # 获取当天的时间字符串
        today_str = '%d-%02d-%02d' % (t.year, t.month, t.day)
        # 将当天的时间字符串转成时间对象datetime，为了跟date字段的类型匹配 2019:05:23  2019-05-23
        today_date = datetime.strptime(today_str, '%Y-%m-%d') # 时间字符串转时间对象；datetime.strftime() # 时间对象转时间字符串

        # 判断当天中指定的分类商品对应的记录是否存在
        try:
            # 如果存在，直接获取到记录对应的对象
            counts_data = GoodsVisitCount.objects.get(date=today_date, category=category)
            print(counts_data)
        except GoodsVisitCount.DoesNotExist:
            # 如果不存在，直接创建记录对应的对象
            counts_data = GoodsVisitCount()

        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.date = today_date
            counts_data.save()
        except Exception as e:
            return http.HttpResponseServerError('统计失败')

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class DetailView(View):
    """商品详情页"""

    def get(self, request, sku_id):
        """提供商品详情页"""
        # 接收和校验参数
        try:
            # 查询sku
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            # return http.HttpResponseNotFound('sku_id 不存在')
            return render(request, '404.html')

        # 查询商品分类
        categories = get_categories()

        # 查询面包屑导航
        breadcrumb = get_breadcrumb(sku.category)

        # 构建当前商品的规格键
        sku_specs = sku.specs.order_by('spec_id')
        sku_key = []
        for spec in sku_specs:
            sku_key.append(spec.option.id)
        # 获取当前商品的所有SKU
        skus = sku.spu.sku_set.all()
        # 构建不同规格参数（选项）的sku字典
        spec_sku_map = {}
        for s in skus:
            # 获取sku的规格参数
            s_specs = s.specs.order_by('spec_id')
            # 用于形成规格参数-sku字典的键
            key = []
            for spec in s_specs:
                key.append(spec.option.id)
            # 向规格参数-sku字典添加记录
            spec_sku_map[tuple(key)] = s.id
        # 获取当前商品的规格信息
        goods_specs = sku.spu.specs.order_by('id')
        # 若当前sku的规格信息不完整，则不再继续
        if len(sku_key) < len(goods_specs):
            return
        for index, spec in enumerate(goods_specs):
            # 复制当前sku的规格键
            key = sku_key[:]
            # 该规格的选项
            spec_options = spec.options.all()
            for option in spec_options:
                # 在规格参数sku字典中查找符合当前规格的sku
                key[index] = option.id
                option.sku_id = spec_sku_map.get(tuple(key))
            spec.spec_options = spec_options

        # 构造上下文
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'specs': goods_specs
        }

        return render(request, 'detail.html', context)

class HotGoodsView(View):
    """热销排行"""

    def get(self, request, category_id):
        # 查询指定分类的SKU信息，而且必须是上架的状态，然后按照销量由高到低排序，最后切片取出前两位
        skus = SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[:2]

        # 将模型列表转字典列表，构造JSON数据
        hot_skus = []

        for sku in skus:
            #default_image_url="http://192.168.153.135:8888/"+sku.default_image
            sku_dict = {
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                #'default_image_url':default_image_url
                'default_image_url': sku.default_image.url # 记得要取出全路径
            }
            hot_skus.append(sku_dict)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})

class ListView(View):
    """商品列表页"""

    def get(self, request, category_id, page_num):
        """查询并渲染商品列表页"""

        # 校验参数category_id的范围 ： 1111111111111111111111111111111
        try:
            # 三级类别
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('参数category_id不存在')

        # 获取sort(排序规则): 如果sort没有值，取'default'
        sort = request.GET.get('sort', 'default')
        # 根据sort选择排序字段，排序字段必须是模型类的属性
        if sort == 'price':
            sort_field = 'price' # 按照价格由低到高排序
        elif sort == 'hot':
            sort_field = '-sales' # 按照销量由高到低排序
        else: # 只要不是'price'和'-sales'其他的所有情况都归为'default'
            sort = 'default' # 当出现?sort=itcast 也把sort设置我'default'
            sort_field = 'create_time'

        # 查询商品分类
        categories = get_categories()

        # 查询面包屑导航：一级 -> 二级 -> 三级
        breadcrumb = get_breadcrumb(category)

        # 分页和排序查询：category查询sku,一查多,一方的模型对象.多方关联字段.all/filter
        # skus = SKU.objects.filter(category=category, is_launched=True) # 无经验查询
        # skus = SKU.objects.filter(category_id=category_id, is_launched=True)  # 无经验查询
        # skus = category.sku_set.filter(is_launched=True).order_by('排序字段：create_time,price,-sales') # 有经验查询
        skus = category.sku_set.filter(is_launched=True).order_by(sort_field)  # 有经验查询
        # 创建分页器
        # Paginator('要分页的记录', '每页记录的条数')
        paginator = Paginator(skus, 5) # 把skus进行分页，每页5条记录
        try:
            # 获取到用户当前要看的那一页（核心数据）
            page_skus = paginator.page(page_num) # 获取到page_num页中的五条记录
        except EmptyPage:
            return http.HttpResponseNotFound('Empty Page')
        # 获取总页数：前端的分页插件需要使用
        total_page = paginator.num_pages

        # 构造上下文
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'page_skus':page_skus,
            'total_page':total_page,
            'page_num':page_num,
            'sort':sort,
            'category_id':category_id,
        }

        return render(request, 'list.html', context)
