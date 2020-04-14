# Spring data mongo 审计

## 简单的示例

SpringBoot启动类上面增加
```java
@EnableMongoAuditing
```


对应实体上面的字段增加对应审计注解信息
```java
@CreatedBy //创建者
@LastModifiedBy //最后修改者
@CreatedDate	//创建时间
@LastModifiedDate	//最后修改时间
```

审计指定了创建者,那么需要AuditorAware提供操作用户信息。

```java
	@Bean
	public AuditorAware<Object> getAuditorProvider() {
		return new AuditorAware() {
			@Override
			public Optional getCurrentAuditor() {
				String oper = ""
				return Optional.of(oper);
			}
		};
	}
```

## 相关过程分析

1、使用

2、spring代理

3、

```java
/*
public class MongoTemplate implements MongoOperations, ApplicationContextAware, IndexOperationsProvider {
*/
protected <T> T doSave(String collectionName, T objectToSave, MongoWriter<T> writer) {
		//将保存的对象发布事件
		objectToSave = maybeEmitEvent(new BeforeConvertEvent<>(objectToSave, collectionName)).getSource();

		AdaptibleEntity<T> entity = operations.forEntity(objectToSave, mongoConverter.getConversionService());
		entity.assertUpdateableIdIfNotSet();

		MappedDocument mapped = entity.toMappedDocument(writer);
		Document dbDoc = mapped.getDocument();

		maybeEmitEvent(new BeforeSaveEvent<>(objectToSave, dbDoc, collectionName));
		Object id = saveDocument(collectionName, dbDoc, objectToSave.getClass());

		T saved = populateIdIfNecessary(entity.getBean(), id);
		maybeEmitEvent(new AfterSaveEvent<>(saved, dbDoc, collectionName));

		return saved;
	}
```

审计监听器中，增加对象转换方法
```java
/*public class AuditingEventListener implements ApplicationListener<BeforeConvertEvent<Object>>, Ordered {
*/
	@Override
	public void onApplicationEvent(BeforeConvertEvent<Object> event) {
    //接受保存对象事件，并增加审计信息。
		event.mapSource(it -> auditingHandlerFactory.getObject().markAudited(it));
	}
```

通过MappingMetadataAuditableBeanWrapper类动态增加审计信息。
```java
/*
public class MappingAuditableBeanWrapperFactory extends DefaultAuditableBeanWrapperFactory {
*/
		@Override
		public Object setCreatedBy(Object value) {

			metadata.createdByPaths.forEach(it -> this.accessor.setProperty(it, value));

			return value;
		}

		@Override
		public Object setLastModifiedBy(Object value) {
			return setProperty(metadata.lastModifiedByPaths, value);
		}

			@Override
		public TemporalAccessor setLastModifiedDate(TemporalAccessor value) {
      //设置最后修改时间
			return setDateProperty(metadata.lastModifiedDatePaths, value);
		}
```


