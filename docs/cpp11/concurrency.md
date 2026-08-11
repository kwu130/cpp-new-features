# 并发编程

C++11 首次提供跨平台线程、同步原语、任务结果和原子操作，使并发代码不再依赖平台 API。

<!-- example id="cpp11-concurrency" std="c++11" file="main.cpp" kind="single" compilers="all" output="total=42, doubled=42" -->
```cpp
#include <atomic>
#include <future>
#include <iostream>
#include <mutex>
#include <thread>

int main() {
    int shared = 0;
    std::mutex mutex;
    std::atomic<int> completed(0);

    std::promise<int> promise;
    std::future<int> future = promise.get_future();
    std::thread worker([&] {
        {
            std::lock_guard<std::mutex> lock(mutex);
            shared = 21;
        }
        completed.fetch_add(1);
        promise.set_value(shared);
    });

    const int value = future.get();
    worker.join();
    std::future<int> doubled = std::async(std::launch::async, [value] { return value * 2; });

    if (completed.load() != 1) {
        return 1;
    }
    std::cout << "total=" << value * 2 << ", doubled=" << doubled.get() << '\n';
}
```

每个可连接线程都必须 `join` 或 `detach`，通常应通过 RAII 包装。优先使用 `lock_guard` 管理互斥量。条件变量的等待必须带谓词以应对虚假唤醒。原子操作只解决特定共享状态的数据竞争，不自动保证整个业务不变量。

## C++ 内存模型基础

两个线程并发访问同一内存位置，至少一个是写操作且没有同步，就会形成数据竞争；数据竞争导致未定义行为，而不只是“偶尔读到旧值”。编译器可假设数据竞争不存在，并据此重排或消除访问，所以仅凭 CPU 上看似原子的读写不能保证正确。

同步操作建立 happens-before 关系。解锁同一互斥量 happens-before 随后的成功加锁；线程完成 happens-before `join` 返回；原子的释放写与读取该值的获取读可以发布此前写入的数据。

内存位置大致对应标量对象或相邻位域规则下的存储单元。两个线程修改同一结构的不同普通成员可能安全，修改相邻位域可能共享内存位置；容器还有自己的线程安全条款。

sequenced-before 描述单线程求值顺序，synchronizes-with 连接特定跨线程操作，二者传递形成 happens-before。正确性证明应标出具体写、发布、获取和读，不只说“这里用了 atomic”。

数据竞争与逻辑竞态不同：全用 mutex 可消除数据竞争，仍可能因检查后操作分离产生余额透支等竞态。锁范围应覆盖完整不变量事务。

### 可见性与顺序

缓存一致性不能替代语言模型。volatile 主要用于某些硬件/信号语义，不建立线程同步；用 volatile bool 作为停止标志仍是数据竞争。

编译器和 CPU 可在不改变单线程可观察行为前提下重排。mutex/atomic 内存序给优化器与硬件建立边界，手写空循环或打印日志不是可靠屏障。

## 线程生命周期

`std::thread` 构造后可能立即执行。参数默认被复制或移动进内部存储，传引用要使用 `std::ref`，并保证对象活到线程结束。可连接线程析构会调用 `std::terminate`，因此所有控制路径都要 `join` 或 `detach`。`detach` 使生命周期难以管理，通常不是解决阻塞的正确办法。

`joinable()` 不等于线程仍在运行：已经执行完成但尚未 join 的 thread 仍可连接。默认构造、移动来源、join/detach 后对象不可连接。对不可连接对象调用 join/detach 会抛 system_error。

线程函数异常若逃出顶层会调用 terminate，不会自动传给创建者。在线程体捕获并通过 promise/exception_ptr 报告，或使用 async/future。主线程 join 只等待，不重抛 std::thread 的异常。

thread::id 可比较/哈希，`this_thread::get_id/yield/sleep_for/sleep_until` 提供当前线程操作。sleep 至少等待相应时长附近但受调度影响，不是实时截止保证。

### RAII join

C++11 没有 jthread，项目常写 thread_guard/scoped_thread 在析构 join。守卫必须在线程引用的其他局部对象之前析构，成员声明顺序也要确保先 join 再销毁共享状态。

析构 join 可能无限阻塞，RAII 解决漏 join 不解决取消。任务要有停止协议/超时 I/O；C++20 jthread 才标准化协作停止入口。

## 互斥量与 RAII

