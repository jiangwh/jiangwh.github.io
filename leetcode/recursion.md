# 递归模版

递归：

1、return 返回条件

2、process 处理业务逻辑

3、drill down 下转

4、revert 状态清除



分治：

1、return 返回条件

2、process 处理业务逻辑

​	如何拆分当前问题

3、drill down 下转	

4、conquer subproblems 

5、revert 状态清除



动态规划：

```python
function DP():
  db=[][] #二维
  for i= 0 ... M{
    for j= 0 ... N{
      dp[i][j]=_function(dp[i'][j']...)
    }
  }
  return dp[m][n]

```







深度

```python
visited = set()
def dfs(node,visited):
  visited.add(node)
  #process current node
  
  for next_node in node.children():
    if not next_node in visited:
      dfs(next_node,visited)
```



```python
def bfs(graph,start,end):
  queue=[]
  queue.append([start])
  
```



