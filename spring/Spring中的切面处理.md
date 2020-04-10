# Spring中的AOP处理

Spring中切面两种代理方式：

1、JdkDynamicAopProxy

2、CglibAopProxy

Spring 采用动态代理的方式来实现面向切面的编程。

## 相关基础信息

### 动态代理：

##### JDK动态代理

```java
		//这就是最基本的JDK动态代理实现。
		InvocationHandler invokeHandler = new InvocationHandler() {
			@Override
			public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
				return method.invoke(proxy,args);
			}
		};
		//Service类必须是一个接口。
		Service service = (Service) Proxy
				.newProxyInstance(Thread.currentThread().getContextClassLoader(),
						new Class[] { Service.class },
						(InvocationHandler) invokeHandler);
		service.method();
```
##### CGlib动态代理
```java
		//CGlib方式代理
		Enhancer enhancer = new Enhancer();
		enhancer.setClassLoader(Thread.currentThread().getContextClassLoader());
		enhancer.setUseCache(false);
		enhancer.setSuperclass(LoggerService.class);
		enhancer.setNamingPolicy(SpringNamingPolicy.INSTANCE);
		enhancer.setCallback(new MethodInterceptor() {
			@Override
			public Object intercept(Object o, Method method, Object[] objects, MethodProxy methodProxy)
					throws Throwable {
				System.out.println("==================");
				return methodProxy.invokeSuper(o, objects);
			}
		});
		LoggerService o = (LoggerService) enhancer.create();
		o.logBefore();
```

### 反射：

```java
	//获取某个方法
	Method method =  Service.class.getMethod("name",new Class[]{String.class});
	//反射调用
	method.invoke(instance,params)
```



## Spring AOP示例

Spring可以采用注解的方式来实现切面编程

```java
@Aspect
@Slf4j
@Component //必须要组册成bean，否则不会触发处理
public class LoggerService {
  //around 拦截处理
	@Around(value = "execution(* com.contorllers.*.*(..))")
	public Object logAop(ProceedingJoinPoint joinPoint) throws Throwable {
		log.info("#### call {}", joinPoint.getTarget().toString());
		return joinPoint.proceed();
	}

  //前置拦截
	@Before("execution(* com.contorllers.*.*(..))")
	public void logBefore(){
		log.info("work ########## before");
	}
}
```

## AOP处理过程

### 初始化过程创建动态代理类

```java
	/*public abstract class AbstractAdvisingBeanPostProcessor extends ProxyProcessorSupport implements BeanPostProcessor {
*/
	@Override
	public Object postProcessAfterInitialization(Object bean, String beanName) {
		if (this.advisor == null || bean instanceof AopInfrastructureBean) {
			// Ignore AOP infrastructure such as scoped proxies.
			return bean;
		}

		if (bean instanceof Advised) {
			Advised advised = (Advised) bean;
			if (!advised.isFrozen() && isEligible(AopUtils.getTargetClass(bean))) {
				// Add our local Advisor to the existing proxy's Advisor chain...
				if (this.beforeExistingAdvisors) {
					advised.addAdvisor(0, this.advisor);
				}
				else {
					advised.addAdvisor(this.advisor);
				}
				return bean;
			}
		}
		//存在切面方法的bean,需要动态创建代理。导致切面的原因：业务上面的AOP编程、cache、异步、事务等。
		if (isEligible(bean, beanName)) {
			ProxyFactory proxyFactory = prepareProxyFactory(bean, beanName);
			if (!proxyFactory.isProxyTargetClass()) {
				evaluateProxyInterfaces(bean.getClass(), proxyFactory);
			}
			proxyFactory.addAdvisor(this.advisor);
			customizeProxyFactory(proxyFactory);
			return proxyFactory.getProxy(getProxyClassLoader());
		}

		// No proxy needed.
		return bean;
	}
```

ProxyFactory创建具体的代理。

```java
	/*public class ProxyFactory extends ProxyCreatorSupport {*/
	public Object getProxy(@Nullable ClassLoader classLoader) {
    //获取代理类
		return createAopProxy().getProxy(classLoader);
	}
```

### 初始化拦截方法配置

//TODO

### 拦截处理

获取获取拦截的方法

