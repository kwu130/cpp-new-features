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

## `atomic_ref` 的用途与约束

`atomic_ref<T>` 为一个已经存在的 T 对象提供原子操作，适合共享内存布局、外部结构或逐步迁移旧数据。所有指向同一对象的并发访问必须兼容地原子化，混用普通读写仍会数据竞争。

底层对象地址必须满足 `required_alignment`，生命周期必须覆盖所有 atomic_ref。对象本身不能是 const，且 T 必须满足规定的可平凡复制等要求。是否无锁可查询，未对齐不能靠实现“凑合”。

## 内存序

等待和加载同样接受内存序。典型发布模式是生产者 release store 新状态并 notify，消费者 acquire wait/load 后读取相关数据。示例使用默认顺序以保持直观；降低到 relaxed 前必须证明没有其他数据需要发布。

## 示例解析与实践

工作线程通过 atomic_ref 写 counter，再发布 state=1；主线程等待 state 改变后原子增加 counter。工程中用版本计数防 ABA，记录对齐与访问协议，避免为大量短暂对象随意创建 atomic_ref，并在目标平台检查锁自由性质与等待延迟。
