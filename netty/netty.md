

# netty的零复制处理

### zero-copy

零复制在操作系统层面的概念

在传统的网络应用，传送的数据会经过网卡、内核、应用（用户空间），这三个阶段的数据通信是通过复制搞定的。

零复制就是在减少以上几个阶段的复制，提高性能。

linux中支持zero-copy的函数：mmap、sendfile、splice。

```sendfile With DMA Scatter/Gather Copy```

## netty中的zero-copy

下面是netty中读取数据的代码与正常的应用程序并无本质区别。

```java
    @Override
    public int setBytes(int index, ScatteringByteChannel in, int length) throws IOException{
        checkIndex(index, length);
        ByteBuffer tmpBuf = internalNioBuffer();
        index = idx(index);
        tmpBuf.clear().position(index).limit(index + length);
        try {
          	
            return in.read(tmpBuf);//将
        } catch (ClosedChannelException ignored) {
            return -1;
        }
    }
	//	class DirectByteBuffer extends MappedByteBuffer implements DirectBuffer
```

netty中零复制的体现，就是netty中bytebuf，bytebuf减少了应用层的数据复制操作。

```java
    @Override
    public ByteBuf slice(int index, int length) {
        ensureAccessible();
        return new UnpooledSlicedByteBuf(this, index, length);
    }
		//未对buffer进行复制操作，只是复制了一份索引、长度。
```
发送数据流为文件时，采用FileChannel
```java
 private int doWriteInternal(ChannelOutboundBuffer in, Object msg) throws Exception {
        if (msg instanceof ByteBuf) {
            ByteBuf buf = (ByteBuf) msg;
            if (!buf.isReadable()) {
                in.remove();
                return 0;
            }

            final int localFlushedAmount = doWriteBytes(buf);
            if (localFlushedAmount > 0) {
                in.progress(localFlushedAmount);
                if (!buf.isReadable()) {
                    in.remove();
                }
                return 1;
            }
        } else if (msg instanceof FileRegion) {
            FileRegion region = (FileRegion) msg;
            if (region.transferred() >= region.count()) {
                in.remove();
                return 0;
            }
						//文件写操作，直接使用了FileChannel的transferTo方法，避免了文件流的复制。底层使用了sendfile
            long localFlushedAmount = doWriteFileRegion(region);
            if (localFlushedAmount > 0) {
                in.progress(localFlushedAmount);
                if (region.transferred() >= region.count()) {
                    in.remove();
                }
                return 1;
            }
        } else {
            // Should not reach here.
            throw new Error();
        }
        return WRITE_STATUS_SNDBUF_FULL;
    }
```