互斥量保护的是不变量而非某个变量。所有访问同一不变量的路径必须使用同一同步协议。`lock_guard` 在构造时加锁、析构时解锁，能跨异常安全释放；`unique_lock` 支持延迟锁、转移所有权并配合条件变量，代价是状态更多。

同时获取多个锁应使用 `std::lock` 等避免死锁算法，并建立全局锁顺序。持锁时调用未知回调、等待线程或执行 I/O 会扩大死锁和延迟风险。

C++11 互斥类型包括 mutex、recursive_mutex、timed_mutex、recursive_timed_mutex。recursive 允许同线程重复获取，但常掩盖设计递归和过大临界区；普通 mutex 更容易推理。

unique_lock 提供 defer_lock、try_to_lock、adopt_lock 构造、lock/try_lock/unlock、owns_lock、release 和移动。release 不解锁，只转移原始 mutex 责任；误用会永久锁住。

`std::lock(m1,m2,...)` 用死锁避免算法取得全部锁，随后常用 `lock_guard(m, adopt_lock)` 分别建立 RAII。若在调用前已持其中锁而协议不匹配，仍可能死锁。

`try_lock` 多锁版本返回失败索引并在失败时解开之前获得的锁。重试策略可能饥饿，公平性不由普通 mutex 保证。

### 锁粒度

一个大锁易正确但串行化，细锁提高并发却引入锁顺序和跨锁不变量。先用简单模型保证正确，再基于测量拆分；不要为理论并发把一个事务分成多个不一致临界区。

锁保护数据应封装在同一类，成员函数不返回脱离锁生命周期的引用。复制快照或接收在锁内执行的短回调，比让调用方手动记 mutex 更可靠。

## 条件变量、Future 与任务

条件变量只提供通知，不保存业务条件。等待线程必须在锁保护下循环检查谓词，因为通知可能早到、重复或出现虚假唤醒。

Promise/Future 把一次性结果或异常从生产者传给消费者。`future.get()` 只能成功取一次，并会重新抛出任务异常。`async` 的默认启动策略可能选择延迟执行；需要并发时应像示例一样显式指定 `launch::async`。

condition_variable 只与 `unique_lock<mutex>` 配合，condition_variable_any 可与满足 BasicLockable 的锁配合但可能成本更高。wait 会原子地释放锁并阻塞，唤醒后重新获取锁再返回。

通知可在持锁时或解锁后调用；先在锁内修改谓词是关键。解锁后 notify 常减少被唤醒线程立即再次阻塞，但具体性能要测。notify_one 不保证选择哪个等待者，notify_all 可能惊群。

`wait_for/wait_until` 超时也要重新检查谓词；相对超时放在虚假唤醒循环中若每次重置完整 duration，可能总等待超长，谓词重载或固定绝对截止更可靠。

### shared state

promise、packaged_task、async 生产共享状态，future 消费。promise 析构前未设置结果会让 future 得到 broken_promise 异常；重复 set_value/set_exception 或重复 get_future 会报 future_error。

shared_future 可复制并允许多个消费者调用 get；若结果类型是引用/const 引用，仍要管理底层共享状态寿命。future::share 转移状态后原 future 无效。

packaged_task 把可调用对象与共享状态绑定，执行 task 时保存返回值/异常，可 move 进队列；它不自行创建线程。reset 可为下一次调用建立新状态，但旧 future 仍对应旧状态。

`async(launch::deferred, f)` 到 wait/get 的线程同步执行，若从未等待可能从未运行。默认 `async|deferred` 由实现选择，涉及并发假设时显式策略。

## 原子操作与内存序

默认 `seq_cst` 提供最强、最直观的全局顺序。更弱的 acquire/release 或 relaxed 能减少约束，但证明难度显著增加。`relaxed` 只保证该原子对象操作不撕裂及修改顺序，不发布其他普通数据。

原子复合操作如 `fetch_add` 是不可分割的读改写；分别 `load`、加一、`store` 不是等价操作。原子类型是否无锁可通过接口查询，不应假设所有平台都由单条指令实现。

原子类型提供 load/store/exchange/compare_exchange，整数/指针还有 fetch_add/sub 等。CAS 会把 expected 作为输入旧值；失败时把实际值写回 expected，因此常在循环中复用它。

`compare_exchange_weak` 允许虚假失败，适合循环且某些架构更高效；strong 不虚假失败，仍可能因值竞争失败。循环体必须在失败后基于更新的 expected 重新计算目标。

### 六种内存序

