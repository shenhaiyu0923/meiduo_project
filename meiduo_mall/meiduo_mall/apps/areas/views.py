from django.shortcuts import render

# Create your views here.
from django.views import View
from areas.models import Area
from django import http
from meiduo_mall.utils.response_code import *
import logging
from django.core.cache import cache  #默认缓存到redis的0号库

logger = logging.getLogger('django')

class Areasview(View):
    '''省市区三级联动'''

    def get(self, request):
        #判断当前是要查询省份数据还是市区数据
        area_id=request.GET.get('area_id')
        if not area_id:
            #判断是否有缓存
            province_list = cache.get('province_list')
            if not province_list:
                #查询省级数据 属性名__条件表达式=值
                try:
                    #Area.objects.filter(parent__isnull=True)
                    province_model_list = Area.objects.filter(parent__isnull=True)#查询的是个集合

                    #需要将模型列表转换成字典列表
                    province_list = []
                    for province_model in province_model_list:
                        province_dict = {
                            'id':province_model.id,
                            'name':province_model.name
                        }
                        province_list.append(province_dict)


                    #缓存省份字典列表数据
                    #cache.set('key', 内容, 有效期)
                    cache.set('province_list', province_list, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '查询省份数据错误'})
            # 响应省级Json数据
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:
            # 读取市或区缓存数据
            sub_data = cache.get('sub_area_' + area_id)
            if not sub_data:
                #查询城市或区县数据
                try:
                    patent_model = Area.objects.get(id = area_id)
                    #patent_model.atea_set.all()  # 一查多
                    sub_model_list = patent_model.subs.all()  # 一查多,自定义
                    #将子级模型列表转换成字典列表
                    subs = []
                    for sub_model in sub_model_list:
                        sub_dict = {
                            'id':sub_model.id,
                            'name':sub_model.name
                        }
                        subs.append(sub_dict)
                    #构造子级JSON数据
                    sub_data={
                        'id':patent_model.id,
                        'name':patent_model.name,
                        'subs':subs
                    }
                    #缓存地区数据
                    cache.set('sub_area_' + area_id, sub_data, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '查询城市或区县数据错误'})
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})
