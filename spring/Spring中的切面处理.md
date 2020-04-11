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
				return methodProxy.invokeSuper(o, objects);
			}
		});
		//创建的增量类为LoggerService的子类
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



### 附：CGLIB增强类

CGLIB 增量主要存在以下几个阶段：

1、使用asm的ClassVisitor生产类字节码。

2、使用当前的classload，defineClass(或者类加载)。

3、使用增量类代理对应方法。


#### 增强类示例：

```java
import java.lang.reflect.Method;
import org.aspectj.lang.ProceedingJoinPoint;
import org.springframework.cglib.core.ReflectUtils;
import org.springframework.cglib.core.Signature;
import org.springframework.cglib.proxy.Callback;
import org.springframework.cglib.proxy.Factory;
import org.springframework.cglib.proxy.MethodInterceptor;
import org.springframework.cglib.proxy.MethodProxy;

//该类为cglib代理生成类，LoggerService为被代理类。
public class LoggerService$$EnhancerBySpringCGLIB$$e2f799bc extends LoggerService implements Factory {
    private boolean CGLIB$BOUND;
    public static Object CGLIB$FACTORY_DATA;
    private static final ThreadLocal CGLIB$THREAD_CALLBACKS;
    private static final Callback[] CGLIB$STATIC_CALLBACKS;
    private MethodInterceptor CGLIB$CALLBACK_0;
    private static Object CGLIB$CALLBACK_FILTER;
    private static final Method CGLIB$logAop$0$Method;
    private static final MethodProxy CGLIB$logAop$0$Proxy;
    private static final Object[] CGLIB$emptyArgs;
    private static final Method CGLIB$logBefore$1$Method;
    private static final MethodProxy CGLIB$logBefore$1$Proxy;
    private static final Method CGLIB$equals$2$Method;
    private static final MethodProxy CGLIB$equals$2$Proxy;
    private static final Method CGLIB$toString$3$Method;
    private static final MethodProxy CGLIB$toString$3$Proxy;
    private static final Method CGLIB$hashCode$4$Method;
    private static final MethodProxy CGLIB$hashCode$4$Proxy;
    private static final Method CGLIB$clone$5$Method;
    private static final MethodProxy CGLIB$clone$5$Proxy;

    public LoggerService$$EnhancerBySpringCGLIB$$e2f799bc() {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc loggerService$$EnhancerBySpringCGLIB$$e2f799bc = this;
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(loggerService$$EnhancerBySpringCGLIB$$e2f799bc);
    }

    static {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$STATICHOOK1();
    }

    public final boolean equals(Object object) {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            Object object2 = methodInterceptor.intercept(this, CGLIB$equals$2$Method, new Object[]{object}, CGLIB$equals$2$Proxy);
            return object2 == null ? false : (Boolean)object2;
        }
        return super.equals(object);
    }

    public final String toString() {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            return (String)methodInterceptor.intercept(this, CGLIB$toString$3$Method, CGLIB$emptyArgs, CGLIB$toString$3$Proxy);
        }
        return super.toString();
    }

    public final int hashCode() {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            Object object = methodInterceptor.intercept(this, CGLIB$hashCode$4$Method, CGLIB$emptyArgs, CGLIB$hashCode$4$Proxy);
            return object == null ? 0 : ((Number)object).intValue();
        }
        return super.hashCode();
    }

    protected final Object clone() throws CloneNotSupportedException {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            return methodInterceptor.intercept(this, CGLIB$clone$5$Method, CGLIB$emptyArgs, CGLIB$clone$5$Proxy);
        }
        return super.clone();
    }

    public Object newInstance(Callback[] arrcallback) {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(arrcallback);
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(null);
        return new LoggerService$$EnhancerBySpringCGLIB$$e2f799bc();
    }

    /*
     * Unable to fully structure code
     * Enabled aggressive block sorting
     * Lifted jumps to return sites
     */
    public Object newInstance(Class[] var1_1, Object[] var2_2, Callback[] var3_3) {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(var3_3);
        v0 = var1_1;
        switch (var1_1.length) {
            case 0: {
                ** break;
            }
        }
        throw new IllegalArgumentException("Constructor not found");
lbl7:
        // 1 sources

        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(null);
        return new LoggerService$$EnhancerBySpringCGLIB$$e2f799bc();
    }

    public Object newInstance(Callback callback) {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(new Callback[]{callback});
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$SET_THREAD_CALLBACKS(null);
        return new LoggerService$$EnhancerBySpringCGLIB$$e2f799bc();
    }

    public void setCallbacks(Callback[] arrcallback) {
        Callback[] arrcallback2 = arrcallback;
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc loggerService$$EnhancerBySpringCGLIB$$e2f799bc = this;
        this.CGLIB$CALLBACK_0 = (MethodInterceptor)arrcallback[0];
    }

    public static void CGLIB$SET_STATIC_CALLBACKS(Callback[] arrcallback) {
        CGLIB$STATIC_CALLBACKS = arrcallback;
    }

    public static void CGLIB$SET_THREAD_CALLBACKS(Callback[] arrcallback) {
        CGLIB$THREAD_CALLBACKS.set(arrcallback);
    }

    public Callback getCallback(int n) {
        MethodInterceptor methodInterceptor;
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
        switch (n) {
            case 0: {
                methodInterceptor = this.CGLIB$CALLBACK_0;
                break;
            }
            default: {
                methodInterceptor = null;
            }
        }
        return methodInterceptor;
    }

    public Callback[] getCallbacks() {
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
        LoggerService$$EnhancerBySpringCGLIB$$e2f799bc loggerService$$EnhancerBySpringCGLIB$$e2f799bc = this;
        return new Callback[]{this.CGLIB$CALLBACK_0};
    }

    public static MethodProxy CGLIB$findMethodProxy(Signature signature) {
        String string = ((Object)signature).toString();
        switch (string.hashCode()) {
            case -1237516411: {
                if (!string.equals("logAop(Lorg/aspectj/lang/ProceedingJoinPoint;)Ljava/lang/Object;")) break;
                return CGLIB$logAop$0$Proxy;
            }
            case -508378822: {
                if (!string.equals("clone()Ljava/lang/Object;")) break;
                return CGLIB$clone$5$Proxy;
            }
            case 616407218: {
                if (!string.equals("logBefore()V")) break;
                return CGLIB$logBefore$1$Proxy;
            }
            case 1826985398: {
                if (!string.equals("equals(Ljava/lang/Object;)Z")) break;
                return CGLIB$equals$2$Proxy;
            }
            case 1913648695: {
                if (!string.equals("toString()Ljava/lang/String;")) break;
                return CGLIB$toString$3$Proxy;
            }
            case 1984935277: {
                if (!string.equals("hashCode()I")) break;
                return CGLIB$hashCode$4$Proxy;
            }
        }
        return null;
    }

    public final Object logAop(ProceedingJoinPoint proceedingJoinPoint) throws Throwable {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            return methodInterceptor.intercept(this, CGLIB$logAop$0$Method, new Object[]{proceedingJoinPoint}, CGLIB$logAop$0$Proxy);
        }
        return super.logAop(proceedingJoinPoint);
    }

    public final void logBefore() {
        MethodInterceptor methodInterceptor = this.CGLIB$CALLBACK_0;
        if (methodInterceptor == null) {
            LoggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BIND_CALLBACKS(this);
            methodInterceptor = this.CGLIB$CALLBACK_0;
        }
        if (methodInterceptor != null) {
            Object object = methodInterceptor.intercept(this, CGLIB$logBefore$1$Method, CGLIB$emptyArgs, CGLIB$logBefore$1$Proxy);
            return;
        }
        super.logBefore();
    }

    public void setCallback(int n, Callback callback) {
        switch (n) {
            case 0: {
                this.CGLIB$CALLBACK_0 = (MethodInterceptor)callback;
                break;
            }
        }
    }

    static void CGLIB$STATICHOOK1() {
        CGLIB$THREAD_CALLBACKS = new ThreadLocal();
        CGLIB$emptyArgs = new Object[0];
        Class<?> class_ = Class.forName("LoggerService$$EnhancerBySpringCGLIB$$e2f799bc");
        Class<?> class_2 = Class.forName("java.lang.Object");
        Method[] arrmethod = ReflectUtils.findMethods(new String[]{"equals", "(Ljava/lang/Object;)Z", "toString", "()Ljava/lang/String;", "hashCode", "()I", "clone", "()Ljava/lang/Object;"}, class_2.getDeclaredMethods());
        CGLIB$equals$2$Method = arrmethod[0];
        CGLIB$equals$2$Proxy = MethodProxy.create(class_2, class_, "(Ljava/lang/Object;)Z", "equals", "CGLIB$equals$2");
        CGLIB$toString$3$Method = arrmethod[1];
        CGLIB$toString$3$Proxy = MethodProxy.create(class_2, class_, "()Ljava/lang/String;", "toString", "CGLIB$toString$3");
        CGLIB$hashCode$4$Method = arrmethod[2];
        CGLIB$hashCode$4$Proxy = MethodProxy.create(class_2, class_, "()I", "hashCode", "CGLIB$hashCode$4");
        CGLIB$clone$5$Method = arrmethod[3];
        CGLIB$clone$5$Proxy = MethodProxy.create(class_2, class_, "()Ljava/lang/Object;", "clone", "CGLIB$clone$5");
        class_2 = Class.forName("LoggerService");
        Method[] arrmethod2 = ReflectUtils.findMethods(new String[]{"logAop", "(Lorg/aspectj/lang/ProceedingJoinPoint;)Ljava/lang/Object;", "logBefore", "()V"}, class_2.getDeclaredMethods());
        CGLIB$logAop$0$Method = arrmethod2[0];
        CGLIB$logAop$0$Proxy = MethodProxy.create(class_2, class_, "(Lorg/aspectj/lang/ProceedingJoinPoint;)Ljava/lang/Object;", "logAop", "CGLIB$logAop$0");
        CGLIB$logBefore$1$Method = arrmethod2[1];
        CGLIB$logBefore$1$Proxy = MethodProxy.create(class_2, class_, "()V", "logBefore", "CGLIB$logBefore$1");
    }

    final Object CGLIB$logAop$0(ProceedingJoinPoint proceedingJoinPoint) throws Throwable {
        return super.logAop(proceedingJoinPoint);
    }

    private static final void CGLIB$BIND_CALLBACKS(Object object) {
        block2: {
            Object object2;
            block3: {
                LoggerService$$EnhancerBySpringCGLIB$$e2f799bc loggerService$$EnhancerBySpringCGLIB$$e2f799bc = (LoggerService$$EnhancerBySpringCGLIB$$e2f799bc)object;
                if (loggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BOUND) break block2;
                loggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$BOUND = true;
                object2 = CGLIB$THREAD_CALLBACKS.get();
                if (object2 != null) break block3;
                object2 = CGLIB$STATIC_CALLBACKS;
                if (CGLIB$STATIC_CALLBACKS == null) break block2;
            }
            loggerService$$EnhancerBySpringCGLIB$$e2f799bc.CGLIB$CALLBACK_0 = (MethodInterceptor)((Callback[])object2)[0];
        }
    }

    final void CGLIB$logBefore$1() {
        super.logBefore();
    }

    final boolean CGLIB$equals$2(Object object) {
        return super.equals(object);
    }

    final String CGLIB$toString$3() {
        return super.toString();
    }

    final int CGLIB$hashCode$4() {
        return super.hashCode();
    }

    final Object CGLIB$clone$5() throws CloneNotSupportedException {
        return super.clone();
    }
}
```

