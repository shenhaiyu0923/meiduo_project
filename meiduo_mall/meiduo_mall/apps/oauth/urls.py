from django.conf.urls import url

# from .views import RegisterView
from . import views
urlpatterns = [

    #提供QQ登陆扫码页面
    url(r'^qq/login/$', views.QQAuthURLView.as_view()),
    #处理qq登陆回调
    url(r'^oauth_callback/$', views.QQAuthUserView.as_view()),#这个url不能变，是qq返回回来的地址
]