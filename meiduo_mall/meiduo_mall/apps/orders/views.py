from django.shortcuts import render

# Create your views here.
from django.views import View

from meiduo_mall.utils.views import LoginRequiredJSONMixin,LoginRequiredMixin


class OrderSettlementView(LoginRequiredMixin, View):
    """结算订单"""

    def get(self, request):
        """查询并展示要结算的订单数据"""
        # 获取登录用户

        return render(request, 'place_order.html', context=None)