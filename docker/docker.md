# Docker

## Namespace



## Cgroup





## UnionFS



##code snapshot

```go
//overlay方式 挂载文件 
//func Mount(source string, target string, fstype string, flags uintptr, data string) (err error)
unix.Mount("none", "/var/run/gocker/containers/containerid/fs/mnt", "overlay", 0, "lowerdir=/var/lib/gocker/images,upperdir=,workdir=")

```



## net bridge

```go
	//利用go创建一个网桥
	linkAttrs := netlink.NewLinkAttrs()
	linkAttrs.Name = "bridge0"
	gBridge := &netlink.Bridge{LinkAttrs: linkAttrs}
	if err := netlink.LinkAdd(gBridge); err != nil {
		return err
	}
	//设置子网掩码
	addr, _ := netlink.ParseAddr("172.29.0.1/24") 
	netlink.AddrAdd(gBridge, addr)
	netlink.LinkSetUp(gBridge)
```

