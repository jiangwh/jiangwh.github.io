# Spring的事件处理分析

每个事件都是有过程的，一般会经过发布、处理、消费三个环境。带这个思路来看看spring事件的处理。

##事件发布
先上一段代码，正常情况下，在spring中可以发布事件的写法。
```java
//业务逻辑代码
@Component
public class ApplicationEventPublish {

  //ApplicationContext 同样也可以发布事件
	@Autowired
	ApplicationEventPublisher publisher;

	public void publish(EventObject event) {
    //发布事件
		publisher.publishEvent(event);
	}
}
```
## 事件处理
spring中获取到事件处理对象

```java
//public class ApplicationListenerMethodAdapter implements GenericApplicationListener 
public void processEvent(ApplicationEvent event) {
		Object[] args = resolveArguments(event);//解析获取事件对象
		if (shouldHandle(event, args)) {
			Object result = doInvoke(args); //调用事件监听的类的对应方法
			if (result != null) {
				handleResult(result); //如果事件有返回对象，会继续发布。
			}
			else {
				logger.trace("No result object given - no result to handle");
			}
		}
	}
```
## 事件消费
```java
//业务逻辑代码
@EventListener
	public void eventConsumer(EventObject event) {
		//事件处理逻辑
	}
```

## 进入细节

上面是spring中事件处理的大概流程，我们可以深挖一些细节：

- 1、如果没有设定taskExcutor，那么 spring事件中发布与订阅是在同一个线程中执行。

- 2、spring中一个事件是可以被多处消费的。

  这两个点的逻辑在一个方法中，具体如下：

```java
//public class SimpleApplicationEventMulticaster extends AbstractApplicationEventMulticaster

@Override
	public void multicastEvent(final ApplicationEvent event, @Nullable ResolvableType eventType) {
		ResolvableType type = (eventType != null ? eventType : resolveDefaultEventType(event));
    //根据类型获取事件的consumer，可能多个。
		for (final ApplicationListener<?> listener : getApplicationListeners(event, type)) {
      //getApplicationListeners(event, type) 获取事件处理类。
			Executor executor = getTaskExecutor();
			if (executor != null) {
				executor.execute(() -> invokeListener(listener, event)); //存在taskExcutor，异步执行
			}
			else {
				invokeListener(listener, event);
			}
		}
	}
```

- 3、如果不设定errorHandle，那么会直接抛出异常。

spring中对接线程执行、错误处理的源码如下：

如果存在异常处理的handler，那么就利用try catch语句包裹。

```java
//public class SimpleApplicationEventMulticaster extends AbstractApplicationEventMulticaster
protected void invokeListener(ApplicationListener<?> listener, ApplicationEvent event) {
		ErrorHandler errorHandler = getErrorHandler();
		if (errorHandler != null) {
			try {
				doInvokeListener(listener, event);
			}
			catch (Throwable err) {
				errorHandler.handleError(err); //存在错误处理的handler，会catch异常。
			}
		}
		else {
			doInvokeListener(listener, event);
		}
	}
```

为了让当前线程不中断，那么需要设定Executor或者ErrorHandler其中之一即可。

具体做法如下：

```java
@Component("applicationEventMulticaster")
@Slf4j
public class ApplicationEventMulticaster extends SimpleApplicationEventMulticaster {

  /*Executor 不能直接直接返回Executor，需要把exceutor注入到对应单例的bean中*/
	@Override
	protected Executor getTaskExecutor() {
		Executor executor = super.getTaskExecutor();
		if (null == executor) {
			ThreadFactory threadFactory = new DefaultThreadFactory("event-factory");
			super.setTaskExecutor(Executors.newFixedThreadPool(5, threadFactory));
		}
		return super.getTaskExecutor();
	}
	
	@Override
	protected ErrorHandler getErrorHandler() {
		ErrorHandler handler = super.getErrorHandler();
		if (null == handler) {
			handler = new ErrorHandler() {
				@Override
				public void handleError(Throwable t) {
					log.error("error in event process", t);
				}
			};
			super.setErrorHandler(handler);
		}
		return super.getErrorHandler();
	}
}
```

- 4、事件执行的条件condition。

在@EventListener 可以增加执行的condition条件，该条件为spel表达式。

