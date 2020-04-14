
# Spring中cache处理

本文以cache在springboot应用使用示例。

备注：本文中所有源码基于spring 5.1.2 版本
## Cache使用方式

一般在spring框架中，可以使用以下几个注解。
```
@Cacheable: Triggers cache population.
@CacheEvict: Triggers cache eviction.
@CachePut: Updates the cache without interfering with the method execution.
@Caching: Regroups multiple cache operations to be applied on a method.
@CacheConfig: Shares some common cache-related settings at class-level.
```
## 简单的示例代码

1、使用@EnableCaching生效Cache

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.annotation.EnableCaching;

@EnableCaching
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class);
    }
}
```

2、cacheManager配置。

```java
    @Bean("cacheManager")
    @Primary
    public CacheManager caffeineCacheManager() {
        SimpleCacheManager cacheManager = new SimpleCacheManager();
        ArrayList<CaffeineCache> caches = new ArrayList<CaffeineCache>();
        Cache cache = Caffeine.newBuilder().recordStats()
                .expireAfterWrite(60 * 60, TimeUnit.SECONDS)
                .maximumSize(100000)
                .build();
        CaffeineCache XCache = new CaffeineCache("Cache01", cache);
        CaffeineCache YCache = new CaffeineCache("Cache02", cache);
        caches.add(XCache);
        caches.add(YCache);
        cacheManager.setCaches(caches);
        return cacheManager;
    }
```

3、使用Cache相关注解

这里对应spring cache使用的注解就不一一举例了。

```java
@Cacheable(value = “cache名字”, key = "#key", cacheManager = "cacheManager")
```



## 缓存的过程

从缓存、获取缓存、失效缓存三个维度来看看spring cache。

### 缓存对象到cache

```java
/* public class CacheInterceptor extends CacheAspectSupport implements MethodInterceptor, Serializable {
*/
@Override
	@Nullable
	public Object invoke(final MethodInvocation invocation) throws Throwable {
    //invocation 是CglibMethodInvocation extends ReflectiveMethodInvocation类型中，在此处包含了调用的方法，参数信息以及对应的bean信息。
		Method method = invocation.getMethod();

		CacheOperationInvoker aopAllianceInvoker = () -> {
			try {
				return invocation.proceed();
			}
			catch (Throwable ex) {
				throw new CacheOperationInvoker.ThrowableWrapper(ex);
			}
		};

		try {
			return execute(aopAllianceInvoker, invocation.getThis(), method, invocation.getArguments());
		}
		catch (CacheOperationInvoker.ThrowableWrapper th) {
			throw th.getOriginal();
		}
	}

```

```java
//把相关信息放入cache中。
protected Object execute(CacheOperationInvoker invoker, Object target, Method method, Object[] args) {
		// Check whether aspect is enabled (to cope with cases where the AJ is pulled in automatically)
		if (this.initialized) {
			Class<?> targetClass = getTargetClass(target);
      //获取所有相关cache注解的class、method信息
			CacheOperationSource cacheOperationSource = getCacheOperationSource();
			if (cacheOperationSource != null) {
        //获取到对应的cache操作，包含该方法信息，cache相关信息
        /*
        caches=[cache名字] | key='' | keyGenerator='' | cacheManager='cacheManager' | cacheResolver='' | condition='' | unless='' | sync='false'
        */
				Collection<CacheOperation> operations = cacheOperationSource.getCacheOperations(method, targetClass);
				if (!CollectionUtils.isEmpty(operations)) {
					return execute(invoker, method,
							new CacheOperationContexts(operations, method, args, target, targetClass));
				}
			}
		}

		return invoker.invoke();
	}
