# 内联变量与嵌套命名空间

内联变量允许在头文件中定义同一个变量而不违反单一定义规则。嵌套命名空间语法则缩短了多层命名空间声明。

<!-- example id="cpp17-inline-variables" std="c++17" file="main.cpp" kind="single" compilers="all" output="cpp-features:1" -->
```cpp
#include <iostream>
#include <string_view>

namespace project::config {
inline constexpr std::string_view name = "cpp-features";
inline int active_readers = 0;
}

int main() {
    ++project::config::active_readers;
    std::cout << project::config::name << ':'
              << project::config::active_readers << '\n';
}
```

`inline` 解决的是跨翻译单元定义问题，并不提供线程安全。可在编译期确定的配置值优先写成 `inline constexpr`。

## 从内联函数到内联变量

`inline` 的核心语义不是“要求优化器内联”，而是允许一个实体在多个翻译单元中出现相同定义，并在程序中表示同一实体。C++17 把这套 ODR 规则扩展到变量，使头文件可以直接定义具有统一地址的全局对象。

每个翻译单元看到的定义必须由相同标记序列组成，并满足名称查找一致等 ODR 要求。违反规则通常不要求链接器诊断，可能形成难以复现的问题。实现一般借助弱符号或 COMDAT 合并定义，但这是 ABI 手段，不是标准接口。

## `inline constexpr` 与静态成员

命名空间作用域 `constexpr` 变量过去常具有内部链接，取地址和跨单元身份需要谨慎处理。`inline constexpr` 明确允许头文件定义并提供统一实体。类内 `static constexpr` 数据成员在 C++17 起隐式是内联变量，不再总需要额外类外定义。

## 初始化与线程安全

内联变量仍可能进行动态初始化，并受到跨翻译单元初始化顺序问题影响。复杂全局对象若依赖另一个全局对象，`inline` 不会自动建立可靠顺序。优先使用常量初始化，或通过函数局部静态实现首次使用时初始化。

对 `active_readers` 的递增仍是普通非原子写；多个线程同时执行会数据竞争。需要同步时使用原子或锁，不要把链接语义误解为并发语义。

## 嵌套命名空间与实践

`namespace project::config` 等价于逐层嵌套声明，减少缩进但不改变名称查找。版本化 API 可结合内联命名空间，而普通嵌套语法本身不会让命名空间“内联”。

头文件中的配置优先 `inline constexpr`；可变全局状态应尽量避免；必须存在时明确初始化顺序、线程安全和测试隔离策略。
