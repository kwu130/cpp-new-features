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

函数是否成为协程由函数体中的协程关键字决定，而不是返回类型名字。协程不能是构造函数、析构函数、`constexpr` 函数或其他受规则禁止的函数形式。

参数先按普通调用规则建立，再被保存进帧；按值参数拥有自己的对象，引用参数仍只是引用。局部变量只有在挂起点之后仍可能需要时才必须跨挂起保留，实现可按活跃区间优化帧布局。

调用协程函数通常先完成参数处理和帧分配，再构造 Promise、取得返回对象并经过 `initial_suspend`。返回给调用方的不一定是结果值，而是由返回类型协议定义的任务/生成器句柄包装。

### 帧分配失败

若 Promise 类型提供合适的 `get_return_object_on_allocation_failure()`，协程帧分配会使用不抛形式并由该函数返回失败对象；否则分配失败通常抛 `bad_alloc`。自定义 Promise `operator new` 可以接收帧大小，并在满足签名规则时接收协程参数以选择 allocator。

分配消除是允许优化，程序正确性不能依赖是否调用 Promise 的分配函数。统计或注册等业务副作用不应放进仅为帧内存管理设计的 `operator new`。

## Promise 与三个关键阶段

返回类型通过 `promise_type` 定义协议。调用开始后构造 Promise，并调用 `initial_suspend` 决定立即运行还是先挂起；正常结束通过 `return_value` 或 `return_void`；最后调用 `final_suspend` 决定是否保留帧等待外部销毁或续体。

`unhandled_exception` 接收逃出协程体的异常。任务类型通常保存 `exception_ptr`，在等待结果时重新抛出；示例为简化直接终止进程。

Promise 不是 `std::promise`，两者只共享英文含义。它是由编译器按协程协议调用的用户类型，通常成为帧内对象。外部返回对象可通过 `coroutine_handle<promise_type>::from_promise` 关联它。

`initial_suspend` 返回 awaiter：返回 `suspend_always` 形成 lazy 协程，调用后尚未执行用户函数体；返回 `suspend_never` 形成 eager 协程，立即运行到首个挂起点或结束。任务库必须明确选择，否则调用者无法判断副作用何时发生。

`final_suspend` 在正常 `co_return` 或函数体结束后执行。若它不挂起，帧可能自动销毁，外部句柄必须避免再次访问；若它挂起，拥有者需销毁帧，并可在该阶段恢复 continuation。析构 Promise、参数副本和帧存储的顺序由协程销毁流程管理。

非 void 结果通常由 `return_value(value)` 接收，void 结果用 `return_void()`；Promise 不能同时以冲突方式提供两者。`co_return expression` 不等于普通 `return expression`，它通过 Promise 协议保存结果并进入最终挂起流程。

## `co_await` 协议

等待表达式最终提供 awaiter，其 `await_ready` 判断是否无需挂起，`await_suspend` 接收当前协程句柄并安排恢复，`await_resume` 产生表达式结果。调度器、I/O 框架和任务类型的核心工作发生在 `await_suspend`，语言本身不会创建线程或事件循环。

`co_yield value` 大致转换为 `co_await promise.yield_value(value)`。示例的 `yield_value` 保存当前整数并返回 `suspend_always`，调用方每次 `resume` 只推进到下一个产出点。

awaitable 到 awaiter 的转换可能先经过 Promise 的 `await_transform`，再尝试成员 `operator co_await`、非成员 `operator co_await`，或直接把对象当 awaiter。任务库可用 `await_transform` 统一拦截协程体中的等待表达式，但过度定制会让普通 awaitable 在该协程中失效。

`await_ready()` 返回真时跳过挂起，直接执行 `await_resume()`，是同步快速完成路径。返回假时，协程先进入挂起状态，再调用 `await_suspend(handle)`；该函数可返回 `void`、`bool` 或另一个协程句柄，三种形式分别表达不同恢复控制。

`await_suspend` 常把当前句柄发布给事件循环。句柄一旦被其他线程恢复，当前协程可能并发继续甚至销毁 awaiter，因此 `await_suspend` 发布后不应再访问可能随帧销毁的 `this` 状态。跨线程调度还需要普通 C++ 内存同步，协程关键字不会自动消除数据竞争。

