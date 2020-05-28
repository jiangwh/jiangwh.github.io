# Trace命令

## 简单示例

```bash
trace {namespace.class} method
```

trace命令可以追踪某个类/多个类的方法执行调用链（同一个thread中），以及执行时间。

## 相关源码

```java
 protected void enhance(CommandProcess process) {
   			Session session = process.session();
   			//这边锁的实现使用了CAS乐观锁方式。
        if (!session.tryLock()) {
            process.write("someone else is enhancing classes, pls. wait.\n");
            process.end();
            return;
        }
        int lock = session.getLock();
        try {
            Instrumentation inst = session.getInstrumentation();
          	//trace命令存在对应监听器
          	//trace监听器主要的目标：1、记录方法执行调用链路。2、记录方法执行时间。
          	//使用threadlocal记录对象，以树形结构记录。
            AdviceListener listener = getAdviceListener(process);
            if (listener == null) {
                warn(process, "advice listener is null");
                return;
            }
            boolean skipJDKTrace = false;
            if(listener instanceof AbstractTraceAdviceListener) {
                skipJDKTrace = ((AbstractTraceAdviceListener) listener).getCommand().isSkipJDKTrace();
            }
						//arthas精华部分，就是增加字节码。
            EnhancerAffect effect = Enhancer.enhance(inst, listener, listener instanceof InvokeTraceable,
                    skipJDKTrace, getClassNameMatcher(), getMethodNameMatcher());

            if (effect.cCnt() == 0 || effect.mCnt() == 0) {
                // no class effected
                // might be method code too large
                process.write("Matched class count: " + effect.cCnt() + ", method count: " + effect.mCnt() + "\n");
                process.write("No class or method is affected, try:\n"
                              + "1. sm CLASS_NAME METHOD_NAME to make sure the method you are tracing actually exists (it might be in your parent class).\n"
                              + "2. reset CLASS_NAME and try again, your method body might be too large.\n"
                              + "3. check arthas log: " + LogUtil.loggingFile() + "\n"
                              + "4. visit https://github.com/alibaba/arthas/issues/47 for more details.\n");
                process.end();
                return;
            }

            // 这里做个补偿,如果在enhance期间,unLock被调用了,则补偿性放弃
            if (session.getLock() == lock) {
                // 注册通知监听器
                process.register(lock, listener, effect.getTransformer());
                if (process.isForeground()) {
                    process.echoTips(Constants.Q_OR_CTRL_C_ABORT_MSG + "\n");
                }
            }

            process.write(effect + "\n");
        } catch (UnmodifiableClassException e) {
            logger.error("error happens when enhancing class", e);
        } finally {
            if (session.getLock() == lock) {
                // enhance结束后解锁
                process.session().unLock();
            }
        }
    }
```

### 乐观锁

```
使用AtomicInteger来实现锁。
-1表示该锁的状态为 未锁定状态。
```
对于trylock需要说明下
```java
 @Override
    public boolean tryLock() {
    		//此处使用lockSequence自增的方式，有效防止ABA问题的发生。
        return lock.compareAndSet(LOCK_TX_EMPTY, lockSequence.getAndIncrement());
    }
```

### 编织字节码

此处按照3.1.0tag代码逻辑说明。个人感觉这也是arthas中比较难以阅读的代码。

```java
private void spy(final ClassLoader targetClassLoader) throws Exception {
        if (targetClassLoader == null) {
            // 增强JDK自带的类,targetClassLoader为null
            return;
        }
        // 因为 Spy 是被bootstrap classloader加载的，所以一定可以被找到，如果找不到的话，说明应用方的classloader实现有问题
        Class<?> spyClass = targetClassLoader.loadClass(Constants.SPY_CLASSNAME);

        final ClassLoader arthasClassLoader = Enhancer.class.getClassLoader();

        // 初始化间谍, AgentLauncher会把各种hook设置到ArthasClassLoader当中
        // 这里我们需要把这些hook取出来设置到目标classloader当中
        Method initMethod = spyClass.getMethod("init", ClassLoader.class, Method.class,
                Method.class, Method.class, Method.class, Method.class, Method.class);
        initMethod.invoke(null, arthasClassLoader,
                FieldUtils.getField(spyClass, "ON_BEFORE_METHOD").get(null),
                FieldUtils.getField(spyClass, "ON_RETURN_METHOD").get(null),
                FieldUtils.getField(spyClass, "ON_THROWS_METHOD").get(null),
                FieldUtils.getField(spyClass, "BEFORE_INVOKING_METHOD").get(null),
                FieldUtils.getField(spyClass, "AFTER_INVOKING_METHOD").get(null),
                FieldUtils.getField(spyClass, "THROW_INVOKING_METHOD").get(null));
	}
/*
Spy类中增加hook方法
ON_BEFORE_METHOD = methodOnBegin
ON_RETURN_METHOD = methodOnReturnEnd
ON_THROWS_METHOD = methodOnThrowingEnd
BEFORE_INVOKING_METHOD = methodOnInvokeBeforeTracing
AFTER_INVOKING_METHOD = methodOnInvokeAfterTracing
THROW_INVOKING_METHOD = methodOnInvokeThrowTracing
*/
```



