# `jthread`、停止令牌与协作取消

`jthread` 析构时自动请求停止并连接线程。若可调用对象首参数接受 `stop_token`，它就能响应协作式取消。

```cpp example id="cpp20-jthread" std="c++20" file="main.cpp" kind="single" compilers="all" output="42"
#include <iostream>
#include <stop_token>
#include <thread>

int main() {
    int result = 0;
    std::jthread worker([&result](std::stop_token token) {
        if (!token.stop_requested()) {
            result = 42;
        }
    });
    worker.join();
    std::cout << result << '\n';
}
```

停止请求不会强行终止线程，任务必须在合适位置查询令牌或注册回调。自动 `join` 改善异常安全，但持锁析构 `jthread` 仍可能造成死锁。

## RAII 线程所有权

`std::thread` 在仍可连接时析构会终止程序，异常路径容易漏掉 `join`。`jthread` 析构时若可连接，先请求停止再连接，使线程所有权与对象作用域一致。它仍可能无限等待：若任务忽略停止请求或阻塞在不可取消操作上，析构就会阻塞。

`jthread` 可移动不可复制。移动会转移线程句柄和停止源，源对象变为不可连接。显式 `join()` 后析构不再重复连接。

析构的概念顺序是：若 `joinable()`，调用 `request_stop()`，随后 `join()`。停止回调可能就在析构线程同步运行，然后析构线程等待工作线程结束。因此析构不是轻量清理操作，作用域边界可能成为阻塞点。

`detach()` 仍然存在；分离后对象不再可连接，析构不能等待线程，也无法靠自身生命周期保证捕获对象存活。除非有独立所有权管理，优先保留 joinable RAII 语义。

与 `thread` 类似，`get_id()`、`native_handle()`、`hardware_concurrency()` 等服务于线程身份/平台集成。native handle 操作不受标准停止协议保护，平台调用与 jthread 生命周期必须协调。

### 可调用对象的令牌注入

构造时若函数对象可按 `(stop_token, args...)` 调用，jthread 优先采用这一路径并自动传入关联令牌；否则按普通 `(args...)` 调用。令牌位置固定在用户参数之前，不是任意匹配。

过载函数对象若两种签名都可调用，令牌版本会改变选择。公共任务类型应明确提供哪种 operator()，避免通用转发重载意外吞掉 `stop_token`。

注入检查发生在构造模板的可调用性判断中，首参数必须能按规定接收 `stop_token`，随后才是用户参数。若某个泛型 `operator()(auto&&...)` 同时接受任意形状，它很可能意外走令牌版本；可用显式重载、Concept 或包装 Lambda 固定意图。

自动注入只发生在 jthread 启动入口。入口再调用子函数或创建普通 thread 时，令牌不会自动沿调用链传播，必须显式传递。任务树取消需要应用层保存 token/source 关系。

线程函数参数仍按线程构造的 decay-copy/调用规则进入新执行线程。把 `std::ref`、裸引用或 this 与 `stop_token` 一起传递，并不会因存在自动 join 就无条件安全；成员析构顺序和显式 join/detach 仍决定被引用对象寿命。

## 停止状态的组成

`stop_source` 可发出请求，`stop_token` 观察请求，`stop_callback` 在请求到达时运行回调；它们共享一个线程安全的停止状态。请求是幂等的，首次成功请求触发已注册回调。

当 jthread 的可调用对象能以 `stop_token` 作为首参数调用时，构造函数会自动传入令牌。停止只是协作信号，没有抢占式终止、栈展开或锁释放。任务必须选择安全检查点，并维护中止时的不变量。

停止状态通常是引用计数共享控制块，包含“是否请求停止”、已注册回调集合和同步元数据。标准规定观察行为，不规定分配方式或具体锁结构。复制 source/token 只是共享状态，不复制工作线程。

`stop_possible()` 区分“当前未请求”与“永远不可能由任何 source 请求”。默认构造的 `stop_token` 通常没有关联可停止状态；由 jthread 取得的令牌在相应状态存在时可停止。

