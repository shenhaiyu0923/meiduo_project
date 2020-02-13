from decimal import Decimal

from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.views import LoginRequiredJSONMixin,LoginRequiredMixin
from users.models import Address


class OrderSettlementView(LoginRequiredMixin, View):
    """结算订单"""

    def get(self, request):
        """查询并展示要结算的订单数据"""
        # 获取登录用户
        user = request.user

        # 查询用户收货地址，查询登陆用户的没有被删除的地址
        try:
            addresses = Address.objects.filter(user=user,is_deleted=False)
        except Exception as e:
            # 如果无地址，可以去编辑地址
            addresses = None

        # 查询redis购物车中被勾选中的商品
        redis_conn = get_redis_connection('carts')
        # 所有的购物车数据，包含了勾选和未勾选 ：{b'1': b'1', b'2': b'2'}
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        # 被勾选的商品的sku_id：[b'1']
        redis_selected = redis_conn.smembers('selected_%s' % user.id)
        #构造购物车中被勾选的商品的数据 {b'1': b'1'}
        new_cart_dict= {}
        for sku_id in redis_selected:
            new_cart_dict[int(sku_id)] = int(redis_cart[sku_id])

        # 获取被勾选的商品的sku_id

        sku_ids = new_cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        total_count = 0
        total_amount = Decimal(0.00)
        #取出所有的sku
        for sku in skus:
            # 遍历skus给每个sku补充count(数量)和amount（小计）
            sku.count = new_cart_dict[sku.id]
            sku.amount = sku.price * sku.count  # Decimal类型的

            # 累加数量和金额
            total_count += sku.count
            total_amount += sku.amount # 类型不同不能运算

        # 指定默认的邮费
        freight = Decimal(10.00)

        # 构造上下文
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight,
        }

        return render(request, 'place_order.html', context)