```

cache处理流程代码：

```java
@Nullable
	private Object execute(final CacheOperationInvoker invoker, Method method, CacheOperationContexts contexts) {
		// Special handling of synchronized invocation
		if (contexts.isSynchronized()) {
			CacheOperationContext context = contexts.get(CacheableOperation.class).iterator().next();
			if (isConditionPassing(context, CacheOperationExpressionEvaluator.NO_RESULT)) {
				Object key = generateKey(context, CacheOperationExpressionEvaluator.NO_RESULT);
				Cache cache = context.getCaches().iterator().next();
				try {
					return wrapCacheValue(method, cache.get(key, () -> unwrapReturnValue(invokeOperation(invoker))));
				}
				catch (Cache.ValueRetrievalException ex) {
					// The invoker wraps any Throwable in a ThrowableWrapper instance so we
					// can just make sure that one bubbles up the stack.
					throw (CacheOperationInvoker.ThrowableWrapper) ex.getCause();
				}
			}
			else {
				// No caching required, only call the underlying method
				return invokeOperation(invoker);
			}
		}


		// Process any early evictions
    //在调用方法之前失效Cache，由注解中配置决定。
		processCacheEvicts(contexts.get(CacheEvictOperation.class), true,
				CacheOperationExpressionEvaluator.NO_RESULT);

		// Check if we have a cached item matching the conditions
		Cache.ValueWrapper cacheHit = findCachedItem(contexts.get(CacheableOperation.class));

		// Collect puts from any @Cacheable miss, if no cached item is found
		List<CachePutRequest> cachePutRequests = new LinkedList<>();
		if (cacheHit == null) {
			collectPutRequests(contexts.get(CacheableOperation.class),
					CacheOperationExpressionEvaluator.NO_RESULT, cachePutRequests);
		}

		Object cacheValue;
		Object returnValue;

		if (cacheHit != null && !hasCachePut(contexts)) {
			// If there are no put requests, just use the cache hit
      //cache命中使用cache中值
			cacheValue = cacheHit.get();
			returnValue = wrapCacheValue(method, cacheValue);
		}
		else {
			// Invoke the method if we don't have a cache hit
			returnValue = invokeOperation(invoker);
			cacheValue = unwrapReturnValue(returnValue);
		}

		// Collect any explicit @CachePuts
		collectPutRequests(contexts.get(CachePutOperation.class), cacheValue, cachePutRequests);

		// Process any collected put requests, either from @CachePut or a @Cacheable miss
		for (CachePutRequest cachePutRequest : cachePutRequests) {
      //放入cache。
			cachePutRequest.apply(cacheValue);
		}

		// Process any late evictions
   //在调用方法之后失效Cache
		processCacheEvicts(contexts.get(CacheEvictOperation.class), false, cacheValue);

		return returnValue;
	}
```

```java
	/*
	public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {
	*/
	public void apply(@Nullable Object result) {
			if (this.context.canPutToCache(result)) {
        //遍历cache缓存。
				for (Cache cache : this.context.getCaches()) {
					doPut(cache, this.key, result);
				}
			}
		}
```



```java
	//public abstract class AbstractCacheInvoker 
  protected void doPut(Cache cache, Object key, @Nullable Object result) {
		try {
      //cache中存放缓存对象
			cache.put(key, result);
		}
		catch (RuntimeException ex) {
			getErrorHandler().handleCachePutError(ex, cache, key, result);
		}
	}
```

### 取出cache中对象

获取cache对象的主要方法。

```java
	/*
	public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {
	*/
	@Nullable
	private Cache.ValueWrapper findCachedItem(Collection<CacheOperationContext> contexts) {
		Object result = CacheOperationExpressionEvaluator.NO_RESULT;
		for (CacheOperationContext context : contexts) {
			if (isConditionPassing(context, result)) {
        //在细节部分，会有key生成算法的部分。
				Object key = generateKey(context, result);
				Cache.ValueWrapper cached = findInCaches(context, key);
				if (cached != null) {
					return cached;
				}
				else {
					if (logger.isTraceEnabled()) {
						logger.trace("No cache entry for key '" + key + "' in cache(s) " + context.getCacheNames());
					}
				}
			}
		}
		return null;
	}
```



### 失效cache中对象

Cache失效会有两种方式：

1、对应cache的配置，一般是通过时间、队列的中元素数量来限制cache。

2、通过@CacheEvict注解来失效cache信息

通过@CacheEvict会有两个阶段失效Cache，在调用前（没有获取cache去失效cache）、在调用后（获取到返回值后，失效cache）。默认为调用前。

```java
/*
public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {	
*/
private void processCacheEvicts(
			Collection<CacheOperationContext> contexts, boolean beforeInvocation, @Nullable Object result) {

		for (CacheOperationContext context : contexts) {
			CacheEvictOperation operation = (CacheEvictOperation) context.metadata.operation;
      //针对注解中 beforeInvocation参数处理
			if (beforeInvocation == operation.isBeforeInvocation() && isConditionPassing(context, result)) {
				performCacheEvict(context, operation, result);
			}
		}
	}
```



```java
	private void performCacheEvict(
			CacheOperationContext context, CacheEvictOperation operation, @Nullable Object result) {

		Object key = null;
		for (Cache cache : context.getCaches()) {
      //如果注解的 allEntries 为true，那么会删除整个cache
			if (operation.isCacheWide()) {
				logInvalidating(context, operation, null);
				doClear(cache);
			}
			else {
				if (key == null) {
					key = generateKey(context, result);
				}
				logInvalidating(context, operation, key);
        //失效某个key的cache
				doEvict(cache, key);
			}
		}
	}
```



## 相关细节

- 1、@Cacheable对于 unless 的处理逻辑。通过spel判断是否可以放入缓存。unless是在方法调用之后，判断是否需要缓存。

```java
/*
public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {
		*/
