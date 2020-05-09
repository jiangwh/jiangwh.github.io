# Spring中的事务处理

## 事务

- 原子性： 事务是最小的执行单位，不允许分割。事务的原子性确保动作要么全部完成，要么完全不起作用；
- 一致性： 执行事务前后，数据保持一致；
- 隔离性： 并发访问数据库时，一个用户的事物不被其他事务所干扰也就是说多个事务并发执行时，一个事务的执行不应影响其他事务的执行；
- 持久性:  一个事务被提交之后。它对数据库中数据的改变是持久的，即使数据库发生故障也不应该对其有任何影响。

谈到事务会涉及几个基本概念：

1、开始事务（begin transaction）

2、事务结束（rollback，commit）

3、事务隔离级别

## 事务的具体表现

以PG为例子

```plsql
BEGIN TRANSACTION;
select * from t_user where id=32768;
commit;
-- rollback;
```

```sql
-- 查看数据库的数据库级别
select current_setting('transaction_isolation'); 
show default_transaction_isolation;

-- 修改事务级别
begin;
set transaction isolation level serializable;
commit;
-- 设置会话
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

> 事务级别解释

```
dirty read    
A transaction reads data written by a concurrent uncommitted transaction.  
脏读：一个事务读取到另外一个事务未提交的数据。

nonrepeatable read  
A transaction re-reads data it has previously read and finds that data has been modified by another transaction (that committed since the initial read).  
不可重复读：一个事务再次读取数据时，发现 数据被例外一个事务修改了。
不可重复读没有行级锁。

phantom read  
A transaction re-executes a query returning a set of rows that satisfy a search condition and finds that the set of rows satisfying the condition has changed due to another recently-committed transaction.  
幻读：一个事务再次执行一个不改变查询条件的查询语句时发现返回的结果集增加了。
幻读存在纪录的行级锁。

serialization anomaly
The result of successfully committing a group of transactions is inconsistent with all possible orderings of running those transactions one at a time.
```

```sql
READ_UNCOMMITTED  支持脏读

A constant indicating that dirty reads, non-repeatable reads and phantom reads can occur. This level allows a row changed by one transaction to be read by another transaction before any changes in that row have been committed (a "dirty read"). If any of the changes are rolled back, the second transaction will have retrieved an invalid row.

1、T1：insert into `users`(`id`, `name`) values (1, 'XXX');
2、T2：select * from users where id=1;
T1事务未提交，T2事务可以读取。

READ_COMMITTED
阻止脏读，存在幻读以及不可重复读。
A constant indicating that dirty reads are prevented; non-repeatable reads and phantom reads can occur. This level only prohibits a transaction from reading a row with uncommitted changes in it.

不可重复读
1、T1：select * from users where id=1;
2、T2：update users set name="test" where id=1
3、T1: select * from users where id=1;
T1事务两次结果不一致。

REPEATABLE_READ
阻止脏读及不可重复读。存在幻读。
A constant indicating that dirty reads and non-repeatable reads are prevented; phantom reads can occur. This level prohibits a transaction from reading a row with uncommitted changes in it, and it also prohibits the situation where one transaction reads a row, a second transaction alters the row, and the first transaction rereads the row, getting different values the second time (a "non-repeatable read").

1、T1：select * from users where id = 1; -- null
2、T2：insert into `users`(`id`, `name`) values (1, 'XXX');
3、T1：select * from users where id = 1; -- null

T1查询users表不存在id为1的数据，T1再次查询id为1的数据不为空，这个叫幻读。

SERIALIZABLE
A constant indicating that dirty reads, non-repeatable reads and phantom reads are prevented. This level includes the prohibitions in ISOLATION_REPEATABLE_READ and further prohibits the situation where one transaction reads all rows that satisfy a WHERE condition, a second transaction inserts a row that satisfies that WHERE condition, and the first transaction rereads for the same condition, retrieving the additional "phantom" row in the second read.
```

## Spring中的事务

1、PlatformTransactionManager

2、TransactionDefinition

3、SavepointManager

4、TransactionStatus





### 事务提交

commit

```java
	/*
	public abstract class AbstractLogicalConnectionImplementor implements LogicalConnectionImplementor, PhysicalJdbcTransaction {
	*/
	@Override
	public void commit() {
		try {
			log.trace( "Preparing to commit transaction via JDBC Connection.commit()" );
			getConnectionForTransactionManagement().commit();
			status = TransactionStatus.COMMITTED;
			log.trace( "Transaction committed via JDBC Connection.commit()" );
		}
		catch( SQLException e ) {
			status = TransactionStatus.FAILED_COMMIT;
			throw new TransactionException( "Unable to commit against JDBC Connection", e );
		}

		afterCompletion();
	}
