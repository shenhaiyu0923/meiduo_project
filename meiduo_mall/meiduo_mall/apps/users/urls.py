from django.conf.urls import url

# from .views import RegisterView
from . import views

urlpatterns = [
    # 用户注册: reverse(users:register) == '/register/'
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
]