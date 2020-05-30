# raft

raft是一个易懂的一致性算法。

算法介绍：https://raft.github.io/

parer: https://raft.github.io/raft.pdf

rocketmq使用raft协议处理broken集群消息备份的一致性问题。

## 一些简单概念

raft协议中一些概念：

1、leader 领导者。

2、follower 跟随者

3、candidate 候选者

4、term 任期

5、heartBeat 心跳

6、vote 选票



## 在rocketmq raft协议处理

在节点启动时，所有节点的角色都是follower。raft利用每个节点的随机等待时间，尽量让在没有leader节点的情况，一个follower转为candidate并拉取选票。

### 领导者

```java
private void maintainAsLeader() throws Exception {
        if (DLedgerUtils.elapsed(lastSendHeartBeatTime) > heartBeatTimeIntervalMs) {
          	//心跳间隔超过设定时间
            long term;
            String leaderId;
            synchronized (memberState) {
                if (!memberState.isLeader()) {
                    //stop sending
                    return;
                }
              	/*只有领导节点才做该动作*/
                term = memberState.currTerm(); //设置当前人气
                leaderId = memberState.getLeaderId(); //当前领导者的ID 
                lastSendHeartBeatTime = System.currentTimeMillis(); //设置发送心跳时间
            }
            sendHeartbeats(term, leaderId); //leader有发送心跳包的责任
        }
    }
```
### 跟随者
```java
 private void maintainAsFollower() {
        if (DLedgerUtils.elapsed(lastLeaderHeartBeatTime) > 2 * heartBeatTimeIntervalMs) {
            synchronized (memberState) {
                if (memberState.isFollower() && (DLedgerUtils.elapsed(lastLeaderHeartBeatTime) > maxHeartBeatLeak * heartBeatTimeIntervalMs)) {
                    logger.info("[{}][HeartBeatTimeOut] lastLeaderHeartBeatTime: {} heartBeatTimeIntervalMs: {} lastLeader={}", memberState.getSelfId(), new Timestamp(lastLeaderHeartBeatTime), heartBeatTimeIntervalMs, memberState.getLeaderId());
                  //长时间收到心跳报文，更新为候选者
                    changeRoleToCandidate(memberState.currTerm());
                }
            }
        }
    }
```

### 候选者