```java
@Override
    public byte[] transform(final ClassLoader inClassLoader, String className, Class<?> classBeingRedefined,
                    ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException {
        try {
            // 这里要再次过滤一次，为啥？因为在transform的过程中，有可能还会再诞生新的类
            // 所以需要将之前需要转换的类集合传递下来，再次进行判断
            if (!matchingClasses.contains(classBeingRedefined)) {
                return null;
            }

            final ClassReader cr;

            // 首先先检查是否在缓存中存在Class字节码
            // 因为要支持多人协作,存在多人同时增强的情况
            final byte[] byteOfClassInCache = classBytesCache.get(classBeingRedefined);
            if (null != byteOfClassInCache) {
                cr = new ClassReader(byteOfClassInCache);
            }

            // 如果没有命中缓存,则从原始字节码开始增强
            else {
                cr = new ClassReader(classfileBuffer);
            }

            // 字节码增强
            final ClassWriter cw = new ClassWriter(cr, COMPUTE_FRAMES | COMPUTE_MAXS) {

                /*
                 * 注意，为了自动计算帧的大小，有时必须计算两个类共同的父类。
                 * 缺省情况下，ClassWriter将会在getCommonSuperClass方法中计算这些，通过在加载这两个类进入虚拟机时，使用反射API来计算。
                 * 但是，如果你将要生成的几个类相互之间引用，这将会带来问题，因为引用的类可能还不存在。
                 * 在这种情况下，你可以重写getCommonSuperClass方法来解决这个问题。
                 *
                 * 通过重写 getCommonSuperClass() 方法，更正获取ClassLoader的方式，改成使用指定ClassLoader的方式进行。
                 * 规避了原有代码采用Object.class.getClassLoader()的方式
                 */
                @Override
                protected String getCommonSuperClass(String type1, String type2) {
                    Class<?> c, d;
                    final ClassLoader classLoader = inClassLoader;
                    try {
                        c = Class.forName(type1.replace('/', '.'), false, classLoader);
                        d = Class.forName(type2.replace('/', '.'), false, classLoader);
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                    if (c.isAssignableFrom(d)) {
                        return type1;
                    }
                    if (d.isAssignableFrom(c)) {
                        return type2;
                    }
                    if (c.isInterface() || d.isInterface()) {
                        return "java/lang/Object";
                    } else {
                        do {
                            c = c.getSuperclass();
                        } while (!c.isAssignableFrom(d));
                        return c.getName().replace('.', '/');
                    }
                }

            };

            // 生成增强字节码
            cr.accept(new AdviceWeaver(adviceId, isTracing, skipJDKTrace, cr.getClassName(), methodNameMatcher, affect,
                            cw), EXPAND_FRAMES);
            final byte[] enhanceClassByteArray = cw.toByteArray();

            // 生成成功,推入缓存
            classBytesCache.put(classBeingRedefined, enhanceClassByteArray);

            // dump the class
            dumpClassIfNecessary(className, enhanceClassByteArray, affect);

            // 成功计数
            affect.cCnt(1);

            // 排遣间谍
            try {
                spy(inClassLoader);
            } catch (Throwable t) {
                logger.warn("print spy failed. classname={};loader={};", className, inClassLoader, t);
                throw t;
            }

            return enhanceClassByteArray;
        } catch (Throwable t) {
            logger.warn("transform loader[{}]:class[{}] failed.", inClassLoader, className, t);
        }

        return null;
    }
```