```cpp example id="cpp20-stop-state" std="c++20" file="main.cpp" kind="single" compilers="all" output="first=true, second=false, callbacks=1"
#include <iostream>
#include <stop_token>

int main() {
    std::stop_source source;
    int callbacks = 0;
    std::stop_callback callback(source.get_token(), [&] {
        ++callbacks;
    });

    const bool first = source.request_stop();
    const bool second = source.request_stop();
    std::cout << std::boolalpha
              << "first=" << first
              << ", second=" << second
              << ", callbacks=" << callbacks << '\n';
}
```

首次请求原子地把共享状态转为已停止并调用已注册回调，返回 true；后续请求观察到状态已设置，返回 false，也不会再次调用同一回调。回调对象必须活到需要注册的区间结束，其析构会与并发执行协调。

多个 `stop_source` 可以引用同一状态，任何一个成功请求都会影响所有 token。销毁某个 source 不等于请求停止；只有状态再无可发出请求的 source 时，token 的 `stop_possible` 才可能反映不可停止。

`jthread::get_stop_source()` 返回共享同一状态的 source 副本，调用方可把它交给控制器；`get_stop_token()` 返回观察令牌。复制 source 延长“仍可请求”的能力，也可能让 token 在 jthread 对象生命周期之后继续显示 `stop_possible`，因此所有权设计要避免无意长期保存控制权。

`jthread::request_stop()` 只是对关联 source 请求的便捷入口，返回值仍表示此次调用是否完成首次状态转换，不表示工作线程已经退出。需要完成保证仍要 join 或由更高层完成事件确认。

默认构造的 `stop_source` 通常创建可停止状态；`nostopstate` 构造可得到不关联状态的 source，适合明确无取消能力的泛型路径。调用方应通过 `stop_possible` 分辨能力，而不是把 `stop_requested` 为 false 解释成未来一定能停止。

## 回调并发语义

停止回调可能在发出请求的线程同步执行；注册与请求并发时也有严格协调。回调应短小、不能假设运行在线程工作体中，并避免获取会与请求方形成环的锁。

等待循环可结合令牌感知的条件变量设施，减少轮询。对不支持取消的阻塞系统调用，仍需平台机制、超时或关闭句柄来唤醒。

若注册 `stop_callback` 时停止已经请求，回调会在构造过程中同步执行。若请求与注册竞争，标准协调保证回调不会既遗漏又无规则执行两次，但执行线程可能是请求线程或注册路径相关线程。

`stop_callback` 析构必须确保回调不再访问已销毁对象；若另一个线程正在执行回调，析构可能等待。回调内部销毁自身关联对象等重入场景有精细规则，常规设计应避免这种生命周期纠缠。

回调抛出异常会导致终止，因此回调应为不抛、短小操作，例如设置标志、通知条件变量、取消平台句柄。不要直接在回调里执行复杂清理或 join 当前线程。

`stop_callback` 模板拥有回调对象，通常不可移动/复制；注册生命周期就是该对象的作用域。把临时 callback 构造后立即丢弃会立即注销，后续停止请求不会执行它。需要注册跨越等待期时，callback 必须成为该等待状态的成员或局部守卫。

回调可以与 `request_stop` 同步执行，所以请求停止的调用耗时包含回调耗时。大量回调、锁竞争或系统取消调用会让 `request_stop()` 成为高延迟路径。框架应把回调限制为发布轻量信号，把昂贵清理留给工作线程。

回调捕获对象的析构顺序必须晚于 callback 注销完成。类成员按逆序析构时，承载 callback 的成员应先析构、被捕获状态后析构；这通常要求状态成员声明在 callback 之前。

### 可取消等待

`condition_variable_any` 在 C++20 提供接收 `stop_token` 的等待重载，可在谓词满足或停止请求时返回。普通 `condition_variable` 没有同样的通用令牌接口；可以用 `stop_callback` 通知它，但要仔细维护锁与谓词。

轮询 `stop_requested()` 的粒度决定取消延迟与检查开销。CPU 循环可按批次检查，阻塞 I/O 必须结合可中断调用、超时或关闭资源。令牌本身不会唤醒一个完全不知道它的系统调用。

## 取消语义与状态一致性

“停止”不是“失败”。任务应区分正常完成、请求取消、业务错误和外部资源失败，并决定部分结果是否提交。安全检查点通常放在一个事务单元完成之后，避免在不变量暂时破坏时退出。

