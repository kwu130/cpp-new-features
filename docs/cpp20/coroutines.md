# Coroutines

协程允许函数挂起并稍后恢复，是生成器、异步任务和流式处理的底层语言机制。标准提供协程协议，但不直接提供通用任务类型。

<!-- example id="cpp20-coroutines" std="c++20" file="main.cpp" kind="single" compilers="all" output="1 2 3" -->
```cpp
#include <coroutine>
#include <exception>
#include <iostream>
#include <utility>

class Generator {
public:
    struct promise_type {
        int current = 0;
        Generator get_return_object() {
            return Generator(std::coroutine_handle<promise_type>::from_promise(*this));
        }
        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        std::suspend_always yield_value(int value) noexcept {
            current = value;
            return {};
        }
        void return_void() noexcept {}
        void unhandled_exception() { std::terminate(); }
    };

    explicit Generator(std::coroutine_handle<promise_type> handle) : handle_(handle) {}
    Generator(const Generator&) = delete;
    Generator(Generator&& other) noexcept : handle_(std::exchange(other.handle_, {})) {}
    ~Generator() { if (handle_) handle_.destroy(); }

    bool next() {
        handle_.resume();
        return !handle_.done();
    }
    int value() const { return handle_.promise().current; }

private:
    std::coroutine_handle<promise_type> handle_;
};

Generator sequence() {
    for (int value = 1; value <= 3; ++value) {
        co_yield value;
    }
}

int main() {
    Generator generator = sequence();
    bool first = true;
    while (generator.next()) {
        std::cout << (first ? "" : " ") << generator.value();
        first = false;
    }
    std::cout << '\n';
}
```

协程帧和句柄所有权必须清晰；遗失 `destroy` 会泄漏，过早销毁会留下悬空句柄。生产代码通常应使用经过验证的任务/生成器库，而不是反复手写协议类型。

## 编译器如何改写协程

函数体出现 `co_await`、`co_yield` 或 `co_return` 后，编译器把它转换为状态机。局部变量、当前挂起点、Promise 对象等通常放进协程帧；调用返回一个由 `promise_type::get_return_object()` 创建的外部对象。

协程帧通常动态分配，但编译器在生命周期严格嵌套且大小可知时可以消除分配。分配策略还可由 Promise 提供定制 `operator new`。标准规定语义，不保证帧布局、分配位置或状态编号。

## Promise 与三个关键阶段

返回类型通过 `promise_type` 定义协议。调用开始后构造 Promise，并调用 `initial_suspend` 决定立即运行还是先挂起；正常结束通过 `return_value` 或 `return_void`；最后调用 `final_suspend` 决定是否保留帧等待外部销毁或续体。

`unhandled_exception` 接收逃出协程体的异常。任务类型通常保存 `exception_ptr`，在等待结果时重新抛出；示例为简化直接终止进程。

## `co_await` 协议

等待表达式最终提供 awaiter，其 `await_ready` 判断是否无需挂起，`await_suspend` 接收当前协程句柄并安排恢复，`await_resume` 产生表达式结果。调度器、I/O 框架和任务类型的核心工作发生在 `await_suspend`，语言本身不会创建线程或事件循环。

`co_yield value` 大致转换为 `co_await promise.yield_value(value)`。示例的 `yield_value` 保存当前整数并返回 `suspend_always`，调用方每次 `resume` 只推进到下一个产出点。

## 生命周期与对称转移

句柄只是非拥有指针式对象。持有者必须确保每个未自动销毁的帧恰好 `destroy()` 一次，且恢复已经完成或销毁的协程是错误。挂起期间引用的外部对象也必须存活；普通函数栈已返回并不代表引用被自动复制进帧。

协程之间可以通过从 `await_suspend` 返回另一个句柄实现对称转移，避免层层恢复导致栈增长，但这属于任务库设计的高级部分。

## 性能与工程实践

协程降低异步控制流的源代码复杂度，不会自动让操作非阻塞。成本包括帧分配、状态跳转、调度和缓存局部性；同步快速完成路径可通过 `await_ready` 避免挂起。

生产代码应复用成熟任务类型，明确取消、异常、执行器、销毁线程和背压语义；测试立即完成、挂起后完成、异常、取消、从未恢复和消费者提前销毁等路径。
