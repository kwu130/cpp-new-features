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

### `latch` 接口

构造参数是初始计数，必须在实现支持范围内。`count_down(n)` 原子减少计数但不等待；`wait()` 阻塞直到零；`try_wait()` 只观察是否已开放；`arrive_and_wait(n)` 先减少再等待。

计数不得减到零以下。没有方法增加或重置 latch，所有参与者和异常路径必须在创建时规划完成。计数为零的 latch 从一开始就开放，后续 wait 立即返回。

### `barrier` 阶段

barrier 构造时给出预计参与数和可选 completion function。每次 `arrive` 返回 arrival_token，线程可稍后用 `wait(token)` 等待该阶段完成；`arrive_and_wait` 合并两步；`arrive_and_drop` 到达当前阶段并永久减少未来阶段预计数。

最后一个到达使阶段完成，并在规定上下文执行 completion，然后解除等待者并开始下一阶段。completion 必须满足不抛要求，其副作用可作为阶段间状态转换。不要假定固定某个工作线程执行它。

<!-- example id="cpp20-barrier-phases" std="c++20" file="main.cpp" kind="single" compilers="all" output="phases=3" -->
```cpp
#include <barrier>
#include <iostream>
#include <thread>

int main() {
    int completed_phases = 0;
    std::barrier phase(2, [&completed_phases]() noexcept {
        ++completed_phases;
    });

    auto participant = [&phase] {
        for (int iteration = 0; iteration < 3; ++iteration) {
            phase.arrive_and_wait();
        }
    };

    std::jthread first(participant);
    std::jthread second(participant);
    first.join();
    second.join();
    std::cout << "phases=" << completed_phases << '\n';
}
```

每阶段两个参与者各到达一次，completion 恰好执行一次，然后 barrier 自动重置进入下一阶段。主线程在 join 后读取计数，线程完成同步保证结果可见；程序不依赖哪一个参与者执行 completion。

### 信号量许可

模板参数是所需最大值下界，实现的 `max()` 可能更大。初始计数必须在合法范围，`release(update)` 不能让计数超过最大值。`try_acquire` 不阻塞，`try_acquire_for/until` 提供定时尝试，但超时精度受调度和时钟影响。

许可没有线程亲和性：一个线程 acquire，另一个线程可以 release，这正适合生产者/消费者和资源池。它不是递归锁，也不自动把具体资源与某张许可绑定；资源池仍需受保护队列或无锁结构管理对象。

## 内存同步

这些原语不仅阻塞线程，还建立标准规定的同步关系，使阶段前写入对阶段后线程可见。仍需遵守每个原语的到达、释放和访问顺序，不能用一个 barrier 自动保护阶段内部的并发写。

latch 计数归零的操作与成功返回的等待建立同步，适合让多个生产者发布初始化结果。barrier 的阶段完成步骤强 happens-before 被解除的参与者从等待返回，使 completion 处理的阶段汇总可见。

semaphore 的 release 与随后成功 acquire 之间建立同步关系，但许可不标识某次具体 release 与业务对象的配对。若多生产者共享队列，队列写入还必须按自身并发协议完成，然后才 release 通知数量。

同步关系只覆盖按协议发生在相应操作之前/之后的访问。线程在 barrier 返回后并发写同一普通对象仍是数据竞争；阶段边界不是整个阶段内的互斥锁。

## 与条件变量的选择

条件变量适合等待任意谓词，并允许重复改变条件；latch/barrier 直接表达已知参与数量的阶段；semaphore 表达资源容量。选择与问题同构的原语能减少手写计数和虚假唤醒处理。

条件变量需要互斥量和显式谓词循环，能表达队列非空、状态枚举等任意条件。信号量内部保存许可，所以 release 可先于 acquire，不会像无谓词通知那样丢失；但它只表达数量，不表达复杂状态。

一次性“所有初始化任务完成”用 latch；每轮迭代所有工作者汇合用 barrier；最多 N 个并发访问或 N 项可消费资源用 semaphore。用 binary_semaphore 模拟 mutex 时要自己保证释放配对和异常安全，普通 mutex RAII 通常更好。

future/promise 适合传递一次结果或异常，latch 只传递完成事件没有值。选择原语时也要考虑错误传播和取消，而不只看唤醒功能。

## 死锁与异常

参与者在到达前异常退出，会让 latch/barrier 永远等不到目标计数。线程创建失败、提前返回和取消路径必须显式补偿计数或采用 RAII 到达守卫。完成函数应短小且不抛异常。

barrier 的 arrival_token 代表特定阶段，必须交给对应 barrier 的等待且不能错误复用。把 token 遗失同时又要求该线程等待，会破坏控制流设计；移动 token 后原对象不再表示有效到达。

`arrive_and_drop` 适合线程永久退出迭代，但临时跳过一轮不能用 drop，否则下一阶段参与数永久减少。动态工作者加入不受 barrier 直接支持，需要在阶段外重建同步结构或采用其他调度模型。

semaphore 没有自动归还许可的标准守卫。acquire 后发生异常或提前返回时，应使用自定义 RAII permit guard，确保 release 恰好一次。重复 release 会超过逻辑容量，即便实现计数上限尚未触发也会破坏资源约束。

## 性能与公平性

这些原语允许实现先自旋再进入内核等待，也可用平台 futex/event 等机制；标准不规定内部结构。短阶段、参与者多于核心数、completion 较重时，barrier 调度成本可能明显。

信号量不保证严格 FIFO 公平，某个等待线程可能长期得不到许可。需要服务等级或优先级时，应在更高层队列明确调度，不从唤醒顺序推断业务公平。

latch/barrier 共享计数会形成缓存热点。把非常细粒度循环每次都同步，可能让屏障成本超过工作；应基准调整批量大小，并观察最慢参与者造成的尾延迟。

## 示例解析与实践

示例用信号量启动工作线程，主/工作线程在 barrier 汇合，再用 latch 通知工作完成。虽然为了教学同时展示三种原语，生产代码应使用最少且语义最贴合的一种。为所有等待设置外部超时监控，并测试参与者减少和提前取消。

## 权威资料

- [P1135R6：同步库](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1135r6.html)
- [工作草案：Coordination types](https://eel.is/c++draft/thread.coord)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