```java
public @interface EventListener {
	//忽略其他代码
	String condition() default "";
}
```
源码是这么处理这个condtion的
```java
//public class ApplicationListenerMethodAdapter implements GenericApplicationListener
private boolean shouldHandle(ApplicationEvent event, @Nullable Object[] args) {
		if (args == null) {
			return false;
		}
		String condition = getCondition();
		if (StringUtils.hasText(condition)) {
			Assert.notNull(this.evaluator, "EventExpressionEvaluator must not be null");
			return this.evaluator.condition(
					condition, event, this.targetMethod, this.methodKey, args, this.applicationContext);
		}
		return true;
	}
```

- 5、对应事件consumer的细节。
```java
//public class ApplicationListenerMethodAdapter implements GenericApplicationListener
private List<ResolvableType> resolveDeclaredEventTypes(Method method, @Nullable EventListener ann) {
		int count = method.getParameterCount();
		if (count > 1) {
			throw new IllegalStateException(
					"Maximum one parameter is allowed for event listener method: " + method);
		}

		if (ann != null) {
			Class<?>[] classes = ann.classes(); //获取@EventListener 注解中标识的类信息。
			if (classes.length > 0) {
				List<ResolvableType> types = new ArrayList<>(classes.length);
				for (Class<?> eventType : classes) {
					types.add(ResolvableType.forClass(eventType));
				}
				return types;
			}
		}

		if (count == 0) { //如果参数为0且没有标识处理事件的类，那么抛出异常。
			throw new IllegalStateException(
					"Event parameter is mandatory for event listener method: " + method);
		}
		return Collections.singletonList(ResolvableType.forMethodParameter(method, 0));
	}
```

从源码中可以看到，处理事件的方法拥有的参数必须小于等于1个。如果参数为0个的方法，必须在@EventListener中增加class信息。

如：
```java
@EventListener(Object.class)
public void eventConsumer() {} //这种写法，会处理所有事件
```

- 6、事件的consumer的加载细节。

```java
/*public class EventListenerMethodProcessor
		implements SmartInitializingSingleton, ApplicationContextAware, BeanFactoryPostProcessor */
private void processBean(final String beanName, final Class<?> targetType) {
		if (!this.nonAnnotatedClasses.contains(targetType) && !isSpringContainerClass(targetType)) {
			Map<Method, EventListener> annotatedMethods = null;
			try {
				annotatedMethods = MethodIntrospector.selectMethods(targetType,
						(MethodIntrospector.MetadataLookup<EventListener>) method ->
								AnnotatedElementUtils.findMergedAnnotation(method, EventListener.class));
			}
			catch (Throwable ex) {
				// An unresolvable type in a method signature, probably from a lazy bean - let's ignore it.
				if (logger.isDebugEnabled()) {
					logger.debug("Could not resolve methods for bean with name '" + beanName + "'", ex);
				}
			}
			if (CollectionUtils.isEmpty(annotatedMethods)) {
				this.nonAnnotatedClasses.add(targetType);
				if (logger.isTraceEnabled()) {
					logger.trace("No @EventListener annotations found on bean class: " + targetType.getName());
				}
			}
			else {
				// Non-empty set of methods
				ConfigurableApplicationContext context = this.applicationContext;
				Assert.state(context != null, "No ApplicationContext set");
				List<EventListenerFactory> factories = this.eventListenerFactories;
				Assert.state(factories != null, "EventListenerFactory List not initialized");
				for (Method method : annotatedMethods.keySet()) {
					for (EventListenerFactory factory : factories) {
            /*
            一般情况会有两类：
            1、org.springframework.transaction.event.TransactionalEventListenerFactory
            2、org.springframework.context.event.DefaultEventListenerFactory
            	//普通事件涉及的第二类factory
            */
						if (factory.supportsMethod(method)) { 
              /*找到处理事件的方法*/
							Method methodToUse = AopUtils.selectInvocableMethod(method, context.getType(beanName));
              /*创建监听*/
							ApplicationListener<?> applicationListener =
									factory.createApplicationListener(beanName, targetType, methodToUse);
							if (applicationListener instanceof ApplicationListenerMethodAdapter) {
								((ApplicationListenerMethodAdapter) applicationListener).init(context, this.evaluator);
							}
              /*增加到事件处理中*/
							context.addApplicationListener(applicationListener);
							break;
						}
					}
				}
				if (logger.isDebugEnabled()) {
					logger.debug(annotatedMethods.size() + " @EventListener methods processed on bean '" +
							beanName + "': " + annotatedMethods);
				}
			}
		}
	}
```

