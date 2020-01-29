from django.contrib.auth.mixins import LoginRequiredMixin
from django import http
from meiduo_mall.utils.response_code import RETCODE

class LoginRequiredJSONMixin(LoginRequiredMixin):
    '''自定义判断用户是否登陆的扩展类：返回JSON'''

    #只需要重写未登陆部分的操作handle_no_permission

    def handle_no_permission(self):
        return http.JsonResponse({'code':RETCODE.SESSIONERR,'errmsg':'用户未登陆'})


    '''
    class LoginRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
    '''