# `jthread`、停止令牌与协作取消

`jthread` 析构时自动请求停止并连接线程。若可调用对象首参数接受 `stop_token`，它就能响应协作式取消。

<!-- example id="cpp20-jthread" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
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

## 停止状态的组成

`stop_source` 可发出请求，`stop_token` 观察请求，`stop_callback` 在请求到达时运行回调；它们共享一个线程安全的停止状态。请求是幂等的，首次成功请求触发已注册回调。

当 jthread 的可调用对象能以 `stop_token` 作为首参数调用时，构造函数会自动传入令牌。停止只是协作信号，没有抢占式终止、栈展开或锁释放。任务必须选择安全检查点，并维护中止时的不变量。

## 回调并发语义

停止回调可能在发出请求的线程同步执行；注册与请求并发时也有严格协调。回调应短小、不能假设运行在线程工作体中，并避免获取会与请求方形成环的锁。

等待循环可结合令牌感知的条件变量设施，减少轮询。对不支持取消的阻塞系统调用，仍需平台机制、超时或关闭句柄来唤醒。

## 示例解析与工程策略

示例线程启动时令牌尚未请求停止，因此写入结果，主线程显式 join 后读取，建立可见性。真实任务应测试启动前取消、运行中取消、完成后请求、回调异常策略和析构阻塞上限，并让停止结果区别于业务失败。

## 权威资料

- [P0660R10：jthread 与停止令牌](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0660r10.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
