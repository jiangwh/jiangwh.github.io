#  性能优化

```js
"mlockall": true //es禁止使用swap


sudo swapoff -a //禁止服务器使用swap

sysctl -w vm.max_map_count=262144 //设置可以映射文件的数量

```



# 维护操作

## 索引操作

1、索引合并

```java
PUT http://ip:port/_reindex
{
	"source":{
		"index":["indexname1","indexname2"]
	},
	"dest":{
		"index":"dstIndex"
	}
}
```

2、索引冻结

```java
POST http://ip:port/<index>/_freeze
```

3、索引别名



## 备份维护

1、备份数据



2、恢复数据