<!-- example id="cpp20-manual-coroutine-resume" std="c++20" file="main.cpp" kind="single" compilers="all" output="before after" -->
```cpp
#include <coroutine>
#include <exception>
#include <iostream>
#include <utility>

class ManualTask {
public:
    struct promise_type {
        ManualTask get_return_object() noexcept {
            return ManualTask(
                std::coroutine_handle<promise_type>::from_promise(*this));
        }
        std::suspend_never initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        void return_void() noexcept {}
        void unhandled_exception() noexcept { std::terminate(); }
    };

    explicit ManualTask(std::coroutine_handle<promise_type> handle) noexcept
        : handle_(handle) {}
    ManualTask(const ManualTask&) = delete;
    ManualTask(ManualTask&& other) noexcept
        : handle_(std::exchange(other.handle_, {})) {}
    ~ManualTask() {
        if (handle_) {
            handle_.destroy();
        }
    }

    void resume() {
        if (handle_ && !handle_.done()) {
            handle_.resume();
        }
    }

private:
    std::coroutine_handle<promise_type> handle_;
};

ManualTask work() {
    std::cout << "before ";
    co_await std::suspend_always{};
    std::cout << "after\n";
}

int main() {
    ManualTask task = work();
    task.resume();
}
```

`initial_suspend` 不挂起，所以调用 `work()` 时立即输出前半段；显式 `co_await suspend_always` 保存状态并返回调用方；`resume()` 从该点继续，随后到达会挂起的 `final_suspend`，最终由 `ManualTask` 析构销毁帧。

## 生命周期与对称转移

句柄只是非拥有指针式对象。持有者必须确保每个未自动销毁的帧恰好 `destroy()` 一次，且恢复已经完成或销毁的协程是错误。挂起期间引用的外部对象也必须存活；普通函数栈已返回并不代表引用被自动复制进帧。

协程之间可以通过从 `await_suspend` 返回另一个句柄实现对称转移，避免层层恢复导致栈增长，但这属于任务库设计的高级部分。

`coroutine_handle<>` 可从有类型句柄擦除 Promise 类型，提供 `resume()`、`destroy()`、`done()` 和地址转换等底层操作。它通常可平凡复制，复制不会增加引用计数；多个副本并不共同拥有帧。必须在更高层类型中定义唯一所有权或共享协调。

`done()` 只应在协程已挂起时查询，它表示协程是否挂在最终挂起点。对空句柄调用恢复/销毁，恢复运行中的协程，或恢复已经完成且不允许恢复的帧都可能违反前置条件。

销毁挂起协程会析构 Promise、参数副本和仍存活的局部对象，再释放帧。消费者提前停止生成器时，这条路径必须正确释放资源。若帧正在另一个线程排队等待恢复，直接销毁会制造 use-after-free，取消协议必须先从调度器撤销或协调句柄。

### 对称转移

若 `await_suspend` 返回另一个 `coroutine_handle`，实现可直接把执行权转移给目标协程，而不是先返回某个调度循环再递归 resume。任务链在完成时把 continuation 句柄从 final awaiter 返回，可避免深链同步完成导致调用栈增长。

对称转移仍不等于线程切换。目标协程默认在当前执行线程继续，除非 awaiter 显式把句柄交给其他执行器。

## 异常、取消与线程

异常穿过协程体时不会直接跨挂起边界抛给最初调用者，而是由编译器捕获并调用 `unhandled_exception()`。任务 Promise 常保存 `current_exception()`，等待方在 `await_resume()` 取结果时重新抛出。若任务从未被等待，库必须定义异常是被观察、记录还是终止。

C++20 协程语言本身没有取消令牌。可把 `stop_token`、取消槽或业务标志整合进 awaitable：在挂起前检查取消，在注册 I/O 后能撤销回调，并处理取消与完成同时发生的竞态。

协程可能在任意恢复它的线程继续，线程局部状态、GUI 线程亲和性和锁所有权都要纳入执行器契约。绝不要持有普通互斥锁跨越可能切换线程或长时间等待的 `co_await`，除非同步原语明确支持这种设计。

## 生成器与任务的协议差异

生成器通常由消费者主动 `resume`，`co_yield` 保存当前引用/值，并在消费者停止时销毁；任务通常由完成事件恢复，保存结果/异常，并支持另一个协程 `co_await`。两者的 initial/final suspend、所有权和背压完全不同。

一个健壮任务类型还要处理：多次等待是否合法、任务对象销毁时是否取消、continuation 在哪个线程恢复、结果引用生命周期、帧是否自销毁以及未观察异常。标准只提供拼装这些语义的语言钩子，没有给出统一答案。

## 性能与工程实践

协程降低异步控制流的源代码复杂度，不会自动让操作非阻塞。成本包括帧分配、状态跳转、调度和缓存局部性；同步快速完成路径可通过 `await_ready` 避免挂起。

生产代码应复用成熟任务类型，明确取消、异常、执行器、销毁线程和背压语义；测试立即完成、挂起后完成、异常、取消、从未恢复和消费者提前销毁等路径。

## 权威资料

- [P0912R5：协程并入 C++20](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0912r5.html)
- [工作草案：Coroutines](https://eel.is/c++draft/dcl.fct.def.coroutine)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
