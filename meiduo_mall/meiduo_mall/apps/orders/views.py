import json
from decimal import Decimal

from django import http
from django.shortcuts import render
from django.utils import timezone
# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredJSONMixin,LoginRequiredMixin
from orders.models import OrderInfo, OrderGoods
from users.models import Address

class OrderSuccessView(LoginRequiredMixin, View):
    """提交订单成功页面"""

    def get(self,request):
        """提供提交订单成功页面"""
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        return render(request, 'order_success.html', context)

class OrderCommitView(LoginRequiredJSONMixin, View):
    """提交订单"""

    def post(self, request):
        """保存订单基本信息和订单商品信息"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        # 校验参数
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
            # 判断address_id是否合法
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('参数address_id错误')
        # 判断pay_method是否合法
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

        # 获取登陆用户
        user = request.user
        # 获取订单编号：时间+user_id=='20200213201713000000001'

        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        #保存订单基本信息（多）
        order = OrderInfo.objects.create(
            order_id=order_id,
            user=user,
            address=address,
            total_count=0,
            total_amount=Decimal(0.00),
            freight=Decimal(10.00),
            pay_method=pay_method,
            # status = 'UNPAID' if pay_method=='ALIPAY' else 'UNSEND'
            status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else OrderInfo.ORDER_STATUS_ENUM['UNSEND']
        )

        # 保存订单商品信息（多）
        # 查询redis购物车中被勾选的商品
        redis_conn = get_redis_connection('carts')
        # 所有的购物车数据，包含了勾选和未勾选 ：{b'1': b'1', b'2': b'2'}
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        # 被勾选的商品的sku_id：[b'1']
        redis_selected = redis_conn.smembers('selected_%s' % user.id)

        # 构造购物车中被勾选的商品的数据 {b'1': b'1'}
        new_cart_dict = {}
        for sku_id in redis_selected:
            new_cart_dict[int(sku_id)] = int(redis_cart[sku_id])

        # 获取被勾选的商品的sku_id
        sku_ids = new_cart_dict.keys()
        for sku_id in sku_ids:
            # 读取购物车商品信息
            sku = SKU.objects.get(id=sku_id)  # 查询商品和库存信息时，不能出现缓存，所以没用filter(id__in=sku_ids)

            #获取想要提交的商品的数量
            sku_count = new_cart_dict[sku_id]
            #判断商品数量是否大于库存，如果大于，响应库存不足
            if sku_count > sku.stock:
                 return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

            # SKU 减库存，加销量
            sku.stock -= sku_count
            sku.sales += sku_count
            try:
                sku.save()
            except:
                print("保存成功，但处理有异常")

            # SPU 加销量
            sku.spu.sales += sku_count
            sku.spu.save()

            OrderGoods.objects.create(
                order = order,
                sku = sku,
                count = sku_count,
                price = sku.price
            )

            #累加订单商品的数量和总价到订单基本信息表
            order.total_count += sku_count
            order.total_count += sku_count * sku.price

        # 最后再加运费
        order.total_count += order.freight
        order.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'order_id': order_id})



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