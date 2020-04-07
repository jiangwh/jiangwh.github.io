# Spring中的异步处理

## 简单的示例

```java
@EnableAsync
@Async
```


## 异步方法的执行
```java
/*
public class AsyncExecutionInterceptor extends AsyncExecutionAspectSupport implements MethodInterceptor, Ordered {
*/
public Object invoke(final MethodInvocation invocation) throws Throwable {
		Class<?> targetClass = (invocation.getThis() != null ? AopUtils.getTargetClass(invocation.getThis()) : null);
		Method specificMethod = ClassUtils.getMostSpecificMethod(invocation.getMethod(), targetClass);
		final Method userDeclaredMethod = BridgeMethodResolver.findBridgedMethod(specificMethod);

		AsyncTaskExecutor executor = determineAsyncExecutor(userDeclaredMethod);
		if (executor == null) {
			throw new IllegalStateException(
					"No executor specified and no default executor set on AsyncExecutionInterceptor either");
		}

		Callable<Object> task = () -> {
			try {
				Object result = invocation.proceed();
				if (result instanceof Future) {
					return ((Future<?>) result).get();
				}
			}
			catch (ExecutionException ex) {
				handleError(ex.getCause(), userDeclaredMethod, invocation.getArguments());
			}
			catch (Throwable ex) {
				handleError(ex, userDeclaredMethod, invocation.getArguments());
			}
			return null;
		};

		return doSubmit(task, executor, invocation.getMethod().getReturnType());
	}

```

异步方法不处理返回。如果需要异步执行的方法存在返回，那么需要将方法的返回类型定义为 ListenableFuture 类型，或者定义为Future，通过Future get方法获取返回。
```java
/*
public abstract class AsyncExecutionAspectSupport implements BeanFactoryAware {
*/
@Nullable
	protected Object doSubmit(Callable<Object> task, AsyncTaskExecutor executor, Class<?> returnType) {
		if (CompletableFuture.class.isAssignableFrom(returnType)) {
			return CompletableFuture.supplyAsync(() -> {
				try {
					return task.call();
				}
				catch (Throwable ex) {
					throw new CompletionException(ex);
				}
			}, executor);
		}
		else if (ListenableFuture.class.isAssignableFrom(returnType)) {
			return ((AsyncListenableTaskExecutor) executor).submitListenable(task);
		}
		else if (Future.class.isAssignableFrom(returnType)) {
			return executor.submit(task);
		}
		else {
			executor.submit(task);
			return null;
		}
	}
```

## 其他细节信息

配置异步执行器以及异常处理。

```java
/*
@Configuration
public abstract class AbstractAsyncConfiguration implements ImportAware {
*/
@Autowired(required = false)
	void setConfigurers(Collection<AsyncConfigurer> configurers) {
		if (CollectionUtils.isEmpty(configurers)) {
			return;
		}
		if (configurers.size() > 1) {
			throw new IllegalStateException("Only one AsyncConfigurer may exist");
		}
		AsyncConfigurer configurer = configurers.iterator().next();
		this.executor = configurer::getAsyncExecutor;
		this.exceptionHandler = configurer::getAsyncUncaughtExceptionHandler;
	}
```

配置默认的异步执行器以及异常处理方式。

```java

	/**
	 * Configure this aspect with the given executor and exception handler suppliers,
	 * applying the corresponding default if a supplier is not resolvable.
	 * @since 5.1
	 */
	public void configure(@Nullable Supplier<Executor> defaultExecutor,
			@Nullable Supplier<AsyncUncaughtExceptionHandler> exceptionHandler) {

		this.defaultExecutor = new SingletonSupplier<>(defaultExecutor, () -> getDefaultExecutor(this.beanFactory));
		this.exceptionHandler = new SingletonSupplier<>(exceptionHandler, SimpleAsyncUncaughtExceptionHandler::new);
	}
```

## 总结

1、spring异步执行方式是通过代理执行的。

2、任务可以存在返回值或者没有返回值。

3、异常以及部分执行器都是可以设定的。





如果分析过程中存在错误点，请大家评批指点。一起学习，共同进步。

```
作者：仁蕴。
邮箱：jiang_wh@126.com 
github：https://github.com/jiangwh/blog
```