```java
private void maintainAsCandidate() throws Exception {
        //for candidate
        if (System.currentTimeMillis() < nextTimeToRequestVote && !needIncreaseTermImmediately) {
            return;
        }
        long term;
        long ledgerEndTerm;
        long ledgerEndIndex;
        synchronized (memberState) {
            if (!memberState.isCandidate()) {
                return;
            }
            if (lastParseResult == VoteResponse.ParseResult.WAIT_TO_VOTE_NEXT || needIncreaseTermImmediately) {
                long prevTerm = memberState.currTerm();
                term = memberState.nextTerm();
                logger.info("{}_[INCREASE_TERM] from {} to {}", memberState.getSelfId(), prevTerm, term);
                lastParseResult = VoteResponse.ParseResult.WAIT_TO_REVOTE;
            } else {
                term = memberState.currTerm();
            }
            ledgerEndIndex = memberState.getLedgerEndIndex();
            ledgerEndTerm = memberState.getLedgerEndTerm();
        }
        if (needIncreaseTermImmediately) {
          	//变更任期
            nextTimeToRequestVote = getNextTimeToRequestVote();
            needIncreaseTermImmediately = false;
            return;
        }

        long startVoteTimeMs = System.currentTimeMillis();
  			//法定选票相应，需要带上任期
        final List<CompletableFuture<VoteResponse>> quorumVoteResponses = voteForQuorumResponses(term, ledgerEndTerm, ledgerEndIndex);
        final AtomicLong knownMaxTermInGroup = new AtomicLong(-1);
        final AtomicInteger allNum = new AtomicInteger(0);
        final AtomicInteger validNum = new AtomicInteger(0);
        final AtomicInteger acceptedNum = new AtomicInteger(0); //同意票数量
        final AtomicInteger notReadyTermNum = new AtomicInteger(0);
        final AtomicInteger biggerLedgerNum = new AtomicInteger(0);
        final AtomicBoolean alreadyHasLeader = new AtomicBoolean(false); //已经有领导了

        CountDownLatch voteLatch = new CountDownLatch(1); 
        for (CompletableFuture<VoteResponse> future : quorumVoteResponses) {
          //唱票
            future.whenComplete((VoteResponse x, Throwable ex) -> {
                try {
                    if (ex != null) {
                        throw ex;
                    }
                    logger.info("[{}][GetVoteResponse] {}", memberState.getSelfId(), JSON.toJSONString(x));
                    if (x.getVoteResult() != VoteResponse.RESULT.UNKNOWN) {
                        validNum.incrementAndGet();
                    }
                    synchronized (knownMaxTermInGroup) {
                        switch (x.getVoteResult()) {
                            case ACCEPT:
                                acceptedNum.incrementAndGet();
                                break;
                            case REJECT_ALREADY_VOTED:
                            case REJECT_TAKING_LEADERSHIP:
                                break;
                            case REJECT_ALREADY_HAS_LEADER:
                                alreadyHasLeader.compareAndSet(false, true);
                                break;
                            case REJECT_TERM_SMALL_THAN_LEDGER:
                            case REJECT_EXPIRED_VOTE_TERM:
                                if (x.getTerm() > knownMaxTermInGroup.get()) {
                                    knownMaxTermInGroup.set(x.getTerm());
                                }
                                break;
                            case REJECT_EXPIRED_LEDGER_TERM:
                            case REJECT_SMALL_LEDGER_END_INDEX:
                                biggerLedgerNum.incrementAndGet();
                                break;
                            case REJECT_TERM_NOT_READY:
                                notReadyTermNum.incrementAndGet();
                                break;
                            default:
                                break;

                        }
                    }
                    if (alreadyHasLeader.get() //已经存在领导
                        || memberState.isQuorum(acceptedNum.get()) //同意人数大于一般
                        || memberState.isQuorum(acceptedNum.get() + notReadyTermNum.get())) 
                    {
     										//选举已经出结果
                        voteLatch.countDown();
                    }
                } catch (Throwable t) {
                    logger.error("vote response failed", t);
                } finally {
                    allNum.incrementAndGet();
                    if (allNum.get() == memberState.peerSize()) {
                        //所有人都投票，选举出结构
                        voteLatch.countDown();
                    }
                }
            });

        }
        try {
          	//等待选举结果最长：3秒+随机时间。防止在偶数候选人时形成脑裂。
            voteLatch.await(3000 + random.nextInt(maxVoteIntervalMs), TimeUnit.MILLISECONDS);
        } catch (Throwable ignore) {

        }
        lastVoteCost = DLedgerUtils.elapsed(startVoteTimeMs);
        VoteResponse.ParseResult parseResult;
  			//如果组最大任期大于当前任期。
        if (knownMaxTermInGroup.get() > term) {
            parseResult = VoteResponse.ParseResult.WAIT_TO_VOTE_NEXT;
          	//获取下次选举时间。
            nextTimeToRequestVote = getNextTimeToRequestVote();
          	//转为候选人，最大任期作为参数传入。
            changeRoleToCandidate(knownMaxTermInGroup.get());
        } else if (alreadyHasLeader.get()) {
          	//如果已经有领导者了。
            parseResult = VoteResponse.ParseResult.WAIT_TO_REVOTE;
            nextTimeToRequestVote = getNextTimeToRequestVote() + heartBeatTimeIntervalMs * maxHeartBeatLeak;
        } else if (!memberState.isQuorum(validNum.get())) {
          	//有效选票小于半票
            parseResult = VoteResponse.ParseResult.WAIT_TO_REVOTE;
            nextTimeToRequestVote = getNextTimeToRequestVote();
        } else if (memberState.isQuorum(acceptedNum.get())) {
          	//有效选票大于半票
            parseResult = VoteResponse.ParseResult.PASSED;
        } else if (memberState.isQuorum(acceptedNum.get() + notReadyTermNum.get())) {
          	//如果选票+无效任期数量 大于 半数，立刻重选。
            parseResult = VoteResponse.ParseResult.REVOTE_IMMEDIATELY;
        } else if (memberState.isQuorum(acceptedNum.get() + biggerLedgerNum.get())) {
          	//等待重新选举
            parseResult = VoteResponse.ParseResult.WAIT_TO_REVOTE;
            nextTimeToRequestVote = getNextTimeToRequestVote();
        } else {
            parseResult = VoteResponse.ParseResult.WAIT_TO_VOTE_NEXT;
            nextTimeToRequestVote = getNextTimeToRequestVote();
        }
        lastParseResult = parseResult;
        logger.info("[{}] [PARSE_VOTE_RESULT] cost={} term={} memberNum={} allNum={} acceptedNum={} notReadyTermNum={} biggerLedgerNum={} alreadyHasLeader={} maxTerm={} result={}",
            memberState.getSelfId(), lastVoteCost, term, memberState.peerSize(), allNum, acceptedNum, notReadyTermNum, biggerLedgerNum, alreadyHasLeader, knownMaxTermInGroup.get(), parseResult);

        if (parseResult == VoteResponse.ParseResult.PASSED) {
            logger.info("[{}] [VOTE_RESULT] has been elected to be the leader in term {}", memberState.getSelfId(), term);
          	//如果选举通过，那么成为领导者
            changeRoleToLeader(term);
        }
    }
```

## 消息同步

在raft协议中只有领导者才进行消息的发布，因此只能在leader节点进行写操作。

leader节点日志必须是有序的，如果flower节点的序列小雨

```
@Override
public void doWork() {
    try {
        if (!checkAndFreshState()) {
            waitForRunning(1);
            return;
        }

        if (type.get() == PushEntryRequest.Type.APPEND) {
            if (dLedgerConfig.isEnableBatchPush()) {
                doBatchAppend();
            } else {
                doAppend();
            }
        } else {
            doCompare();
        }
        waitForRunning(1);
    } catch (Throwable t) {
        DLedgerEntryPusher.logger.error("[Push-{}]Error in {} writeIndex={} compareIndex={}", peerId, getName(), writeIndex, compareIndex, t);
        DLedgerUtils.sleep(500);
    }
}
```

