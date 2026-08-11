# `shared_timed_mutex` 与 `exchange`

`shared_timed_mutex` 允许多个读者共享锁或单个写者独占锁，并支持定时等待。`exchange` 用新值替换对象并返回旧值，常用于移动操作和状态机。

<!-- example id="cpp14-library-enhancements" std="c++14" file="main.cpp" kind="single" compilers="all" output="old=1, current=2" -->
```cpp
#include <iostream>
#include <mutex>
#include <shared_mutex>
#include <utility>

int main() {
    std::shared_timed_mutex mutex;
    int state = 1;
    int old = 0;
    {
        std::unique_lock<std::shared_timed_mutex> lock(mutex);
        old = std::exchange(state, 2);
    }
    {
        std::shared_lock<std::shared_timed_mutex> lock(mutex);
        std::cout << "old=" << old << ", current=" << state << '\n';
    }
}
```

读写锁只在读操作占绝大多数且临界区值得其额外开销时更有优势。`exchange` 不负责同步，共享状态仍需要锁或适当的原子操作。

## 共享互斥模型

`shared_timed_mutex` 有两种互斥的所有权模式：任意时刻要么一个线程持有独占锁，要么一个或多个线程持有共享锁。写者使用 `unique_lock`，读者使用 `shared_lock`。它还提供 `try_lock_for`、`try_lock_until` 等定时接口。

实现通常维护读者计数、写者状态和等待队列，内部成本高于普通互斥量。标准不保证严格公平，持续读流可能让写者饥饿，具体策略取决于平台实现。读临界区很短时，读者计数的共享缓存行竞争甚至可能比普通互斥量更慢。

共享锁只允许逻辑只读操作。如果所谓“读”会更新缓存、统计或延迟初始化状态，它仍可能需要独占锁或独立原子同步。返回受保护对象的引用后立即释放锁，也会把数据竞争推给调用者。

### 锁接口与 RAII 包装

独占模式提供 `lock()`、`try_lock()`、`try_lock_for()`、`try_lock_until()` 和 `unlock()`；共享模式对应 `lock_shared()`、`try_lock_shared()`、`try_lock_shared_for()`、`try_lock_shared_until()` 和 `unlock_shared()`。实际代码应优先让 `unique_lock` 或 `shared_lock` 管理解锁，避免异常和提前返回破坏配对。

定时接口的失败只表示在给定等待条件内没有获得锁，不说明持锁线程已经发生故障。`try_lock_for` 接受相对时长，可能因为调度或系统时钟粒度等待得比请求更久；`try_lock_until` 接受绝对时间点。超时路径必须由业务显式定义，例如返回旧快照、重试、取消请求或报告繁忙。

标准不提供从共享所有权直接原子升级为独占所有权的操作。先释放共享锁再获取独占锁会留下竞争窗口，期间状态可能改变，因此写入前必须重新检查前置条件。反向“降级”也不应假定能无缝完成。

### 内存同步而非只保护语句块

写线程在独占解锁前对受保护数据的修改，会通过随后成功获取相应互斥量的线程变得可见。锁的作用既是排他，也是建立跨线程的 happens-before 关系。仅仅把字段声明为 `volatile` 不能替代这种同步。

共享模式允许多个读线程并发，但它们仍会共同更新互斥量内部的读者计数。高核心数下，这个计数可能成为缓存一致性热点。所以“读多写少”只是使用读写锁的必要线索，不是性能结论；还要比较临界区工作量与锁管理成本。

## `exchange` 的语义

`std::exchange(object, new_value)` 概念上先移动保存旧值，再把新值转发赋给对象，最后返回旧值。它把状态替换写成单个清晰表达式，但不是 CPU 原子交换；并发对象需要 `atomic::exchange`。

该工具常用于移动构造：目标取得源句柄，同时把源句柄设为空值；也适合状态机返回前一状态。它要求旧值可移动构造且新值可赋值，异常保证取决于这两个操作。

可以把它理解为如下三个有顺序的步骤：先从 `object` 构造旧值临时量，再执行 `object = new_value`，最后返回旧值。第一步成功、第二步抛出时，对象是否改变取决于赋值运算自身的异常保证；`exchange` 不额外提供事务回滚。返回类型是被替换对象的类型，而新值可以是能赋给它的不同类型。

<!-- example id="cpp14-exchange-move-state" std="c++14" file="main.cpp" kind="single" compilers="all" output="moved=7, source=-1" -->
```cpp
#include <iostream>
#include <utility>

class Handle {
public:
    explicit Handle(int value) noexcept : value_(value) {}

    Handle(Handle&& other) noexcept
        : value_(std::exchange(other.value_, invalid_value)) {}

    Handle& operator=(Handle&& other) noexcept {
        if (this != &other) {
            value_ = std::exchange(other.value_, invalid_value);
        }
        return *this;
    }

    int value() const noexcept { return value_; }

private:
    static constexpr int invalid_value = -1;
    int value_;
};

constexpr int Handle::invalid_value;

int main() {
    Handle source(7);
    Handle moved(std::move(source));
    std::cout << "moved=" << moved.value()
              << ", source=" << source.value() << '\n';
}
```

移动构造函数取得旧句柄并同时把源对象设成明确的无效状态。这个例子没有真实资源释放逻辑；生产级句柄类的移动赋值还必须先正确释放目标原有资源。若只是覆盖 `value_`，会泄漏目标此前拥有的操作系统句柄。

### `std::exchange` 与原子交换的区别

`std::exchange` 是普通泛型函数，适用于任意满足构造和赋值要求的对象，不提供线程安全。`atomic<T>::exchange` 是原子读-改-写操作，可指定内存序，并参与原子对象的修改顺序。两者名字相似，但解决的问题分别是“简洁表达状态替换”和“并发同步”。

## 何时选择哪一种互斥量

若所有访问都需要写入，或临界区非常短，`mutex` 往往更简单且更快。只有读操作可真正并行、写入相对稀少、读取工作量足以摊薄内部计数成本时，才值得基准测试 `shared_timed_mutex`。若完全不需要超时，而工具链支持后续标准，可考虑 C++17 的 `shared_mutex`，它不承诺定时接口，允许实现针对这一较小接口优化。

无论选择哪种锁，都应把受保护数据和互斥量封装在同一抽象内。调用者不应拿到脱离锁生命周期的引用、指针或迭代器。需要长时间消费数据时，常见策略是在锁内复制快照，随后在锁外处理。

## 示例解析与工程权衡

示例在独占锁内用 `exchange` 更新状态，再在共享锁内读取。锁建立必要的同步关系，`exchange` 只负责值替换。评估读写锁时应测量实际读写比例、临界区时长和目标平台，并明确超时后业务如何恢复，而不是把定时锁当作自动容错。

## 权威资料

- [N3659：共享互斥量](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3659.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