relaxed 仅保证原子性/修改顺序；release 发布此前操作，acquire 获取发布；acq_rel 用于读改写两侧；seq_cst 再加入单一全局顺序。consume 在实践中长期实现为 acquire，复杂依赖语义不宜作为入门优化。

store 不能使用 acquire/acq_rel，load 不能使用 release/acq_rel；CAS 成功/失败可分别指定，失败序不能包含 release 且不能强于成功序。用默认 seq_cst 正确后再由证明确认降低。

release/acquire 必须通过同一原子上的值读取关系连接，两个“各自用了 release/acquire”的不同原子不自动同步。release sequence 和 CAS 链有精细规则，应用标准模式而非凭直觉拼装。

### lock-free 不等于 wait-free

`is_lock_free()` 表示实现是否不用阻塞锁完成该原子类型操作，不保证某线程有限步完成，也不保证算法整体无锁。`ATOMIC_*_LOCK_FREE` 宏给出类型类别能力级别。

无锁算法还要解决 ABA、内存回收和对象生命周期。指针 CAS 成功不代表被指对象仍存活，hazard pointer/epoch 等回收策略超出单个 atomic 能力。优先 mutex，除非已证明瓶颈且有完整算法审计。

## 示例解析与检查清单

工作线程在互斥区写入共享值，通过 Promise 发布结果并增加原子计数；主线程 `get` 后连接线程，再启动明确的异步任务。工程检查时应画出共享状态、所有访问路径和 happens-before 边，验证线程在异常路径也会连接，并用线程消毒器补充测试。

## 条件变量的完整等待协议

共享谓词必须由同一互斥量保护。生产者持锁修改状态，解锁后或解锁前通知；消费者通过带谓词的 `wait` 重复检查条件。通知可以合并或早于等待发生，真正不会丢失的是受锁保护的状态。

<!-- example id="cpp11-condition-variable-queue" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42" -->
```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

int main() {
    std::mutex mutex;
    std::condition_variable ready;
    bool available = false;
    int value = 0;

    std::thread producer([&] {
        {
            std::lock_guard<std::mutex> lock(mutex);
            value = 42;
            available = true;
        }
        ready.notify_one();
    });

    {
        std::unique_lock<std::mutex> lock(mutex);
        ready.wait(lock, [&] { return available; });
        std::cout << "value=" << value << '\n';
    }
    producer.join();
}
```

## release/acquire 发布普通数据

原子状态可以发布此前对普通内存的写入。生产者先写数据，再以 release 存储状态；消费者以 acquire 读取到该状态后，可以看见之前的数据。这要求 acquire 确实读取 release 序列中的值。

<!-- example id="cpp11-release-acquire" std="c++11" file="main.cpp" kind="single" compilers="all" output="published=42" -->
```cpp
#include <atomic>
#include <iostream>
#include <thread>

int main() {
    int data = 0;
    std::atomic<bool> ready(false);
    std::thread producer([&] {
        data = 42;
        ready.store(true, std::memory_order_release);
    });
    std::thread consumer([&] {
        while (!ready.load(std::memory_order_acquire)) {
        }
        std::cout << "published=" << data << '\n';
    });
    producer.join();
    consumer.join();
}
```

忙等会持续占用 CPU，示例只用于展示内存序；真实等待应考虑条件变量、平台等待原语或 C++20 原子 wait。若把状态操作都改成 relaxed，对普通 `data` 的可见性就没有这条同步保证。

循环应考虑 `this_thread::yield`/退避降低争用，但仍不提供睡眠通知和超时。C++11 便携阻塞方案是条件变量，不能用 sleep 固定轮询间隔假装精确同步。

发布对象后生产者不得无同步继续修改 data；acquire 只让此前写可见，不把 data 永久变成线程安全。若后续多次更新，需要版本协议、锁或让所有访问原子化。

## 并发测试与工具

单次运行通过不能证明无竞态，调度组合巨大。使用 ThreadSanitizer 等动态工具、压力循环、随机调度和针对 happens-before 的代码审查；工具未报错也不是形式证明。

测试设置超时防死锁，输出顺序不确定时在程序内部验证集合/计数并只检查退出码。仓库并发示例尽量通过 join 和同步建立确定输出。

避免用加入日志“修复”竞态，I/O 内部锁会改变时序掩盖问题。最小复现应保留同步结构，并在优化构建与多核心环境运行。

## 权威资料

- [线程支持库](https://eel.is/c++draft/thread)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