protected boolean canPutToCache(@Nullable Object value) {
   String unless = "";
   if (this.metadata.operation instanceof CacheableOperation) {
      unless = ((CacheableOperation) this.metadata.operation).getUnless();
   }
   else if (this.metadata.operation instanceof CachePutOperation) {
      unless = ((CachePutOperation) this.metadata.operation).getUnless();
   }
   if (StringUtils.hasText(unless)) {
      EvaluationContext evaluationContext = createEvaluationContext(value);
      return !evaluator.unless(unless, this.metadata.methodKey, evaluationContext);
   }
   return true;
}
```

- 2、@Cacheable对condition的处理逻辑。condition在从缓存中获取时会生效。

```java
 /*	
	public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {
 */
	private boolean hasCachePut(CacheOperationContexts contexts) {
		// Evaluate the conditions *without* the result object because we don't have it yet...
		Collection<CacheOperationContext> cachePutContexts = contexts.get(CachePutOperation.class);
		Collection<CacheOperationContext> excluded = new ArrayList<>();
		for (CacheOperationContext context : cachePutContexts) {
			try {
				if (!context.isConditionPassing(CacheOperationExpressionEvaluator.RESULT_UNAVAILABLE)) {
					excluded.add(context);
				}
			}
			catch (VariableNotAvailableException ex) {
				// Ignoring failure due to missing result, consider the cache put has to proceed
			}
		}
		// Check if all puts have been excluded by condition
		return (cachePutContexts.size() != excluded.size());
	}
```

  ```java
	//从缓存获取信息，需要通过condition的spel。
	protected boolean isConditionPassing(@Nullable Object result) {
			if (this.conditionPassing == null) {
				if (StringUtils.hasText(this.metadata.operation.getCondition())) {
					EvaluationContext evaluationContext = createEvaluationContext(result);
					this.conditionPassing = evaluator.condition(this.metadata.operation.getCondition(),
							this.metadata.methodKey, evaluationContext);
				}
				else {
					this.conditionPassing = true;
				}
			}
			return this.conditionPassing;
		}
  ```

- 3、对于缓存key的处理

```java
	/*
	public abstract class CacheAspectSupport extends AbstractCacheInvoker
		implements BeanFactoryAware, InitializingBean, SmartInitializingSingleton {
	*/
	private void collectPutRequests(Collection<CacheOperationContext> contexts,
			@Nullable Object result, Collection<CachePutRequest> putRequests) {

		for (CacheOperationContext context : contexts) {
			if (isConditionPassing(context, result)) {
				Object key = generateKey(context, result);
				putRequests.add(new CachePutRequest(context, key));
			}
		}
	}

		@Nullable
		protected Object generateKey(@Nullable Object result) {
      //如果设计key的spel，那么通过spel执行获取到key
			if (StringUtils.hasText(this.metadata.operation.getKey())) {
				EvaluationContext evaluationContext = createEvaluationContext(result);
				return evaluator.key(this.metadata.operation.getKey(), this.metadata.methodKey, evaluationContext);
			}
      //通过key生产类产生key，如果我们不指定keyGenerator，那么使用SimpleKeyGenerator
			return this.metadata.keyGenerator.generate(this.target, this.metadata.method, this.args);
		}
```
SimpleKeyGenerator生成key的相关算法。
```java
	//public class SimpleKeyGenerator implements KeyGenerator {
	public static Object generateKey(Object... params) {
		if (params.length == 0) {
			return SimpleKey.EMPTY;
		}
		if (params.length == 1) {
			Object param = params[0];
			if (param != null && !param.getClass().isArray()) {
        //直接使用参数对象作为key
				return param;
			}
		}
    //多个参数，把参数转为对象数组，进行hash计算。使用Arrays中的deepHashCode方法
		return new SimpleKey(params);
	}

	public SimpleKey(Object... elements) {
		Assert.notNull(elements, "Elements must not be null");
		this.params = new Object[elements.length];
		System.arraycopy(elements, 0, this.params, 0, elements.length);
		this.hashCode = Arrays.deepHashCode(this.params);
	}
```

```java
//Arrays中的deepHashCode算法
public static int deepHashCode(Object a[]) {
        if (a == null)
            return 0;

        int result = 1;

        for (Object element : a) {
            int elementHash = 0;
            if (element instanceof Object[])
                elementHash = deepHashCode((Object[]) element);
            else if (element instanceof byte[])
                elementHash = hashCode((byte[]) element);
            else if (element instanceof short[])
                elementHash = hashCode((short[]) element);
            else if (element instanceof int[])
                elementHash = hashCode((int[]) element);
            else if (element instanceof long[])
                elementHash = hashCode((long[]) element);
            else if (element instanceof char[])
                elementHash = hashCode((char[]) element);
            else if (element instanceof float[])
                elementHash = hashCode((float[]) element);
            else if (element instanceof double[])
                elementHash = hashCode((double[]) element);
            else if (element instanceof boolean[])
                elementHash = hashCode((boolean[]) element);
            else if (element != null)
                elementHash = element.hashCode();

            result = 31 * result + elementHash;
        }

        return result;
```

## 总结

1、spring框架cache注解的处理是在AOP阶段，使用CacheInterceptor执行的，因此使用Cache相关注解，该类注册成spring bean。

2、cache中key是可以自定义的。

3、cache失效由阶段的，使用时注意要结合业务。





如果分析过程中存在错误点，请大家评批指点。一起学习，共同进步。
