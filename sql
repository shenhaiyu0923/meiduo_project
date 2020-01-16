create database meiduo charset=utf8;
create user itheima_it identified by '123456';
grant all on meiduo.* to 'itheima_it'@'%';
flush privileges;