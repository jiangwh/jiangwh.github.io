# Arthas 中使用的反编译器

arthas使用cfr反编译器，该反编译器可以反编译lamda表达式。



## Arthas 使用反编译命令示例

```bash
jad {namespace.classname} {method}
method 为可以选择项
反编译时，可以指定classload进行反编译。
具体使用方式可以参考：https://alibaba.github.io/arthas/jad.html
```

## cfr反编译器使用的简单示例

```java
		final StringBuilder result = new StringBuilder(8192);
		OutputSinkFactory mySink = new OutputSinkFactory() {
			@Override
			public List<SinkClass> getSupportedSinks(SinkType sinkType, Collection<SinkClass> collection) {
				return Arrays.asList(SinkClass.STRING, SinkClass.DECOMPILED, SinkClass.DECOMPILED_MULTIVER,
						SinkClass.EXCEPTION_MESSAGE);
			}

			@Override
			public <T> Sink<T> getSink(final SinkType sinkType, SinkClass sinkClass) {
				return new Sink<T>() {
					@Override
					public void write(T sinkable) {
						if (sinkType == SinkType.PROGRESS) {
							return;
						}
						result.append(sinkable);
					}
				};
			}
		};
		HashMap<String, String> options = new HashMap<String, String>();
		options.put("showversion", "false");
		CfrDriver driver = new CfrDriver.Builder().withOptions(options).withOutputSink(mySink).build();
		driver.analyse(Lists.newArrayList("a.class")); //待反编译的class
		System.out.println(result.toString());
```

## Arthas中相关源代码

要实现反编译，那么需要两个条件：

1、待反编译的字节码。

2、反编译器

获取字节码文件

```java
ClassDumpTransformer transformer = new ClassDumpTransformer(allClasses);
//由于arthas中的字节码经过enhance,需要镜像转换。
retransformClasses(inst, transformer, allClasses);
Map<Class<?>, File> classFiles = transformer.getDumpResult();
File classFile = classFiles.get(c);
```

调用反编译器。

```java
//调用反编译器代码。
public static String decompile(String classFilePath, String methodName) {
        final StringBuilder result = new StringBuilder(8192);

        OutputSinkFactory mySink = new OutputSinkFactory() {
            @Override
            public List<SinkClass> getSupportedSinks(SinkType sinkType, Collection<SinkClass> collection) {
                return Arrays.asList(SinkClass.STRING, SinkClass.DECOMPILED, SinkClass.DECOMPILED_MULTIVER,
                                SinkClass.EXCEPTION_MESSAGE);
            }

            @Override
            public <T> Sink<T> getSink(final SinkType sinkType, SinkClass sinkClass) {
                return new Sink<T>() {
                    @Override
                    public void write(T sinkable) {
                        // skip message like: Analysing type demo.MathGame
                        if (sinkType == SinkType.PROGRESS) {
                            return;
                        }
                        result.append(sinkable);
                    }
                };
            }
        };

        HashMap<String, String> options = new HashMap<String, String>();
        /**
         * @see org.benf.cfr.reader.util.MiscConstants.Version.getVersion() Currently,
         *      the cfr version is wrong. so disable show cfr version.
         */
        options.put("showversion", "false");
        if (!StringUtils.isBlank(methodName)) {
            options.put("methodname", methodName);
        }

        CfrDriver driver = new CfrDriver.Builder().withOptions(options).withOutputSink(mySink).build();
        List<String> toAnalyse = new ArrayList<String>();
        toAnalyse.add(classFilePath);
        driver.analyse(toAnalyse);
        return result.toString();
    }

```

