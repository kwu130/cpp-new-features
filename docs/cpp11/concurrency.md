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

## 线程生命周期

`std::thread` 构造后可能立即执行。参数默认被复制或移动进内部存储，传引用要使用 `std::ref`，并保证对象活到线程结束。可连接线程析构会调用 `std::terminate`，因此所有控制路径都要 `join` 或 `detach`。`detach` 使生命周期难以管理，通常不是解决阻塞的正确办法。

## 互斥量与 RAII

互斥量保护的是不变量而非某个变量。所有访问同一不变量的路径必须使用同一同步协议。`lock_guard` 在构造时加锁、析构时解锁，能跨异常安全释放；`unique_lock` 支持延迟锁、转移所有权并配合条件变量，代价是状态更多。

同时获取多个锁应使用 `std::lock` 等避免死锁算法，并建立全局锁顺序。持锁时调用未知回调、等待线程或执行 I/O 会扩大死锁和延迟风险。

## 条件变量、Future 与任务

条件变量只提供通知，不保存业务条件。等待线程必须在锁保护下循环检查谓词，因为通知可能早到、重复或出现虚假唤醒。

Promise/Future 把一次性结果或异常从生产者传给消费者。`future.get()` 只能成功取一次，并会重新抛出任务异常。`async` 的默认启动策略可能选择延迟执行；需要并发时应像示例一样显式指定 `launch::async`。

## 原子操作与内存序

默认 `seq_cst` 提供最强、最直观的全局顺序。更弱的 acquire/release 或 relaxed 能减少约束，但证明难度显著增加。`relaxed` 只保证该原子对象操作不撕裂及修改顺序，不发布其他普通数据。

原子复合操作如 `fetch_add` 是不可分割的读改写；分别 `load`、加一、`store` 不是等价操作。原子类型是否无锁可通过接口查询，不应假设所有平台都由单条指令实现。

## 示例解析与检查清单

工作线程在互斥区写入共享值，通过 Promise 发布结果并增加原子计数；主线程 `get` 后连接线程，再启动明确的异步任务。工程检查时应画出共享状态、所有访问路径和 happens-before 边，验证线程在异常路径也会连接，并用线程消毒器补充测试。

## 权威资料

- [线程支持库](https://eel.is/c++draft/thread)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