请求只是建议，任务可能在请求到达前已经完成。调用方不能看到 `request_stop` 返回 true 就断言结果一定取消；最终状态要由任务协议报告。

停止传播可把父 token 连接到子 `stop_source`，但标准不会自动构建任务树。注册桥接回调时要管理回调对象生命周期，否则桥接刚创建就析构，后续请求无法传播。

取消检查点应位于不变量稳定处：例如完成一项队列任务后、提交事务前或下一块计算前。若在持有资源许可后立即退出，要用 RAII 归还许可；若已经产生部分输出，要定义丢弃、提交还是标记不完整。

多次请求天然幂等，但业务清理未必幂等。只让首次 `request_stop` 的回调负责发布信号，工作线程在单一退出路径清理，可避免多个控制者重复关闭句柄或重复提交取消结果。

## 析构和锁顺序风险

若持有工作线程完成所需互斥量时销毁 jthread，析构 join 会等待工作线程，而工作线程等待同一锁，形成死锁。应在锁外结束 jthread 生命周期，或先移动线程对象到安全作用域再释放锁。

类成员按声明逆序析构。若 jthread 使用其他成员，应把线程成员声明在被访问状态之后，使线程先析构/join，再销毁状态；构造失败路径也要遵守这一所有权顺序。

任务捕获 `this` 时，jthread 的自动 join 只有在它确实先于其他成员析构时才保护访问。显式成员布局、停止检查和析构测试缺一不可。

## 示例解析与工程策略

示例线程启动时令牌尚未请求停止，因此写入结果，主线程显式 join 后读取，建立可见性。真实任务应测试启动前取消、运行中取消、完成后请求、回调异常策略和析构阻塞上限，并让停止结果区别于业务失败。

## 线程停止接口速查

| 接口/类型 | 关键语义 |
| --- | --- |
| `jthread` 析构 | joinable 时先 `request_stop` 再 join |
| `detach` | 放弃自动等待，需独立保证捕获寿命 |
| token 注入 | 可调用 `(stop_token,args...)` 时优先该签名 |
| `stop_source` | 共享停止状态的请求端 |
| `stop_token` | 只读观察请求与能力 |
| `stop_callback` | 作用域注册回调，构造时可能同步执行 |
| `request_stop` | 首次状态转换返回 true，不表示线程已退出 |
| `stop_possible` | 区分未请求与状态根本不可请求 |
| `stop_requested` | 只查询协作标志，不中断阻塞系统调用 |
| `condition_variable_any` | C++20 提供 token 感知等待重载 |

## Jthread 专项审查问题

- 工作函数是否真的观察 token 并能在有限时间退出？
- 泛型调用对象是否意外触发 `stop_token` 自动注入重载？
- 析构 join 是否可能在持有工作线程需要的锁时发生？
- 成员声明顺序是否让 jthread 先于其访问状态析构？
- `stop_callback` 是否活到整个注册区间而非临时即销毁？
- 回调是否短小、不抛并避免与请求线程形成锁环？
- 阻塞 I/O 是否有平台取消、超时或关闭句柄路径？
- `request_stop` 的 true 是否被误解为线程已经停止？
- 父子任务停止传播的桥接 callback 是否持续存活？
- 正常完成、取消和业务失败是否用不同最终状态表达？

## Jthread 故障定位线索

- 析构长期阻塞：工作体未观察停止或卡在不可取消 I/O。
- 析构死锁：持有工作线程退出所需互斥量时发生自动 join。
- token 参数意外出现：泛型调用对象同时匹配了注入签名。
- callback 从未运行：注册对象构造后立即离开作用域注销。
- `request_stop` 很慢：回调在请求线程同步执行且工作过重。
- 回调访问悬空状态：成员析构顺序让被捕获对象先销毁。
- 取消后仍有结果：请求是协作建议，任务可能已先完成。
- 系统调用不醒：`stop_token` 不会自动中断不感知它的阻塞 API。
- 子任务不停：停止状态不会自动形成父子任务树。
- detach 后 use-after-free：jthread 已失去 join 对捕获生命周期的保护。

## 权威资料

- [P0660R10：jthread 与停止令牌](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0660r10.pdf)
- [工作草案：Stop tokens](https://eel.is/c++draft/thread.stoptoken)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
