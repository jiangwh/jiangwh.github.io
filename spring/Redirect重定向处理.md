# Redirect重定向处理

spring security 中对重定向处理的默认策略是返回全路径，这样的好处是可以支持协议转换。如果对协议不需要处理，可以直接返回相对路径。我们在应用上做一些跳转时，一定仔细分析（这些都是隐含的约束性需求）看看采用哪一种方式适应相关场景的需求。

源码如下：


```java
/*
 * Copyright 2002-2016 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.security.web;

import java.io.IOException;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.security.web.util.UrlUtils;

/**
 * Simple implementation of <tt>RedirectStrategy</tt> which is the default used throughout
 * the framework.
 *
 * @author Luke Taylor
 * @since 3.0
 */
public class DefaultRedirectStrategy implements RedirectStrategy {

	protected final Log logger = LogFactory.getLog(getClass());

	private boolean contextRelative;

	/**
	 * Redirects the response to the supplied URL.
	 * <p>
	 * If <tt>contextRelative</tt> is set, the redirect value will be the value after the
	 * request context path. Note that this will result in the loss of protocol
	 * information (HTTP or HTTPS), so will cause problems if a redirect is being
	 * performed to change to HTTPS, for example.
	 */
	public void sendRedirect(HttpServletRequest request, HttpServletResponse response,
			String url) throws IOException {
		String redirectUrl = calculateRedirectUrl(request.getContextPath(), url);
		redirectUrl = response.encodeRedirectURL(redirectUrl);

		if (logger.isDebugEnabled()) {
			logger.debug("Redirecting to '" + redirectUrl + "'");
		}

		response.sendRedirect(redirectUrl);
	}

	protected String calculateRedirectUrl(String contextPath, String url) {
		//判断是否为绝对路径，采用正则匹配
		if (!UrlUtils.isAbsoluteUrl(url)) {
			//是否需要返回相对路径
			if (isContextRelative()) {
				return url;
			}
			else {
				return contextPath + url;
			}
		}

		// Full URL, including http(s)://

		if (!isContextRelative()) {
			return url;
		}

		//计算出相对路径
		// Calculate the relative URL from the fully qualified URL, minus the last
		// occurrence of the scheme and base context.
		url = url.substring(url.lastIndexOf("://") + 3); // strip off scheme
		url = url.substring(url.indexOf(contextPath) + contextPath.length());

		if (url.length() > 1 && url.charAt(0) == '/') {
			url = url.substring(1);
		}

		return url;
	}

	/**
	 * If <tt>true</tt>, causes any redirection URLs to be calculated minus the protocol
	 * and context path (defaults to <tt>false</tt>).
	 */
	public void setContextRelative(boolean useRelativeContext) {
		this.contextRelative = useRelativeContext;
	}

	/**
	 * Returns <tt>true</tt>, if the redirection URL should be calculated
	 * minus the protocol and context path (defaults to <tt>false</tt>).
	 */
	protected boolean isContextRelative() {
		return contextRelative;
	}
}
```


如果分析过程中存在错误点，请大家评批指点。一起学习，共同进步。

```
作者：仁蕴。
邮箱：jiang_wh@126.com 
github：https://github.com/jiangwh/blog
```
