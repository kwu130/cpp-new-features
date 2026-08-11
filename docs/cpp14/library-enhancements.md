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

## `exchange` 的语义

`std::exchange(object, new_value)` 概念上先移动保存旧值，再把新值转发赋给对象，最后返回旧值。它把状态替换写成单个清晰表达式，但不是 CPU 原子交换；并发对象需要 `atomic::exchange`。

该工具常用于移动构造：目标取得源句柄，同时把源句柄设为空值；也适合状态机返回前一状态。它要求旧值可移动构造且新值可赋值，异常保证取决于这两个操作。

## 示例解析与工程权衡

示例在独占锁内用 `exchange` 更新状态，再在共享锁内读取。锁建立必要的同步关系，`exchange` 只负责值替换。评估读写锁时应测量实际读写比例、临界区时长和目标平台，并明确超时后业务如何恢复，而不是把定时锁当作自动容错。
