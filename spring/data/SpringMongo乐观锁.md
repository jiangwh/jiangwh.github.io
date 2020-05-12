# Spring Mongo乐观锁

Spring-data-mongo中提供了乐观锁的使用方式

## 简单实例

```java
@Version
```





## 相关实现源码

```java
/*
package org.springframework.data.mongodb.core;
class MongoTemplate
*/
@Override
	@SuppressWarnings("unchecked")
	public <T> T save(T objectToSave, String collectionName) {

		Assert.notNull(objectToSave, "Object to save must not be null!");
		Assert.hasText(collectionName, "Collection name must not be null or empty!");

		AdaptibleEntity<T> source = operations.forEntity(objectToSave, mongoConverter.getConversionService());

		return source.isVersionedEntity() //
				? doSaveVersioned(source, collectionName) //
				: (T) doSave(collectionName, objectToSave, this.mongoConverter);

	}
```



```java
private final Lazy<Boolean> isVersion = Lazy.of(() -> isAnnotationPresent(Version.class));
```



```java
private <T> T doSaveVersioned(AdaptibleEntity<T> source, String collectionName) {

		Number number = source.getVersion();

		if (number != null) {

			// Create query for entity with the id and old version
			Query query = source.getQueryForVersion();

			// Bump version number
			T toSave = source.incrementVersion();

			toSave = maybeEmitEvent(new BeforeConvertEvent<T>(toSave, collectionName)).getSource();

			source.assertUpdateableIdIfNotSet();

			MappedDocument mapped = source.toMappedDocument(mongoConverter);

			maybeEmitEvent(new BeforeSaveEvent<>(toSave, mapped.getDocument(), collectionName));
			Update update = mapped.updateWithoutId();

			UpdateResult result = doUpdate(collectionName, query, update, toSave.getClass(), false, false);

			if (result.getModifiedCount() == 0) {
				throw new OptimisticLockingFailureException(
						String.format("Cannot save entity %s with version %s to collection %s. Has it been modified meanwhile?",
								source.getId(), number, collectionName));
			}
			maybeEmitEvent(new AfterSaveEvent<>(toSave, mapped.getDocument(), collectionName));

			return toSave;
		}

		return (T) doInsert(collectionName, source.getBean(), this.mongoConverter);
	}
```



底层的乐观锁只是保证的更新对象是否是期望的对象，但是没有保证业务上正确性。如果使用这种乐观锁方式，那么需要花费一部分精力处理失败的业务逻辑。