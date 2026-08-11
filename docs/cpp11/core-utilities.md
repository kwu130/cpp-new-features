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

## `noexcept`：接口契约与优化条件

`noexcept` 是函数类型语义的一部分，表示异常不得逃出函数。若违反，运行时调用 `std::terminate`，不会让外层 `catch` 正常恢复。条件形式 `noexcept(condition)` 适合让模板函数的异常保证跟随成员操作。

`noexcept(expression)` 运算符不会执行表达式，而是在编译期查询它是否被声明为不抛异常。标准容器在搬迁元素时会参考移动构造是否 `noexcept`，从而决定移动能否保持强异常保证。因此准确标注会影响算法路径，错误标注则可能把可恢复异常变成终止。

## 用户定义字面量

字面量运算符把源代码中的数值、字符或字符串字面量转换成领域类型。编译器先按规定参数形式解析字面量，再调用对应运算符；它不是任意文本宏，不能改变语言词法规则。

示例使用整数形式接收 `unsigned long long` 并在编译期换算 KiB。实际单位库应返回强类型而非裸 `size_t`，从类型系统层面防止字节、时间和距离混用。自定义后缀必须以下划线开头，非下划线名称保留给标准库。

## `thread_local` 的存储模型

每个线程拥有变量的独立实例，变量在线程首次使用前完成初始化，在线程结束时销毁。实现通常通过线程本地存储段和运行时线程控制块定位对象，而不是为每次访问加锁。

线程局部状态减少共享竞争，但也会放大内存占用，并让测试、任务在线程池间迁移和析构顺序更复杂。它适合缓存或线程上下文，不应替代清晰的参数传递。

## 对齐控制

`alignas(N)` 指定对象至少满足 N 字节对齐，`alignof(T)` 查询类型对齐要求。编译器会在对象布局和数组步长中插入必要填充；更高对齐可能增加结构体大小。动态分配过度对齐类型在不同标准版本的支持不同，不能只看到类型声明通过就假设任意分配器都满足要求。

## 工程检查清单

异常保证必须与实现一致；单位字面量优先返回强类型；线程局部对象保持轻量且避免复杂析构依赖；布局相关代码同时验证 `sizeof`、`alignof` 和目标 ABI，而不是假设跨平台一致。

## 条件 `noexcept` 与泛型包装器

模板包装器的异常保证通常取决于被包装操作。条件 `noexcept(noexcept(expression))` 先在内层查询表达式，再把结果用于外层函数规格。这样类型系统可以准确区分不抛与可能抛出的实例。

<!-- example id="cpp11-conditional-noexcept" std="c++11" file="main.cpp" kind="single" compilers="all" output="safe=true, risky=false" -->
```cpp
#include <iostream>
#include <utility>

struct Safe {
    Safe(Safe&&) noexcept {}
};

struct Risky {
    Risky(Risky&&) noexcept(false) {}
};

template <typename T>
void relocate(T& value) noexcept(noexcept(T(std::move(value)))) {
    T moved(std::move(value));
    (void)moved;
}

int main() {
    std::cout << std::boolalpha
              << "safe=" << noexcept(relocate(std::declval<Safe&>()))
              << ", risky=" << noexcept(relocate(std::declval<Risky&>())) << '\n';
}
```

`declval` 只能用于不求值语境；它让查询代码不必真的构造对象。外层规格和函数体必须查询同一个操作，否则声明承诺可能与实际执行不一致。

## 线程局部实例的隔离

每个线程第一次访问函数内 `thread_local` 对象时，会初始化自己的实例。同名变量在不同线程有不同地址和状态；主线程也拥有独立实例。线程退出时，已构造的非平凡线程局部对象按实现管理的顺序销毁。

<!-- example id="cpp11-thread-local-isolation" std="c++11" file="main.cpp" kind="single" compilers="all" output="workers=2,2 main=0" -->
```cpp
#include <iostream>
#include <thread>

thread_local int calls = 0;

void run(int& result) {
    ++calls;
    ++calls;
    result = calls;
}

int main() {
    int first = 0;
    int second = 0;
    std::thread left(run, std::ref(first));
    std::thread right(run, std::ref(second));
    left.join();
    right.join();
    std::cout << "workers=" << first << ',' << second
              << " main=" << calls << '\n';
}
```

在线程池中，任务会复用工作线程，因此 thread_local 状态可能跨请求残留。请求上下文若需要严格清理，应使用作用域对象或显式重置，而不能假设每个任务获得新线程。

## 权威资料

- [异常规格](https://eel.is/c++draft/except.spec)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
