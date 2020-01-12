from django.conf.urls import url

# from .views import RegisterView
from . import views

urlpatterns = [
    # 用户注册: reverse(users:register) == '/register/'
    #首页广告
    url(r'^$', views.IndexView.as_view(), name='index'),
]