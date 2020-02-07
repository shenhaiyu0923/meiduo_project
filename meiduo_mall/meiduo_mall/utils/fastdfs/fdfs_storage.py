from django.conf import settings
from django.core.files.storage import Storage
from meiduo_mall.settings.dev import FDFS_BASE_URL
class FastDFSStorage(Storage):
    '''自定义文件存储类'''
    def __init__(self, fdfs_base_url=None):
        # if not fdfs_base_url:
        #     self.fdfs_base_url = settings.FDFS_BASE_URL
        # self.fdfs_base_url = fdfs_base_url
        self.fdfs_base_url =fdfs_base_url or settings.FDFS_BASE_URL

    def _open(self,name,mode='rb'):
        '''
        打开文件时会被调用的，文档告诉我必须重写
        :param name: 文件路径
        :param mode: 文件打开方式
        :return: None
        '''
        # 因为当前不是去打开某个文件，所以这个方法目前无用，但又必须重写，所以pass

        pass

    def _safe(self,name,content):
        '''
        PS：将来后台管理系统，需要在这个方法中实现上传文件到fastDFS服务器中
        保存文件时会被调用的，文档告诉我必须重
        :param name: 文件路径
        :param content: 文件二进制内容
        :return: None
        '''
        # 因为当前不是去打开某个文件，所以这个方法目前无用，但又必须重写，所以pass
        pass

    # def url(self,name):
    #     '''
    #     返回文件的全路径
    #     :param name: 文件相对路径
    #     :return: 文件的全路径
    #     '''
    #     return settings.FDFS_BASE_URL+name
    #     #return FDFS_BASE_URL + name
    #     pass

    def url(self,name):
        '''
        返回文件的全路径
        :param name: 文件相对路径
        :return: 文件的全路径
        '''
        return self.fdfs_base_url+name
        #return FDFS_BASE_URL + name