```java
/*
public class DefaultAdvisorChainFactory implements AdvisorChainFactory, Serializable {
*/
public List<Object> getInterceptorsAndDynamicInterceptionAdvice(
			Advised config, Method method, @Nullable Class<?> targetClass) {

		// This is somewhat tricky... We have to process introductions first,
		// but we need to preserve order in the ultimate list.
		AdvisorAdapterRegistry registry = GlobalAdvisorAdapterRegistry.getInstance();
		Advisor[] advisors = config.getAdvisors();
		List<Object> interceptorList = new ArrayList<>(advisors.length);
		Class<?> actualClass = (targetClass != null ? targetClass : method.getDeclaringClass());
		Boolean hasIntroductions = null;

		for (Advisor advisor : advisors) {
			if (advisor instanceof PointcutAdvisor) {
				// Add it conditionally.
				PointcutAdvisor pointcutAdvisor = (PointcutAdvisor) advisor;
				if (config.isPreFiltered() || pointcutAdvisor.getPointcut().getClassFilter().matches(actualClass)) {
					MethodMatcher mm = pointcutAdvisor.getPointcut().getMethodMatcher();
					boolean match;
					if (mm instanceof IntroductionAwareMethodMatcher) {
						if (hasIntroductions == null) {
							hasIntroductions = hasMatchingIntroductions(advisors, actualClass);
						}
						match = ((IntroductionAwareMethodMatcher) mm).matches(method, actualClass, hasIntroductions);
					}
					else {
						match = mm.matches(method, actualClass);
					}
					if (match) {
						MethodInterceptor[] interceptors = registry.getInterceptors(advisor);
						if (mm.isRuntime()) {
							// Creating a new object instance in the getInterceptors() method
							// isn't a problem as we normally cache created chains.
							for (MethodInterceptor interceptor : interceptors) {
								interceptorList.add(new InterceptorAndDynamicMethodMatcher(interceptor, mm));
							}
						}
						else {
							interceptorList.addAll(Arrays.asList(interceptors));
						}
					}
				}
			}
			else if (advisor instanceof IntroductionAdvisor) {
				IntroductionAdvisor ia = (IntroductionAdvisor) advisor;
				if (config.isPreFiltered() || ia.getClassFilter().matches(actualClass)) {
					Interceptor[] interceptors = registry.getInterceptors(advisor);
					interceptorList.addAll(Arrays.asList(interceptors));
				}
			}
			else {
				Interceptor[] interceptors = registry.getInterceptors(advisor);
				interceptorList.addAll(Arrays.asList(interceptors));
			}
		}

		return interceptorList;
	}

```

拦截方法处理

```java
/*
public class ReflectiveMethodInvocation implements ProxyMethodInvocation, Cloneable {
*/
//处理AOP的方法
public Object proceed() throws Throwable {
		//	We start with an index of -1 and increment early.
 		// interceptorsAndDynamicMethodMatchers中存储代理前后需要执行的方法。
		if (this.currentInterceptorIndex == this.interceptorsAndDynamicMethodMatchers.size() - 1) {
			return invokeJoinpoint();
		}
  	//按序获取拦截方法
		Object interceptorOrInterceptionAdvice =
				this.interceptorsAndDynamicMethodMatchers.get(++this.currentInterceptorIndex);
		if (interceptorOrInterceptionAdvice instanceof InterceptorAndDynamicMethodMatcher) {
			// Evaluate dynamic method matcher here: static part will already have
			// been evaluated and found to match.
			InterceptorAndDynamicMethodMatcher dm =
					(InterceptorAndDynamicMethodMatcher) interceptorOrInterceptionAdvice;
			Class<?> targetClass = (this.targetClass != null ? this.targetClass : this.method.getDeclaringClass());
			if (dm.methodMatcher.matches(this.method, targetClass, this.arguments)) {
				return dm.interceptor.invoke(this);
			}
			else {
				// Dynamic matching failed.
				// Skip this interceptor and invoke the next in the chain.
				return proceed();
			}
		}
		else {
			// It's an interceptor, so we just invoke it: The pointcut will have
			// been evaluated statically before this object was constructed.
      // 调用拦截器方法
			return ((MethodInterceptor) interceptorOrInterceptionAdvice).invoke(this);
		}
	}
```

### 反射调用拦截方法

```java
/*
public abstract class AbstractAspectJAdvice implements Advice, AspectJPrecedenceInformation, Serializable {
*/
protected Object invokeAdviceMethodWithGivenArgs(Object[] args) throws Throwable {
		Object[] actualArgs = args;
		if (this.aspectJAdviceMethod.getParameterCount() == 0) {
			actualArgs = null;
		}
		try {
			ReflectionUtils.makeAccessible(this.aspectJAdviceMethod);
			// TODO AopUtils.invokeJoinpointUsingReflection
      //调用切面方法,通过反射完成。
			return this.aspectJAdviceMethod.invoke(this.aspectInstanceFactory.getAspectInstance(), actualArgs);
		}
		catch (IllegalArgumentException ex) {
			throw new AopInvocationException("Mismatch on arguments to advice method [" +
					this.aspectJAdviceMethod + "]; pointcut expression [" +
					this.pointcut.getPointcutExpression() + "]", ex);
		}
		catch (InvocationTargetException ex) {
			throw ex.getTargetException();
		}
	}
```



```java
	/*
	public class ReflectiveAspectJAdvisorFactory extends AbstractAspectJAdvisorFactory implements Serializable {
	*/
	private List<Method> getAdvisorMethods(Class<?> aspectClass) {
		final List<Method> methods = new ArrayList<>();
		ReflectionUtils.doWithMethods(aspectClass, method -> {
			// Exclude pointcuts
			if (AnnotationUtils.getAnnotation(method, Pointcut.class) == null) {
				methods.add(method);
			}
		});
		methods.sort(METHOD_COMPARATOR);
		return methods;
	}
```
