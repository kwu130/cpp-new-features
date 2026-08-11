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