```java
 public static void methodOnBegin(
            int adviceId,
            ClassLoader loader, String className, String methodName, String methodDesc,
            Object target, Object[] args) {

        if (isSelfCallRef.get()) {
            return;
        } else {
            isSelfCallRef.set(true);
        }

        try {
            // 构建执行帧栈,保护当前的执行现场,方法执行完毕，进行出栈操作
            final GaStack<Object> frameStack = new ThreadUnsafeFixGaStack<Object>(FRAME_STACK_SIZE);
            frameStack.push(loader);
            frameStack.push(className);
            frameStack.push(methodName);
            frameStack.push(methodDesc);
            frameStack.push(target);
            frameStack.push(args);

            final AdviceListener listener = getListener(adviceId);
            frameStack.push(listener);

            // 获取通知器并做前置通知
            before(listener, loader, className, methodName, methodDesc, target, args);

            // 保护当前执行帧栈,压入线程帧栈
            threadFrameStackPush(frameStack);
        } finally {
            isSelfCallRef.set(false);
        }

    }
```
### ASM
对于ASM还处于初期阶段，下面给一些ASM的代码片段，方便理解ASM、阅读arthas中相关源码。

#### 增加方法的示例

##### 源码

```java
	public void printHello(){
		System.out.println(this);
	}
```

##### 字节码

```java
public void printHello();
    Code:
       0: getstatic     #2                  // Field java/lang/System.out:Ljava/io/PrintStream;
       3: aload_0
       4: invokevirtual #3                  // Method java/io/PrintStream.println:(Ljava/lang/Object;)V
       7: return
```

##### ASM生成字节码代码

```java
ClassWriter cw = new ClassWriter(0);
//访问com包下的Test类，
cw.visit(V1_5, ACC_PUBLIC, "com/Test", null, "java/lang/Object", null);
//增加 public 无返回、无入参 的 printHello
MethodVisitor mv = cw.visitMethod(ACC_PUBLIC , "printHello", "()V", "null", null);
//方法开始
mv.visitCode();
//获取静态变量 System.out 字段类型为 对象引用 PrintStream
mv.visitFieldInsn(GETSTATIC,"java/lang/System","out","Ljava/io/PrintStream;");
//加载this
mv.visitVarInsn(ALOAD,0);
//mv.visitLdcInsn("Hello"); //加载常量
//调用方法 println
mv.visitMethodInsn(INVOKEVIRTUAL,"java/io/PrintStream","println","(Ljava/lang/Object;)V",false);
//return
mv.visitInsn(RETURN);
//mv.visitMaxs(1, 1);
mv.visitEnd();
cw.visitEnd();
ClassReader cr = new ClassReader(klassBuffer);
cr.accept(cw, EXPAND_FRAMES);
//字节码写入文件
writeClass(cw.toByteArray(), "v.class");
```

#### 修改方法示例 

```java
ClassWriter cw = new ClassWriter(0);
ClassVisitor visitor = new ChangeClassAdapter(0, cw);
ClassReader cr = new ClassReader(klassBuffer);
cr.accept(visitor, EXPAND_FRAMES);
writeClass(cw.toByteArray(), "v.class");
```



```java
class ChangeClassAdapter extends ClassVisitor {
		public ChangeClassAdapter(int api, ClassVisitor cv) {
			super(ASM4, cv);
		}

		@Override public void visit(int version, int access, String name, String signature, String superName,
				String[] interfaces) {
			cv.visit(V1_5, access, name, signature, superName, interfaces); //修改java version
			//super.visit(version, access, name, signature, superName, interfaces);
		}

		@Override public MethodVisitor visitMethod(int access, String name, String desc, String signature,
				String[] exceptions) {
			MethodVisitor mv = super.visitMethod(access, name, desc, signature, exceptions);
      //通过AdviceAdapter修改方法
			return new AdviceAdapter(Opcodes.ASM5, new JSRInlinerAdapter(mv, access, name, desc, signature, exceptions),
					access, name, desc) {
				@Override public void visitCode() {
					super.visitCode();
				}

				@Override public void visitMethodInsn(int i, String s, String s1, String s2, boolean b) {
          //此处也可以针对方法进行修改
					super.visitMethodInsn(i, s, s1, s2, b);
				}

				@Override protected void onMethodEnter() {
          //修改方法进入
					mv.visitMethodInsn(INVOKESTATIC, "java/lang/System", "currentTimeMillis", "()J");
					super.onMethodEnter();
				}

				@Override protected void onMethodExit(int i) {
          //修改方法退出
					mv.visitMethodInsn(INVOKESTATIC, "java/lang/System", "currentTimeMillis", "()J");
					super.onMethodExit(i);
				}
			};
		}

		@Override public void visitEnd() {
			super.visitEnd();
		}
	}
```


## 总结

1、源码中trace命令使用自实现的lock。

2、trace命令使用编织字节码。

