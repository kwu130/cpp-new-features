# `scoped_lock` 与 `shared_mutex`

`scoped_lock` 可以一次安全锁定多个互斥量，降低锁顺序不一致造成死锁的风险。`shared_mutex` 提供共享读与独占写。

<!-- example id="cpp17-concurrency" std="c++17" file="main.cpp" kind="single" compilers="all" output="left=1, right=2" -->
```cpp
#include <iostream>
#include <mutex>
#include <shared_mutex>

int main() {
    std::mutex left_mutex;
    std::mutex right_mutex;
    int left = 0;
    int right = 0;
    {
        std::scoped_lock lock(left_mutex, right_mutex);
        left = 1;
        right = 2;
    }

    std::shared_mutex read_mutex;
    std::shared_lock<std::shared_mutex> read_lock(read_mutex);
    std::cout << "left=" << left << ", right=" << right << '\n';
}
```

共享锁并不一定比普通互斥量快；只有读多写少且临界区足够大时才可能受益。持锁期间应避免调用未知代码或执行缓慢 I/O。

## `scoped_lock` 的死锁避免

同时按固定但不一致顺序逐个 `lock` 两个互斥量容易形成循环等待。多参数 `scoped_lock` 使用与 `std::lock` 等价的死锁避免算法取得全部锁，并在析构时释放。构造期间若获取失败，已取得的锁会被正确释放。

它是不可复制的 RAII 所有者，通常让作用域直接表达临界区。单互斥量时效果类似 `lock_guard`；多锁时不要在外部预先锁住其中一把，除非使用明确的采用锁协议。

<!-- example id="cpp17-scoped-lock-opposite-order" std="c++17" file="main.cpp" kind="single" compilers="all" output="left=2000, right=2000" -->
```cpp
#include <iostream>
#include <mutex>
#include <thread>

int main() {
    std::mutex left_mutex;
    std::mutex right_mutex;
    int left = 0;
    int right = 0;

    auto update = [&](bool reverse) {
        for (int count = 0; count < 1000; ++count) {
            if (reverse) {
                std::scoped_lock lock(right_mutex, left_mutex);
                ++left;
                ++right;
            } else {
                std::scoped_lock lock(left_mutex, right_mutex);
                ++left;
                ++right;
            }
        }
    };

    std::thread first(update, false);
    std::thread second(update, true);
    first.join();
    second.join();

    std::cout << "left=" << left << ", right=" << right << '\n';
}
```

两个线程故意以相反参数顺序请求同一组锁；`scoped_lock` 的多锁获取协议避免简单的“各持一把再等另一把”循环等待。锁内同时递增两个值，使 `left == right` 成为受保护的不变量。程序内部通过确定性最终结果验证，而不依赖线程交错顺序。

### 构造形式与锁类型要求

CTAD 让 `std::scoped_lock lock(m1, m2)` 推导互斥量类型。零互斥量的 `scoped_lock<>` 是合法的无操作守卫，单互斥量版本只要求基本互斥接口；多互斥量版本需要支持 `try_lock` 等死锁避免算法所需操作。

采用锁构造形式接收 `adopt_lock_t`，表示调用方已经拥有全部互斥量，守卫只负责最终解锁。错误地采用未持有的锁或漏掉其中一把会破坏前置条件。普通代码优先让构造函数自己获取锁。

`scoped_lock` 不提供手动 `unlock()`、延迟锁定或所有权转移；需要这些能力时使用 `unique_lock`。较小接口使它适合严格词法作用域，也减少提前解锁导致不变量暴露的机会。

## `shared_mutex` 与 C++14 版本

C++17 `shared_mutex` 提供共享和独占模式但不要求定时接口，相比 C++14 `shared_timed_mutex` 可以让不需要超时的实现更直接。读者用 `shared_lock`，写者用 `unique_lock`。

标准仍不规定公平性。读者持续到来时写者是否饥饿由实现策略决定。读锁内部通常需要更新共享状态，极端读并发会竞争同一缓存行。

共享接口是 `lock_shared`、`try_lock_shared`、`unlock_shared`，独占接口与普通互斥量一致。`shared_lock<shared_mutex>` 是共享所有权 RAII 包装器，`unique_lock<shared_mutex>` 是独占包装器；直接使用 `lock_guard` 也只能取得独占锁。

标准没有提供原子的共享锁升级。读线程发现需要写入时，释放共享锁再获取独占锁会打开竞争窗口，必须在独占锁下重新检查状态。试图同时持有共享锁并再请求独占锁可能自锁。

返回被保护容器的迭代器或引用后销毁 `shared_lock`，并没有把保护传递给调用方。可以返回值快照、让回调在锁作用域内执行，或返回同时拥有锁与访问句柄的受控对象。

## 内存可见性

释放独占锁 happens-before 随后成功获取同一互斥量的共享或独占锁，因此受保护写入对读者可见。仅把字段声明为 `const` 或只在业务上“读取”不会创建同步关系。

互斥量保护的是访问协议而非某个内存地址的固有属性。所有访问同一非原子状态的线程都必须遵守同一锁约定；某条“只读快速路径”绕过锁仍可与写线程形成数据竞争。

不要在持锁期间调用未知回调、执行网络 I/O 或等待另一个可能反向依赖当前锁的任务。即使没有严格死锁，长时间持锁也会把共享结构变成串行瓶颈。先在锁内复制必要状态，再在锁外执行昂贵工作，是常用边界设计。

## 死锁避免不是事务

`scoped_lock` 只协调获取一组进程内 BasicLockable 对象，不会让锁内对外部系统的多个写入获得事务原子性。更新文件、数据库和网络服务仍需各自的提交/回滚协议。

它也无法自动解决锁集合在运行期不断变化的架构问题。若业务操作可能递归调用并获取额外锁，应建立全局锁层级、重构所有权，或把状态汇聚到单线程执行器，而不是在局部不断扩大 `scoped_lock` 参数列表。

## 示例解析和设计原则

示例用一个 `scoped_lock` 原子地维护左右两个值的不变量，再持共享锁读取。实际代码应为数据不变量选择最少数量的锁、记录统一锁顺序、避免返回锁保护数据的裸引用，并通过压力测试和线程消毒器验证，而不是只靠代码看起来有锁。

## 权威资料

- [P0156R2：scoped_lock](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0156r2.html)
- [工作草案：Mutex requirements](https://eel.is/c++draft/thread.mutex.requirements)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
