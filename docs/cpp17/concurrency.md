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

## `shared_mutex` 与 C++14 版本

C++17 `shared_mutex` 提供共享和独占模式但不要求定时接口，相比 C++14 `shared_timed_mutex` 可以让不需要超时的实现更直接。读者用 `shared_lock`，写者用 `unique_lock`。

标准仍不规定公平性。读者持续到来时写者是否饥饿由实现策略决定。读锁内部通常需要更新共享状态，极端读并发会竞争同一缓存行。

## 内存可见性

释放独占锁 happens-before 随后成功获取同一互斥量的共享或独占锁，因此受保护写入对读者可见。仅把字段声明为 `const` 或只在业务上“读取”不会创建同步关系。

## 示例解析和设计原则

示例用一个 `scoped_lock` 原子地维护左右两个值的不变量，再持共享锁读取。实际代码应为数据不变量选择最少数量的锁、记录统一锁顺序、避免返回锁保护数据的裸引用，并通过压力测试和线程消毒器验证，而不是只靠代码看起来有锁。

## 权威资料

- [P0156R2：scoped_lock](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0156r2.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
