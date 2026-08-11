# 原子等待与 `atomic_ref`

原子对象可以直接等待值变化并通知等待者，避免围绕简单状态额外建立条件变量。`atomic_ref` 则为现有对象提供原子访问视图。

<!-- example id="cpp20-atomic" std="c++20" file="main.cpp" kind="single" compilers="all" output="43" -->
```cpp
#include <atomic>
#include <iostream>
#include <thread>

int main() {
    std::atomic<int> state{0};
    int counter = 0;
    std::jthread worker([&] {
        std::atomic_ref<int> reference(counter);
        reference.store(42);
        state.store(1);
        state.notify_one();
    });

    state.wait(0);
    std::atomic_ref<int> reference(counter);
    reference.fetch_add(1);
    worker.join();
    std::cout << reference.load() << '\n';
}
```

`atomic_ref` 的底层对象必须满足对齐要求，且在引用存活期间所有并发访问都应通过原子方式。等待仍应围绕期望值编写，通知本身不保存事件。

## 原子等待的语义

`atomic::wait(old)` 会重复比较当前值与 old；相等时阻塞，值改变后返回。实现可以先自旋，再使用 futex、WaitOnAddress 或平台等价机制休眠，避免条件变量所需的独立互斥量和状态对象。

虚假解除阻塞可以发生在底层，但接口返回前会重新检查值，因此调用者看到的是值已不等于 old。ABA 情况仍可能存在：值从 old 变为其他值又变回 old，等待者可能继续等待；需要观察每次事件时应使用单调序号而非布尔状态。

`notify_one/all` 只唤醒当前等待者，不累积通知。正确性必须建立在原子值上：先修改状态，再通知；后来开始等待的线程会先检查值而不会依赖历史通知。

等待使用按值表示比较，而不是调用 `operator==`。对具有填充位的原子类型，规范对值表示/填充有专门规则；常见整数最直观。`wait` 参数是调用方已观察的旧值，典型循环先 load，再在状态不满足时 wait(old)。

成员版 `atomic<T>::wait/notify_*` 与自由函数版 `atomic_wait/atomic_notify_*` 都可用。通知本身不执行 store，也不附带内存序；它只是提示等待实现重新检查原子值，所以必须先发布新状态。

`notify_one` 至少选择一个阻塞等待者，适合单个工作可由一个消费者处理；`notify_all` 唤醒所有等待者，适合配置版本或关闭状态广播。大量线程同时唤醒会形成惊群，应让状态模型决定，而不是默认全唤醒。

### 等待实现与性能

实现可能先短暂自旋，在值持续不变时进入内核等待。原子类型/地址若不被平台原语直接支持，库可能使用内部等待表。API 避免调用者维护额外 mutex/cv，但不承诺整个阻塞过程 lock-free。

频繁变化且等待很短的状态适合自旋与原子等待结合；长任务仍要考虑取消和超时。C++20 `atomic::wait` 没有超时重载，需要超时语义时使用条件变量、信号量或平台设施。

## `atomic_ref` 的用途与约束

`atomic_ref<T>` 为一个已经存在的 T 对象提供原子操作，适合共享内存布局、外部结构或逐步迁移旧数据。所有指向同一对象的并发访问必须兼容地原子化，混用普通读写仍会数据竞争。

底层对象地址必须满足 `required_alignment`，生命周期必须覆盖所有 atomic_ref。对象本身不能是 const，且 T 必须满足规定的可平凡复制等要求。是否无锁可查询，未对齐不能靠实现“凑合”。

<!-- example id="cpp20-atomic-ref-counter" std="c++20" file="main.cpp" kind="single" compilers="all" output="counter=2000" -->
```cpp
#include <atomic>
#include <iostream>
#include <thread>

int main() {
    alignas(std::atomic_ref<int>::required_alignment) int counter = 0;

    auto increment = [&counter] {
        std::atomic_ref<int> value(counter);
        for (int index = 0; index < 1000; ++index) {
            value.fetch_add(1, std::memory_order_relaxed);
        }
    };

    std::jthread first(increment);
    std::jthread second(increment);
    first.join();
    second.join();

    std::atomic_ref<int> value(counter);
    std::cout << "counter=" << value.load(std::memory_order_relaxed) << '\n';
}
```

底层 `int` 显式满足 required_alignment，两个线程的所有并发访问都经 atomic_ref。这里只需要计数原子性，join 已负责最终可见性，所以 relaxed 足够；若计数值还发布其他数据，就需更强的同步设计。

同一对象上可以存在多个 atomic_ref，它们引用同一原子修改顺序。关键不是“必须共用同一个 atomic_ref 对象”，而是所有重叠生命周期中的访问都遵循原子协议。普通初始化应在并发开始前完成，普通最终读取应在所有原子引用/并发操作结束后并有线程同步。

`is_always_lock_free` 是静态性质，`is_lock_free()` 可查询当前对象/实现。不是 lock-free 仍具有原子语义，只是实现可能使用锁。共享内存跨进程使用还需平台保证，C++ 类型本身不承诺内部锁跨进程工作。

### 对象表示与别名

atomic_ref 不能引用位域，因为位域没有可取得的独立地址。对数组元素、结构成员使用时要确保该对象没有与其他并发访问单元重叠；相邻位打包或联合存储尤其危险。

对象必须是 trivially copyable 类型，但这不代表任意业务操作都能原子完成。atomic_ref 只提供 `atomic<T>` 对该 T 支持的操作；整数有 fetch_add/位操作，普通结构通常只有 load/store/exchange/CAS。

## 内存序

等待和加载同样接受内存序。典型发布模式是生产者 release store 新状态并 notify，消费者 acquire wait/load 后读取相关数据。示例使用默认顺序以保持直观；降低到 relaxed 前必须证明没有其他数据需要发布。

`wait(old, order)` 的 order 约束与加载类似，不能使用 release 或 acq_rel。返回前观察到不同值的加载若以 acquire 执行，可与生产者 release store 同步。notify 不代替这对内存序。

使用 relaxed 等待可以高效观察纯计数/状态，却不发布旁边普通对象。常见错误是生产者先写非原子 payload，再 relaxed store ready 并 notify，消费者看到 ready 后读 payload；这缺少 release/acquire 关系。

版本计数器比布尔状态更能避免 ABA：每次发布递增序号，等待者保存上次已处理版本。固定宽度计数最终会环绕，长期系统仍需评估环绕窗口或使用更宽类型。

## 与条件变量和信号量比较

原子等待适合“等待这个原子值不同于已知旧值”，不直接表达任意多字段谓词、超时或公平队列。条件变量配合锁可以原子地检查复杂谓词并等待；信号量累积许可，更适合每次 release 都代表可消费资源。

通知不累计意味着它不是 semaphore。若状态从 0 变 1、通知、又变回 0 后新线程开始 wait(0)，它看不到历史事件。需要事件计数就把原子值设计成单调序号或使用许可原语。

## 示例解析与实践

工作线程通过 atomic_ref 写 counter，再发布 state=1；主线程等待 state 改变后原子增加 counter。工程中用版本计数防 ABA，记录对齐与访问协议，避免为大量短暂对象随意创建 atomic_ref，并在目标平台检查锁自由性质与等待延迟。

## 权威资料

- [P0019R8：atomic_ref](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0019r8.html)
- [P1135R6：原子等待与通知](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1135r6.html)
- [工作草案：Atomic waiting operations](https://eel.is/c++draft/atomics.wait)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