事件增加到上下文。

```java
/*public abstract class AbstractApplicationContext extends DefaultResourceLoader
		implements ConfigurableApplicationContext {*/	
public void addApplicationListener(ApplicationListener<?> listener) {
		Assert.notNull(listener, "ApplicationListener must not be null");
		if (this.applicationEventMulticaster != null) {
			this.applicationEventMulticaster.addApplicationListener(listener);
		}
		this.applicationListeners.add(listener);
	}
```

我们回头看下获取监听方法的处理的步骤：

```java
/*public abstract class AbstractApplicationEventMulticaster
		implements ApplicationEventMulticaster, BeanClassLoaderAware, BeanFactoryAware 
*/	
private Collection<ApplicationListener<?>> retrieveApplicationListeners(
			ResolvableType eventType, @Nullable Class<?> sourceType, @Nullable ListenerRetriever retriever) {

		List<ApplicationListener<?>> allListeners = new ArrayList<>();
		Set<ApplicationListener<?>> listeners;
		Set<String> listenerBeans;
		synchronized (this.retrievalMutex) {
      //从applicationListeners中获取事件，以及对应bean
			listeners = new LinkedHashSet<>(this.defaultRetriever.applicationListeners);
      //
			listenerBeans = new LinkedHashSet<>(this.defaultRetriever.applicationListenerBeans);
		}
		for (ApplicationListener<?> listener : listeners) {
  		//根据事件源、事件目标获取事件处理方法
			if (supportsEvent(listener, eventType, sourceType)) {
				if (retriever != null) {
					retriever.applicationListeners.add(listener);
				}
				allListeners.add(listener);
			}
		}
		if (!listenerBeans.isEmpty()) {
			BeanFactory beanFactory = getBeanFactory();
			for (String listenerBeanName : listenerBeans) {
				try {
					Class<?> listenerType = beanFactory.getType(listenerBeanName);
					if (listenerType == null || supportsEvent(listenerType, eventType)) {
						ApplicationListener<?> listener =
								beanFactory.getBean(listenerBeanName, ApplicationListener.class);
						if (!allListeners.contains(listener) && supportsEvent(listener, eventType, sourceType)) {
							if (retriever != null) {
								if (beanFactory.isSingleton(listenerBeanName)) {
									retriever.applicationListeners.add(listener);
								}
								else {
									retriever.applicationListenerBeans.add(listenerBeanName);
								}
							}
							allListeners.add(listener);
						}
					}
				}
				catch (NoSuchBeanDefinitionException ex) {
					// Singleton listener instance (without backing bean definition) disappeared -
					// probably in the middle of the destruction phase
				}
			}
		}
		AnnotationAwareOrderComparator.sort(allListeners);
		if (retriever != null && retriever.applicationListenerBeans.isEmpty()) {
			retriever.applicationListeners.clear();
			retriever.applicationListeners.addAll(allListeners);
		}
		return allListeners;
	}
```

7、事件消费者返回对象，依赖作为事件对象发布

```java
//public class ApplicationListenerMethodAdapter implements GenericApplicationListener 
protected void handleResult(Object result) {
		if (result.getClass().isArray()) {
			Object[] events = ObjectUtils.toObjectArray(result);
			for (Object event : events) {
				publishEvent(event);
			}
		}
		else if (result instanceof Collection<?>) {
			Collection<?> events = (Collection<?>) result;
			for (Object event : events) {
				publishEvent(event);
			}
		}
		else {
			publishEvent(result);
		}
	}
```

这个点很重要，不能返回对象与接受事件对象一致，否则很有可能会出现`java.lang.StackOverflowError`

## 总结

spring事件使用非常方便，只要通过简单的注解，就可以使用。这功能也具备一些特性：

1、spring的事件是依赖事件对象来区分事件消费者。

2、spring的事件默认是同步的。

3、spring的事件是广播方式传递的。

4、消费事件的方法如果有返回值，那么这个返回对象会作为事件发布。

5、可以通过spel语句有条件消费事件。



** 如果分析过程中存在错误点，请大家评批指点。共同进步～ **

```
作者：仁蕴。
邮箱：jiang_wh@126.com 
github：https://github.com/jiangwh/blog
```