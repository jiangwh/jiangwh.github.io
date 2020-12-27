# elasticsearch

## code snapshot

```java
//设置全局的异常处理handle
Thread.setDefaultUncaughtExceptionHandler(new ElasticsearchUncaughtExceptionHandler());
```



```bash
# segment merge 操作可以真正删除delete文档占用的空间（refresh）
```

