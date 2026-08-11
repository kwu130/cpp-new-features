# `noexcept`、字面量、线程局部存储与对齐

这些能力分别表达异常保证、领域单位、线程独立状态和内存布局要求。

<!-- example id="cpp11-core-utilities" std="c++11" file="main.cpp" kind="single" compilers="all" output="2048 bytes, calls=2" -->
```cpp
#include <cstddef>
#include <iostream>
#include <type_traits>

constexpr std::size_t operator"" _KiB(unsigned long long value) {
    return static_cast<std::size_t>(value * 1024ULL);
}

thread_local int calls = 0;

void record_call() noexcept {
    ++calls;
}

struct alignas(16) Packet {
    char bytes[16];
};

int main() {
    record_call();
    record_call();
    static_assert(noexcept(record_call()), "record_call promises not to throw");
    static_assert(alignof(Packet) == 16, "Packet alignment must be 16");
    std::cout << 2_KiB << " bytes, calls=" << calls << '\n';
}
```

不要把可能抛出异常的函数错误标为 `noexcept`，否则异常逃出时程序会终止。用户定义字面量后缀应以下划线开头，避免与标准库保留名称冲突。

