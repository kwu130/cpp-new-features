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

