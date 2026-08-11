# `latch`、`barrier` 与 `semaphore`

`latch` 是一次性倒计数门闩，`barrier` 支持重复阶段同步，`semaphore` 管理有限数量的许可。

<!-- example id="cpp20-synchronization" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <barrier>
#include <iostream>
#include <latch>
#include <semaphore>
#include <thread>

int main() {
    std::binary_semaphore start(0);
    std::barrier phase(2);
    std::latch finished(1);
    int result = 0;

    std::jthread worker([&] {
        start.acquire();
        result = 42;
        phase.arrive_and_wait();
        finished.count_down();
    });

    start.release();
    phase.arrive_and_wait();
    finished.wait();
    worker.join();
    std::cout << result << '\n';
}
```

必须保证 barrier 的参与者数量与实际到达一致，否则程序会永久等待。信号量保护的是许可数量，不自动保护许可对应对象的其他共享状态。

