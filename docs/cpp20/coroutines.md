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

