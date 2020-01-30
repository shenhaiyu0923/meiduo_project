from django.conf.urls import url

from . import views


urlpatterns = [
    # 省市区三级联动: '/'
    url(r'^areas/$', views.Areasview.as_view(), name='areas'),
]