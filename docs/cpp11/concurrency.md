# 并发编程

阅读前建议先了解：[Lambda](lambdas.md)、[所有权与 RAII](../prerequisites.md#所有权与-raii)；先学线程与锁，再进入内存序。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 从两个问题开始：谁执行，谁等待

把计算交给另一个线程后，主线程仍会继续往下执行。因此先解决两个问题：如何等工作完成，如何避免两个线程同时改坏同一份数据。C++11 用 thread 管理线程，用 mutex 保护共享数据；暂时不需要记忆内存序名称。

C++03 的标准库没有统一线程接口，通常使用操作系统 API。C++11 把线程、锁和任务结果纳入标准库，但不自动让共享对象变得安全。

## 第一步：启动一个线程，等它结束后读结果

```cpp example id="cpp11-thread-join-basic" std="c++11" file="main.cpp" kind="single" compilers="all" output="result=42"
#include <iostream>
#include <thread>
int main() {
    int result = 0;
    std::thread worker([&result] { result = 42; });
    worker.join();
    std::cout << "result=" << result << '\n';
}
```

按执行关系读这段程序：启动 worker → worker 写 result → join 等 worker 完成 → 主线程读 result。Lambda 里的 &result 表示访问同一变量。主线程在 join 前不读它，因此没有并发读写冲突；若把输出移到 join 前，就没有这个保证。

join 等待完成，不是“开始运行”的按钮。线程从创建成功后就可能开始执行。仍可 join 的 thread 对象析构会终止程序，所以实际业务要照顾异常和提前返回；C++20 的 [jthread](../cpp20/jthread.md)把回收线程放进析构。

## 第二步：两个线程都修改计数时，用同一把锁

只在最后 join，不能保护工作期间的并发 ++counter。一次自增包含读取和写回。没有同步的并发修改会产生数据竞争，属于未定义行为，并非只是可能少加几次；下面用同一把互斥量保护所有修改。

```cpp example id="cpp11-mutex-counter-basic" std="c++11" file="main.cpp" kind="single" compilers="all" output="count=2000"
#include <iostream>
#include <mutex>
#include <thread>
int main() {
    int counter = 0;
    std::mutex mutex;
    auto increment = [&] {
        for (int index = 0; index < 1000; ++index) {
            std::lock_guard<std::mutex> lock(mutex);
            ++counter;
        }
    };
    std::thread worker(increment);
    increment();
    worker.join();
    std::cout << "count=" << counter << '\n';
}
```

lock_guard 构造时加锁，本轮作用域结束时解锁；两个执行者都使用同一 mutex，所以受保护的自增不会同时进行。最后主线程等待 worker 后读取最终值。把 mutex 放到每个线程各自的局部变量里，得到的是不同锁，起不到这里的保护作用。

这个例子为了看清锁的作用而逐次加锁。真实批量统计可以让线程先各自累加，再汇总，减少竞争。多项状态需要一起保持正确时用锁很直接；本篇后半部分再讨论单个原子变量。

## 第三步：只想取得计算结果时，用 Future

Future 可以理解为“稍后领取一次结果的对象”。不必先学 Promise 就能用 async 启动计算，并通过 get() 领取结果或接收异常。

```cpp example id="cpp11-future-result-basic" std="c++11" file="main.cpp" kind="single" compilers="all" output="answer=42"
#include <future>
#include <iostream>
int main() {
    auto answer = std::async(std::launch::async, [] { return 6 * 7; });
    std::cout << "answer=" << answer.get() << '\n';
}
```

launch::async 在这里明确要求异步执行；get() 等待结果可用，并取走结果，普通 future 不应再次 get()。需要自己决定何时写入结果时，再配合 Promise 使用。Future 传结果，mutex 保护访问，它们解决的问题不同。

第一次阅读掌握这三个程序即可。下面保留组合练习；内存模型、条件变量与内存序属于继续深入的部分。

## 组合练习：结果传递与状态记录

下面的练习把锁、Promise/Future、原子计数和 async 放在一起辨认。这个小任务实际只需前面的 async 即可完成；completed 与锁不是发布这一个结果所必需的，不应把四种工具当成固定搭配。

```cpp example id="cpp11-concurrency" std="c++11" file="main.cpp" kind="single" compilers="all" output="total=42, doubled=42"
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

程序输出 `total=42, doubled=42`。每个可连接线程都必须 `join` 或 `detach`，通常应通过 RAII 包装；优先使用 `lock_guard` 管理互斥量；条件变量等待必须反复检查谓词；原子操作只解决特定内存位置的同步，不自动保护整个业务不变量。

## C++ 内存模型基础

两个线程对同一内存位置有冲突访问（至少一个修改），其中至少一个访问非原子且没有建立先后同步关系，就会形成数据竞争；数据竞争导致未定义行为，而不只是“偶尔读到旧值”。编译器可假设数据竞争不存在，并据此重排或消除访问，所以仅凭 CPU 上看似原子的读写不能保证正确。

同步操作建立 happens-before 关系。解锁同一互斥量 happens-before 随后的成功加锁；线程完成 happens-before `join` 返回；原子的释放写与读取该值的获取读可以发布此前写入的数据。

内存位置大致对应标量对象或相邻位域规则下的存储单元。两个线程修改同一结构的不同普通成员可能安全，修改相邻位域可能共享内存位置；容器还有自己的线程安全条款。

sequenced-before 描述单线程求值顺序，synchronizes-with 连接特定跨线程操作，二者传递形成 happens-before。正确性证明应标出具体写、发布、获取和读，不只说“这里用了 atomic”。

数据竞争与逻辑竞态不同：全用 mutex 可消除数据竞争，仍可能因检查后操作分离产生余额透支等竞态。锁范围应覆盖完整不变量事务。

### 可见性与顺序

缓存一致性不能替代语言模型。volatile 主要用于某些硬件/信号语义，不建立线程同步；用 volatile bool 作为停止标志仍是数据竞争。

编译器和 CPU 可在不改变单线程可观察行为前提下重排。mutex/atomic 内存序给优化器与硬件建立边界，手写空循环或打印日志不是可靠屏障。

## 线程生命周期

`std::thread` 构造后可能立即执行。参数默认被复制或移动进内部存储，传引用要使用 `std::ref`，并保证对象活到线程结束。可连接线程析构会调用 `std::terminate`，因此所有控制路径都要 `join` 或 `detach`。`detach` 使生命周期难以管理，通常不是解决阻塞的正确办法。

`joinable()` 不等于线程仍在运行：已经执行完成但尚未 join 的 thread 仍可连接。默认构造、移动来源、join/detach 后对象不可连接。对不可连接对象调用 join/detach 会抛 `system_error`。

线程函数异常若逃出顶层会调用 terminate，不会自动传给创建者。在线程体捕获并通过 promise/`exception_ptr` 报告，或使用 async/future。主线程 join 只等待，不重抛 std::thread 的异常。

thread::id 可比较/哈希，`this_thread::get_id/yield/sleep_for/sleep_until` 提供当前线程操作。sleep 至少等待相应时长附近但受调度影响，不是实时截止保证。

### RAII join

C++11 没有 jthread，项目常写 `thread_guard`/`scoped_thread` 在析构 join。守卫必须在线程引用的其他局部对象之前析构，成员声明顺序也要确保先 join 再销毁共享状态。

析构 join 可能无限阻塞，RAII 解决漏 join 不解决取消。任务要有停止协议/超时 I/O；C++20 jthread 才标准化协作停止入口。

## 互斥量与 RAII

互斥量保护的是不变量而非某个变量。所有访问同一不变量的路径必须使用同一同步协议。`lock_guard` 在构造时加锁、析构时解锁，能跨异常安全释放；`unique_lock` 支持延迟锁、转移所有权并配合条件变量，代价是状态更多。

同时获取多个锁应使用 `std::lock` 等避免死锁算法，并建立全局锁顺序。持锁时调用未知回调、等待线程或执行 I/O 会扩大死锁和延迟风险。

C++11 互斥类型包括 mutex、`recursive_mutex`、`timed_mutex`、`recursive_timed_mutex`。recursive 允许同线程重复获取，但常掩盖设计递归和过大临界区；普通 mutex 更容易推理。

`unique_lock` 提供 `defer_lock`、`try_to_lock`、`adopt_lock` 构造、lock/`try_lock`/unlock、`owns_lock`、release 和移动。release 不解锁，只转移原始 mutex 责任；误用会永久锁住。

`std::lock(m1,m2,...)` 用死锁避免算法取得全部锁，随后常用 `lock_guard(m, adopt_lock)` 分别建立 RAII。若在调用前已持其中锁而协议不匹配，仍可能死锁。

`try_lock` 多锁版本返回失败索引并在失败时解开之前获得的锁。重试策略可能饥饿，公平性不由普通 mutex 保证。

### 锁粒度

一个大锁易正确但串行化，细锁提高并发却引入锁顺序和跨锁不变量。先用简单模型保证正确，再基于测量拆分；不要为理论并发把一个事务分成多个不一致临界区。

锁保护数据应封装在同一类，成员函数不返回脱离锁生命周期的引用。复制快照或接收在锁内执行的短回调，比让调用方手动记 mutex 更可靠。

## 条件变量、Future 与任务

条件变量只提供通知，不保存业务条件。等待线程必须在锁保护下循环检查谓词，因为通知可能早到、重复或出现虚假唤醒。

Promise/Future 把一次性结果或异常从生产者传给消费者。`future.get()` 只能成功取一次，并会重新抛出任务异常。`async` 的默认启动策略可能选择延迟执行；需要并发时应像示例一样显式指定 `launch::async`。

`condition_variable` 只与 `unique_lock<mutex>` 配合，`condition_variable_any` 可与满足 BasicLockable 的锁配合但可能成本更高。wait 会原子地释放锁并阻塞，唤醒后重新获取锁再返回。

通知可在持锁时或解锁后调用；先在锁内修改谓词是关键。解锁后 notify 常减少被唤醒线程立即再次阻塞，但具体性能要测。`notify_one` 不保证选择哪个等待者，`notify_all` 可能惊群。

`wait_for/wait_until` 超时也要重新检查谓词；相对超时放在虚假唤醒循环中若每次重置完整 duration，可能总等待超长，谓词重载或固定绝对截止更可靠。

### shared state

promise、`packaged_task`、async 生产共享状态，future 消费。promise 析构前未设置结果会让 future 得到 `broken_promise` 异常；重复 `set_value`/`set_exception` 或重复 `get_future` 会报 `future_error`。

`shared_future` 可复制并允许多个消费者调用 get；若结果类型是引用/const 引用，仍要管理底层共享状态寿命。future::share 转移状态后原 future 无效。

`packaged_task` 把可调用对象与共享状态绑定，执行 task 时保存返回值/异常，可 move 进队列；它不自行创建线程。reset 可为下一次调用建立新状态，但旧 future 仍对应旧状态。

`async(launch::deferred, f)` 到 wait/get 的线程同步执行，若从未等待可能从未运行。默认 `async|deferred` 由实现选择，涉及并发假设时显式策略。

## 原子操作与内存序

默认 `seq_cst` 提供最强、最直观的全局顺序。更弱的 acquire/release 或 relaxed 能减少约束，但证明难度显著增加。`relaxed` 只保证该原子对象操作不撕裂及修改顺序，不发布其他普通数据。

原子复合操作如 `fetch_add` 是不可分割的读改写；分别 `load`、加一、`store` 不是等价操作。原子类型是否无锁可通过接口查询，不应假设所有平台都由单条指令实现。

原子类型提供 load/store/exchange/`compare_exchange`，整数/指针还有 `fetch_add`/sub 等。CAS 会把 expected 作为输入旧值；失败时把实际值写回 expected，因此常在循环中复用它。

`compare_exchange_weak` 允许虚假失败，适合循环且某些架构更高效；strong 不虚假失败，仍可能因值竞争失败。循环体必须在失败后基于更新的 expected 重新计算目标。

### 六种内存序

relaxed 仅保证原子性/修改顺序；release 发布此前操作，acquire 获取发布；`acq_rel` 用于读改写两侧；`seq_cst` 再加入单一全局顺序。consume 在实践中长期实现为 acquire，复杂依赖语义不宜作为入门优化。

store 不能使用 acquire/`acq_rel`，load 不能使用 release/`acq_rel`；CAS 成功/失败可分别指定，失败序不能包含 release 且不能强于成功序。用默认 `seq_cst` 正确后再由证明确认降低。

release/acquire 必须通过同一原子上的值读取关系连接，两个“各自用了 release/acquire”的不同原子不自动同步。release sequence 和 CAS 链有精细规则，应用标准模式而非凭直觉拼装。

### lock-free 不等于 wait-free

`is_lock_free()` 表示实现是否不用阻塞锁完成该原子类型操作，不保证某线程有限步完成，也不保证算法整体无锁。`ATOMIC_*_LOCK_FREE` 宏给出类型类别能力级别。

无锁算法还要解决 ABA、内存回收和对象生命周期。指针 CAS 成功不代表被指对象仍存活，hazard pointer/epoch 等回收策略超出单个 atomic 能力。优先 mutex，除非已证明瓶颈且有完整算法审计。

## 示例解析与检查清单

工作线程在互斥区写入共享值，通过 Promise 发布结果并增加原子计数；主线程 `get` 后连接线程，再启动明确的异步任务。工程检查时应画出共享状态、所有访问路径和 happens-before 边，验证线程在异常路径也会连接，并用线程消毒器补充测试。

## 条件变量的完整等待协议

共享谓词必须由同一互斥量保护。生产者持锁修改状态，解锁后或解锁前通知；消费者通过带谓词的 `wait` 重复检查条件。通知可以合并或早于等待发生，真正不会丢失的是受锁保护的状态。

```cpp example id="cpp11-condition-variable-queue" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42"
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

```cpp example id="cpp11-release-acquire" std="c++11" file="main.cpp" kind="single" compilers="all" output="published=42"
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

## 并发接口速查

| 设施 | 关键契约 |
| --- | --- |
| `thread` | joinable 对象析构会 terminate，必须 join/detach |
| `mutex` | 非递归独占锁，使用 RAII 守卫管理 |
| `lock_guard` | 简单词法持锁，不支持提前解锁 |
| `unique_lock` | 可延迟、移动、解锁，供 `condition_variable` 使用 |
| `condition_variable` | 通知不保存业务状态，必须配谓词循环 |
| `promise<T>` | 单次写入共享状态，重复满足会报错 |
| `future<T>` | 移动专用结果句柄，get 通常只能调用一次 |
| `shared_future<T>` | 可复制并由多观察者读取同一完成状态 |
| `async` | launch policy 决定异步线程或延迟执行 |
| `packaged_task` | 把可调用结果连接到 future 共享状态 |
| `atomic<T>` | 对该对象操作无数据竞争，内存序决定跨对象发布 |
| `call_once` | 成功完成一次初始化；抛异常时可由后续调用重试 |

## C++11 并发故障定位线索

- 偶发永久等待：记录每把锁持有/请求顺序并构造等待图。
- 条件变量偶发漏事件：检查状态是否在同一锁下更新并由谓词读取。
- 程序退出 terminate：查找仍 joinable 的 thread 析构路径。
- future 永久阻塞：检查对应 promise 是否在所有异常/退出路径满足。
- async 没有并发：确认是否被选择 deferred policy 及何时调用 get。
- 结果偶发陈旧：画出 release/acquire 或 mutex 的 happens-before 链。
- 原子计数正确但 payload 错乱：relaxed 只保护计数，不自动发布旁边数据。
- `call_once` 重复进入：初始化函数抛异常时状态不会标记成功。
- 压测吞吐下降：检查锁粒度、伪共享、日志 I/O 与线程过量。
- 难以复现竞态：在支持环境运行线程消毒器并保留最小压力测试。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/concurrency.md
```

## 权威资料

- [线程支持库](https://eel.is/c++draft/thread)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
