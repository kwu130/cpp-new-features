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

内联变量具有外部或模块相关链接语义时，在每个翻译单元中都可定义，并且程序中具有一个地址。它必须在每个发生 odr-use 的翻译单元中可达定义，这正适合把定义放在头文件。`extern` 声明加单独 `.cpp` 定义仍然有效，只是内联变量让这层文件管理不再是唯一方案。

“相同定义”不只指源文本看起来相似。定义内名称查找通常也必须得到同一实体，默认实参、内部链接常量、Lambda 等还受具体 ODR 条件约束。用条件宏让不同翻译单元看到不同初始化式会形成 ODR 违规，即使链接器安静合并了某个版本。

### 变量模板与统一实体

内联说明符也可用于变量模板。每个实际特化都是变量实体；`inline` 让头文件中的特化在跨单元 odr-use 时遵守统一定义模型。C++17 标准库大量 `_v` 类型萃取辅助（如 `is_same_v`）正是内联 constexpr 变量模板。

<!-- example id="cpp17-inline-variable-template" std="c++17" file="main.cpp" kind="single" compilers="all" output="pointer=true, value=false" -->
```cpp
#include <iostream>
#include <type_traits>

template <typename T>
inline constexpr bool is_pointer_value = std::is_pointer<T>::value;

struct Limits {
    inline static constexpr int maximum = 64;
};

int main() {
    static_assert(Limits::maximum == 64);
    std::cout << std::boolalpha
              << "pointer=" << is_pointer_value<int*>
              << ", value=" << is_pointer_value<int> << '\n';
}
```

`Limits::maximum` 在类内既声明又定义，不需要传统的类外定义。变量模板的两个特化都是编译期常量，优化后通常不占运行期存储；但若代码取地址导致 odr-use，内联定义仍确保程序拥有合规实体。

## `inline constexpr` 与静态成员

命名空间作用域 `constexpr` 变量过去常具有内部链接，取地址和跨单元身份需要谨慎处理。`inline constexpr` 明确允许头文件定义并提供统一实体。类内 `static constexpr` 数据成员在 C++17 起隐式是内联变量，不再总需要额外类外定义。

类内静态数据成员若显式写 `inline static`，可以在不要求常量表达式的情况下初始化；写成 `inline static constexpr` 则同时获得常量表达式能力。`constexpr` 静态数据成员隐含 `inline`，重复写出主要是强调意图。

内联变量可以是不完整类型的静态成员定义场景之外的一般对象，但初始化点仍要求满足对应类型完整性和声明规则。复杂对象放进公共头文件还会增加所有包含者的编译依赖。

## 初始化与线程安全

内联变量仍可能进行动态初始化，并受到跨翻译单元初始化顺序问题影响。复杂全局对象若依赖另一个全局对象，`inline` 不会自动建立可靠顺序。优先使用常量初始化，或通过函数局部静态实现首次使用时初始化。

对 `active_readers` 的递增仍是普通非原子写；多个线程同时执行会数据竞争。需要同步时使用原子或锁，不要把链接语义误解为并发语义。

所有翻译单元共享同一个内联变量，不意味着每个线程获得副本；这与 `thread_local` 完全不同。可变内联全局量会把测试、插件和并发代码耦合到同一进程状态。若确实需要计数器，可把类型改为原子并定义内存序；若需要复合不变量，则封装互斥量和状态。

动态初始化的内联变量在标准初始化顺序规则中有专门分类，但跨翻译单元依赖仍很难凭肉眼证明。`constinit` 要到 C++20 才能强制常量初始化；在 C++17 中应尽量让初始化式成为常量表达式，或使用函数局部静态延迟到第一次调用。

函数局部静态与内联变量解决不同问题：前者在首次控制流经过声明时初始化，且初始化本身线程安全；后者提供可在命名空间/类作用域直接命名的统一实体。不要仅为躲避初始化顺序而把所有状态隐藏成全局访问器，仍应控制依赖关系。

## 嵌套命名空间与实践

`namespace project::config` 等价于逐层嵌套声明，减少缩进但不改变名称查找。版本化 API 可结合内联命名空间，而普通嵌套语法本身不会让命名空间“内联”。

嵌套形式可以带内联命名空间说明，例如外层普通命名空间与版本内联命名空间组合，但属性和 `inline` 的合法放置需按声明语法书写。它不会创建类似 Java 包的访问边界，命名空间仍可在多个位置重新打开。

命名空间别名、using 声明和 ADL 都按等价的嵌套命名空间结构工作。迁移旧写法时通常只是词法简化，不应伴随实体移动或 ABI 命名变化。

头文件中的配置优先 `inline constexpr`；可变全局状态应尽量避免；必须存在时明确初始化顺序、线程安全和测试隔离策略。

## 权威资料

- [P0386R2：内联变量](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0386r2.pdf)
- [工作草案：inline specifier](https://eel.is/c++draft/dcl.inline)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
