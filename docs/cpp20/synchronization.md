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

## 三种原语的状态机

`latch` 保存只能递减的计数。线程可 `count_down`、`wait` 或一次完成两者；计数到零后永久开放，不能重置，适合一次性启动或结束汇合。

`barrier` 按阶段循环使用。每个参与者到达会减少当前阶段计数，最后到达者执行完成函数（若有），随后进入下一阶段并重置期望数。参与者可通过 `arrive_and_drop` 永久退出后续阶段。

`counting_semaphore<N>` 保存许可计数，`acquire` 消耗许可，`release` 增加许可并唤醒等待者。`binary_semaphore` 是最大计数至少为一的特化用途，可表达事件或单许可资源，但不记录“哪个线程拥有许可”。

## 内存同步

这些原语不仅阻塞线程，还建立标准规定的同步关系，使阶段前写入对阶段后线程可见。仍需遵守每个原语的到达、释放和访问顺序，不能用一个 barrier 自动保护阶段内部的并发写。

## 与条件变量的选择

条件变量适合等待任意谓词，并允许重复改变条件；latch/barrier 直接表达已知参与数量的阶段；semaphore 表达资源容量。选择与问题同构的原语能减少手写计数和虚假唤醒处理。

## 死锁与异常

参与者在到达前异常退出，会让 latch/barrier 永远等不到目标计数。线程创建失败、提前返回和取消路径必须显式补偿计数或采用 RAII 到达守卫。完成函数应短小且不抛异常。

## 示例解析与实践

示例用信号量启动工作线程，主/工作线程在 barrier 汇合，再用 latch 通知工作完成。虽然为了教学同时展示三种原语，生产代码应使用最少且语义最贴合的一种。为所有等待设置外部超时监控，并测试参与者减少和提前取消。
