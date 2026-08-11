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

