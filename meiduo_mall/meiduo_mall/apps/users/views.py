from django.shortcuts import render
from django.views import View

# Create your views here.


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """提供用户注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """实现用户注册业务逻辑"""
        pass