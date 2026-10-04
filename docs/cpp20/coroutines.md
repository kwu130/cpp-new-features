# Coroutines

阅读前建议先了解：[对象生命周期](../prerequisites.md#对象生命周期与引用)、[移动与所有权](../cpp11/move-semantics.md#先比较复制与移动)；手动暂停/恢复不要求线程背景。本篇介绍的新增能力属于 C++20；后续版本差异会另行标注。

## 学习目标与回调状态机问题

C++17 中，生成序列或异步等待通常通过迭代器对象、回调链、Future 或手写状态机表达。跨越暂停点的局部状态必须搬进对象，控制流被拆散，错误、取消和所有权也容易隐藏在框架约定中。

C++20 协程允许函数暂停，把控制权交还给调用者，稍后从暂停处继续。co_await 等待一个操作，是否真正挂起由等待协议决定；co_yield 产生值并通过等待协议继续或挂起；co_return 表示完成，而不是另一个可恢复的产出点。语言本身不会创建线程或事件循环。

先观察“暂停前 → 返回调用方 → 手动恢复 → 完成”，再了解编译器如何保存状态。协程帧是保存暂停状态的存储，句柄是访问它的工具，Promise 是由编译器调用的用户协议对象，不是 std::promise。C++20 标准库没有现成的通用 task 或 generator，因此教学示例需要定义一个很小的管理类型。

## 最小语法与角色

```text
co_await awaitable;   // 等待并可能挂起
co_yield value;       // 产生值，大致等价于 co_await promise.yield_value(value)
co_return result;     // 完成，转换为 promise.return_value/return_void

return_object ──拥有/引用──> coroutine_handle ──指向──> coroutine frame
```

## 先看暂停与恢复

传统函数调用会连续执行到 return，再交还控制权。若要手工分成两次调用，通常要用一个对象记录当前阶段；协程让编译器保存这个阶段及跨暂停点仍需存活的状态。

下面的完整程序较长，因为 C++20 需要我们自己提供管理类型。先只看要实现的控制流：

```text
ManualTask work() {
    输出 before;
    co_await std::suspend_always{}; // 在这里暂停，回到调用方
    输出 after;                    // 恢复时从这里继续
}
```

| 调用方做的事 | work 中发生的事 |
| --- | --- |
| `task = work()` | 输出 before，执行到 co_await 后暂停 |
| 第一次 `task.resume()` | 从暂停处继续，输出 after，完成函数 |
| 第二次 `task.resume()` | 包装器发现已经完成，不再恢复 |
| task 离开作用域 | 包装器释放保存的协程状态 |

下面的 `ManualTask` 就负责这份状态的唯一所有权。第一次阅读可以从程序末尾的 `work` 和 `main` 开始，再返回管理类型；Promise 接口留待后文。

```cpp example id="cpp20-manual-coroutine-resume" std="c++20" file="main.cpp" kind="single" compilers="all" output="before after"
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
    task.resume(); // 完成后安全地不再推进
}
```

`initial_suspend` 不挂起，所以调用 `work()` 时立即输出前半段；显式 `co_await suspend_always` 保存状态并返回调用方；`resume()` 从该点继续，随后到达会挂起的 `final_suspend`，最终由 `ManualTask` 析构销毁帧。

手动恢复适合解释控制流，没有并发、I/O 或调度器。简单同步函数不需要改成协程；逐个生成数据、跨异步等待保存局部状态时才可能受益。下面的生成器增加产出当前值的协议，后半篇再解释帧与 awaiter（等待协议对象）的细节。

## 再看逐个产出值的生成器

下面的 `Generator` 是教学用最小拥有类型：Promise 保存当前值，句柄负责恢复，析构函数负责销毁帧。生产代码还需更完整的迭代器、异常和误用保护。

```cpp example id="cpp20-coroutines" std="c++20" file="main.cpp" kind="single" compilers="all" output="1 2 3"
#include <cassert>
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
        if (!handle_ || handle_.done()) return false;
        handle_.resume();
        return !handle_.done();
    }
    int value() const {
        assert(handle_ && !handle_.done()); // 必须先有成功的 next()
        return handle_.promise().current;
    }

private:
    std::coroutine_handle<promise_type> handle_;
};

Generator sequence() {
    for (int value = 1; value <= 3; ++value) {
        co_yield value;
    }
}

int main() {
    Generator original = sequence();
    Generator generator = std::move(original);
    assert(!original.next()); // 移动后不再拥有句柄
    bool first = true;
    while (generator.next()) {
        std::cout << (first ? "" : " ") << generator.value();
        first = false;
    }
    assert(!generator.next()); // 完成后再次 next() 不得 resume
    assert(!generator.next());
    std::cout << '\n';
}
```

程序输出 `1 2 3`。next() 在移动后为空或已完成时返回 false，断言覆盖这两条边界；value() 的调用契约是前一次 next() 成功且尚未再次推进。每次 `next()` 恢复到下一个 `co_yield`，Promise 先保存值再挂起；循环结束后句柄处于完成状态，最终由 Generator 析构。协程帧和句柄所有权必须清晰：遗失 `destroy` 会泄漏，过早销毁会留下悬空句柄。

## 进一步理解：编译器如何改写协程

函数体出现 `co_await`、`co_yield` 或 `co_return` 后，编译器把它转换为状态机。局部变量、当前挂起点、Promise 对象等通常放进协程帧；调用返回一个由 `promise_type::get_return_object()` 创建的外部对象。

协程帧通常动态分配，但编译器在生命周期严格嵌套且大小可知时可以消除分配。分配策略还可由 Promise 提供定制 `operator new`。标准规定语义，不保证帧布局、分配位置或状态编号。

函数是否成为协程由函数体中的协程关键字决定，而不是返回类型名字。协程不能是构造函数、析构函数、`constexpr` 函数或其他受规则禁止的函数形式。

参数先按普通调用规则建立，再被保存进帧；按值参数拥有自己的对象，引用参数仍只是引用。局部变量只有在挂起点之后仍可能需要时才必须跨挂起保留，实现可按活跃区间优化帧布局。

调用协程函数通常先完成参数处理和帧分配，再构造 Promise、取得返回对象并经过 `initial_suspend`。返回给调用方的不一定是结果值，而是由返回类型协议定义的任务/生成器句柄包装。

### Promise 类型如何确定

编译器通过 `std::coroutine_traits<ReturnType, ParameterTypes...>::promise_type` 确定 Promise。对非静态成员函数，隐式对象参数也参与 traits 参数序列。最常见做法是在返回类型中定义嵌套 `promise_type`；高级库也可以特化 `coroutine_traits`，但必须遵守标准库特化规则。

Promise 构造会按规定尝试利用协程参数，因此框架可以把 allocator 或执行上下文送入 Promise。构造函数选择属于编译期协议，不能依赖从尚未执行的协程函数体给 Promise 赋值。参数副本的生命周期覆盖协程帧，而引用参数仍不拥有引用目标。

普通局部对象若跨挂起点活跃，帧需要记录它是否已经构造，以便异常或提前销毁时只析构已建立对象。编译器生成的状态机不只是一个“下一行编号”，还包含异常清理和各局部生命周期分支。

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

编译器创建返回对象与进入用户函数体不是同一件事：帧和 Promise 构造完成后调用 `get_return_object()`，随后才等待 `initial_suspend` 的 awaiter。对于 lazy 协程，调用方已经拿到任务对象，但函数体中第一个普通语句尚未执行；参数求值和 Promise 构造的副作用则已经发生。

走到函数体末尾只适合具有 void 返回协议的协程；需要结果的协程必须执行相应 `co_return value`。普通 `return` 不能绕过 Promise 协议。Promise 接口缺失或同时声明冲突返回协议时，编译器应在协程定义处拒绝。

最终挂起点承担“结果已就绪但帧可能仍需消费者读取”的边界。`final_suspend` 及其等待表达式按标准要求不得潜在抛出异常，不只是工程建议。任务库通常把用户异常更早存进 Promise，再在消费者的 `await_resume` 中重抛。

## `co_await` 协议

等待表达式最终提供 awaiter，其 `await_ready` 判断是否无需挂起，`await_suspend` 接收当前协程句柄并安排恢复，`await_resume` 产生表达式结果。调度器、I/O 框架和任务类型的核心工作发生在 `await_suspend`，语言本身不会创建线程或事件循环。

`co_yield value` 大致转换为 `co_await promise.yield_value(value)`。示例的 `yield_value` 保存当前整数并返回 `suspend_always`，调用方每次 `resume` 只推进到下一个产出点。

awaitable 到 awaiter 的转换可能先经过 Promise 的 `await_transform`，再尝试成员 `operator co_await`、非成员 `operator co_await`，或直接把对象当 awaiter。任务库可用 `await_transform` 统一拦截协程体中的等待表达式，但过度定制会让普通 awaitable 在该协程中失效。

`await_ready()` 返回真时跳过挂起，直接执行 `await_resume()`，是同步快速完成路径。返回假时，协程先进入挂起状态，再调用 `await_suspend(handle)`；该函数可返回 `void`、`bool` 或另一个协程句柄，三种形式分别表达不同恢复控制。

`await_suspend` 常把当前句柄发布给事件循环。句柄一旦被其他线程恢复，当前协程可能并发继续甚至销毁 awaiter，因此 `await_suspend` 发布后不应再访问可能随帧销毁的 `this` 状态。跨线程调度还需要普通 C++ 内存同步，协程关键字不会自动消除数据竞争。

### 三种 `await_suspend` 返回形式

返回 `void` 表示当前协程保持挂起，恢复责任已交给 awaiter/外部系统；返回 `bool` 时，`false` 表示不要保持挂起、当前协程立即继续，`true` 表示维持挂起；返回 `coroutine_handle` 则把执行权转移给指定协程。三者不是风格差异，而是不同调度协议。

`await_ready()` 为真时完全不会调用 `await_suspend`，但仍会调用 `await_resume()` 取得值或抛出已完成操作的错误。快路径和慢路径必须在结果、异常与取消语义上保持一致，不能把必要状态只放在注册回调的慢路径建立。

`await_resume()` 的返回值就是整个 `co_await` 表达式的结果。返回引用时，引用目标必须至少活到协程使用结束；将异步操作对象内部临时缓冲区的引用交给恢复后的代码，可能在下一次操作启动时立即失效。

若 Promise 定义 `await_transform`，一般等待表达式会先被它转换；随后才考虑成员/非成员 `operator co_await` 或对象自身 awaiter 协议。框架可借此注入调度、取消检查和追踪，但过宽的 catch-all 转换会改变第三方 awaitable 的含义，应保留受约束的透传路径。

## 生命周期与对称转移

句柄只是非拥有指针式对象。持有者必须确保每个未自动销毁的帧恰好 `destroy()` 一次，且恢复已经完成或销毁的协程是错误。挂起期间引用的外部对象也必须存活；普通函数栈已返回并不代表引用被自动复制进帧。

协程之间可以通过从 `await_suspend` 返回另一个句柄实现对称转移，避免层层恢复导致栈增长，但这属于任务库设计的高级部分。

`coroutine_handle<>` 可从有类型句柄擦除 Promise 类型，提供 `resume()`、`destroy()`、`done()` 和地址转换等底层操作。它通常可平凡复制，复制不会增加引用计数；多个副本并不共同拥有帧。必须在更高层类型中定义唯一所有权或共享协调。

`done()` 只应在协程已挂起时查询，它表示协程是否挂在最终挂起点。对空句柄调用恢复/销毁，恢复运行中的协程，或恢复已经完成且不允许恢复的帧都可能违反前置条件。

提前销毁挂起协程会先析构仍存活的局部对象，再销毁 Promise 和参数副本，并释放帧；正常完成时局部对象已经在进入最终挂起前清理。消费者提前停止生成器时，这条路径必须正确释放资源。若帧正在另一个线程排队等待恢复，直接销毁会制造 use-after-free，取消协议必须先从调度器撤销或协调句柄。

### 有类型与无类型句柄

`coroutine_handle<Promise>` 能通过 `promise()` 访问特定 Promise；转换为 `coroutine_handle<>` 后仍可恢复、销毁或取地址，但失去类型安全的 Promise 访问。无类型句柄适合调度器队列，有类型句柄适合任务对象管理结果，两者都不是拥有型智能指针。

`from_promise` 建立 Promise 引用到所属帧句柄的映射；`address()` / `from_address()` 用于底层擦除桥接。只有由兼容句柄产生的地址才能安全还原，任意对象地址不能伪装成协程帧。地址也不构成稳定序列化标识。

句柄可复制意味着调度令牌很容易出现多个副本。框架必须用外层状态机确保只有一条路径执行 resume 或 destroy：完成回调、超时和取消若各自持有句柄而无仲裁，就会重复恢复或在销毁后恢复。

### 对称转移

若 `await_suspend` 返回另一个 `coroutine_handle`，实现可直接把执行权转移给目标协程，而不是先返回某个调度循环再递归 resume。任务链在完成时把 continuation 句柄从 final awaiter 返回，可避免深链同步完成导致调用栈增长。

对称转移仍不等于线程切换。目标协程默认在当前执行线程继续，除非 awaiter 显式把句柄交给其他执行器。

## 异常、取消与线程

异常穿过协程体时不会直接跨挂起边界抛给最初调用者，而是由编译器捕获并调用 `unhandled_exception()`。任务 Promise 常保存 `current_exception()`，等待方在 `await_resume()` 取结果时重新抛出。若任务从未被等待，库必须定义异常是被观察、记录还是终止。

C++20 协程语言本身没有取消令牌。可把 `stop_token`、取消槽或业务标志整合进 awaitable：在挂起前检查取消，在注册 I/O 后能撤销回调，并处理取消与完成同时发生的竞态。

协程可能在任意恢复它的线程继续，线程局部状态、GUI 线程亲和性和锁所有权都要纳入执行器契约。绝不要持有普通互斥锁跨越可能切换线程或长时间等待的 `co_await`，除非同步原语明确支持这种设计。

取消至少要处理“尚未提交操作”“已提交等待完成”“完成与取消同时发生”三类状态。稳健 awaiter 往往用原子状态或受锁状态机选出唯一恢复者，并让败方只做资源清理。先检查布尔取消标志再注册回调会留下检查后立刻取消的窗口。

销毁任务对象不必然等同取消底层 I/O。若操作系统或事件循环仍持有回调，它可能稍后使用已经释放的帧地址。任务析构策略必须先撤销/隔离外部回调，等待确认不再访问，或把回调状态放进独立共享所有权对象，再决定何时销毁协程帧。

跨线程恢复需要发布 Promise 结果、awaiter 状态和 continuation 的普通内存同步。把句柄塞进没有同步的数据结构再由另一线程 resume 仍是数据竞争；协程语言只定义控制转移，不替代原子、互斥量或执行器队列的 happens-before（先发生于关系，用于说明线程间哪些操作的结果必须可见） 保证。

## 生成器与任务的协议差异

生成器通常由消费者主动 `resume`，`co_yield` 保存当前引用/值，并在消费者停止时销毁；任务通常由完成事件恢复，保存结果/异常，并支持另一个协程 `co_await`。两者的 initial/final suspend、所有权和背压完全不同。

一个健壮任务类型还要处理：多次等待是否合法、任务对象销毁时是否取消、continuation 在哪个线程恢复、结果引用生命周期、帧是否自销毁以及未观察异常。标准只提供拼装这些语义的语言钩子，没有给出统一答案。

## 性能与工程实践

协程降低异步控制流的源代码复杂度，不会自动让操作非阻塞。成本包括帧分配、状态跳转、调度和缓存局部性；同步快速完成路径可通过 `await_ready` 避免挂起。

生产代码应复用成熟任务类型，明确取消、异常、执行器、销毁线程和背压语义；测试立即完成、挂起后完成、异常、取消、从未恢复和消费者提前销毁等路径。

## 协程协议速查

| 钩子/设施 | 关键职责 |
| --- | --- |
| `coroutine_traits` | 从返回类型和参数确定 `promise_type` |
| `get_return_object` | 创建交给调用者的任务/生成器外壳 |
| `initial_suspend` | 决定 eager 运行还是 lazy 初始挂起 |
| `return_value/void` | 接收 `co_return` 结果 |
| `unhandled_exception` | 接收逃出协程体的异常 |
| `final_suspend` | 决定完成后的续体和帧销毁边界 |
| `await_ready` | true 时跳过挂起直接取结果 |
| `await_suspend` | 发布句柄/调度恢复，可返回 void、bool 或句柄 |
| `await_resume` | 产生 `co_await` 结果或重抛错误 |
| `coroutine_handle` | 非拥有帧句柄，复制不增加所有权 |
| `resume()` | 只对合法挂起且未完成协程调用 |
| `destroy()` | 恰好一次销毁挂起帧并析构内部对象 |

## 协程故障定位线索

- 帧泄漏：确认最终挂起的拥有任务析构是否调用 destroy。
- 二次释放：检查自销毁 `final_suspend` 与外部拥有者是否同时销毁。
- 首行未执行：`initial_suspend` 采用 lazy 策略，需要首次 resume/await。
- 回调后 use-after-free：外部完成事件仍保存已销毁帧句柄。
- 偶发二次 resume：完成、取消、超时缺少唯一获胜状态机。
- 异常消失：检查 `unhandled_exception` 存储及 `await_resume` 重抛路径。
- 栈持续增长：同步任务链未使用适当对称转移 continuation。
- 锁死：普通 mutex 被跨 `co_await` 持有或在不同线程恢复后释放。
- 引用悬空：协程引用形参没有复制调用者对象进帧。
- 线程不符合预期：记录每个 awaiter 把 continuation 提交到哪个执行器。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp20/coroutines.md
```

## 权威资料

- [协程句柄操作与前置条件](https://eel.is/c++draft/coroutine.handle.resumption)
- [P0912R5：协程并入 C++20](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0912r5.html)
- [工作草案：Coroutines](https://eel.is/c++draft/dcl.fct.def.coroutine)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
