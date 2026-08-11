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

