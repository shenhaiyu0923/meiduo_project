from jinja2 import Environment
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse


def jinja2_environment(**options):
    #jinja2环境{{static('静态文件相对路径')}}  {{url('路由的相对空间')}}

    #创建环境对象
    env = Environment(**options)
    # 自定义语法
    env.globals.update({
        'static': staticfiles_storage.url,#获取静态文件的前缀
        'url': reverse,#反向解析
    })
    return env  #返回环境对象