```

```java
/*public class ConnectionImpl extends ConnectionPropertiesImpl implements MySQLConnection {*/
//这是mysql启动的提交事务
public void commit() throws SQLException {
        synchronized (getConnectionMutex()) {
            checkClosed();

            try {
                if (this.connectionLifecycleInterceptors != null) {
                    IterateBlock<Extension> iter = new IterateBlock<Extension>(this.connectionLifecycleInterceptors.iterator()) {

                        @Override
                        void forEach(Extension each) throws SQLException {
                            if (!((ConnectionLifecycleInterceptor) each).commit()) {
                                this.stopIterating = true;
                            }
                        }
                    };

                    iter.doForAll();

                    if (!iter.fullIteration()) {
                        return;
                    }
                }

                // no-op if _relaxAutoCommit == true
                if (this.autoCommit && !getRelaxAutoCommit()) {
                    throw SQLError.createSQLException("Can't call commit when autocommit=true", getExceptionInterceptor());
                } else if (this.transactionsSupported) {
                    if (getUseLocalTransactionState() && versionMeetsMinimum(5, 0, 0)) {
                        if (!this.io.inTransactionOnServer()) {
                            return; // effectively a no-op
                        }
                    }

                    execSQL(null, "commit", -1, null, DEFAULT_RESULT_SET_TYPE, DEFAULT_RESULT_SET_CONCURRENCY, false, this.database, null, false);
                }
            } catch (SQLException sqlException) {
                if (SQLError.SQL_STATE_COMMUNICATION_LINK_FAILURE.equals(sqlException.getSQLState())) {
                    throw SQLError.createSQLException("Communications link failure during commit(). Transaction resolution unknown.",
                            SQLError.SQL_STATE_TRANSACTION_RESOLUTION_UNKNOWN, getExceptionInterceptor());
                }

                throw sqlException;
            } finally {
                this.needsPing = this.getReconnectAtTxEnd();
            }
        }
        return;
    }
```

### 事务回滚







### save point

```java
 private void setSavepoint(MysqlSavepoint savepoint) throws SQLException {

        synchronized (getConnectionMutex()) {
            if (versionMeetsMinimum(4, 0, 14) || versionMeetsMinimum(4, 1, 1)) {
                checkClosed();

                StringBuilder savePointQuery = new StringBuilder("SAVEPOINT ");
                savePointQuery.append('`');
                savePointQuery.append(savepoint.getSavepointName());
                savePointQuery.append('`');

                java.sql.Statement stmt = null;

                try {
                    stmt = getMetadataSafeStatement();

                    stmt.executeUpdate(savePointQuery.toString());
                } finally {
                    closeStatement(stmt);
                }
            } else {
                throw SQLError.createSQLFeatureNotSupportedException();
            }
        }
    }
```



```java
/**/

public void rollback(final Savepoint savepoint) throws SQLException {

        synchronized (getConnectionMutex()) {
            if (versionMeetsMinimum(4, 0, 14) || versionMeetsMinimum(4, 1, 1)) {
                checkClosed();

                try {
                    if (this.connectionLifecycleInterceptors != null) {
                        IterateBlock<Extension> iter = new IterateBlock<Extension>(this.connectionLifecycleInterceptors.iterator()) {

                            @Override
                            void forEach(Extension each) throws SQLException {
                                if (!((ConnectionLifecycleInterceptor) each).rollback(savepoint)) {
                                    this.stopIterating = true;
                                }
                            }
                        };

                        iter.doForAll();

                        if (!iter.fullIteration()) {
                            return;
                        }
                    }

                    StringBuilder rollbackQuery = new StringBuilder("ROLLBACK TO SAVEPOINT ");
                    rollbackQuery.append('`');
                    rollbackQuery.append(savepoint.getSavepointName());
                    rollbackQuery.append('`');

                    java.sql.Statement stmt = null;

                    try {
                        stmt = getMetadataSafeStatement();

                        stmt.executeUpdate(rollbackQuery.toString());
                    } catch (SQLException sqlEx) {
                        int errno = sqlEx.getErrorCode();

                        if (errno == 1181) {
                            String msg = sqlEx.getMessage();

                            if (msg != null) {
                                int indexOfError153 = msg.indexOf("153");

                                if (indexOfError153 != -1) {
                                    throw SQLError.createSQLException("Savepoint '" + savepoint.getSavepointName() + "' does not exist",
                                            SQLError.SQL_STATE_ILLEGAL_ARGUMENT, errno, getExceptionInterceptor());
                                }
                            }
                        }

                        // We ignore non-transactional tables if told to do so
                        if (getIgnoreNonTxTables() && (sqlEx.getErrorCode() != SQLError.ER_WARNING_NOT_COMPLETE_ROLLBACK)) {
                            throw sqlEx;
                        }

                        if (SQLError.SQL_STATE_COMMUNICATION_LINK_FAILURE.equals(sqlEx.getSQLState())) {
                            throw SQLError.createSQLException("Communications link failure during rollback(). Transaction resolution unknown.",
                                    SQLError.SQL_STATE_TRANSACTION_RESOLUTION_UNKNOWN, getExceptionInterceptor());
                        }

                        throw sqlEx;
                    } finally {
                        closeStatement(stmt);
                    }
                } finally {
                    this.needsPing = this.getReconnectAtTxEnd();
                }
            } else {
                throw SQLError.createSQLFeatureNotSupportedException();
            }
        }
    }

```

