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

## ODR 的细粒度要求

多个翻译单元中的 inline 定义必须由相同 token 序列组成，并让定义内部名称查找通常得到相同实体。仅“初始化结果都等于 42”不足；条件宏选择不同表达式、using 指向不同重载都可能违反 ODR。

ODR 违规通常 no diagnostic required，因为链接器只看到可合并符号而不理解全部 C++ 名称查找。程序可能在不同链接顺序/优化级别选中不同定义。公共头文件应避免让 ABI 宏静默改变 inline 变量类型或初始化。

inline 变量具有一个地址的语言保证。每个翻译单元取地址应比较相等（在同一程序/实体条件下），这使它可作为类型标记/注册键；实现通过 COMDAT/weak 等合并只是常见机制。

### 完整定义可达

inline 变量在每个 odr-use 的翻译单元需要可达定义，只有 `extern inline` 风格声明而调用方看不到定义会破坏用途。最直接做法是在头文件定义，不要再在某个 cpp 重复一个不同“权威定义”。

显式特化的变量模板是否 inline 要看特化声明本身，不能只因主模板 inline 就盲目假定所有显式特化获得相同说明。专门化/实例化策略需单独审计。

## 初始化分类与依赖

inline 变量仍有零初始化、常量初始化和动态初始化。constexpr 字面量常走常量初始化；string、容器等可能动态初始化。inline 解决多定义身份，不消除动态初始化执行与次序。

定义在接口中的 inline 动态对象若互相引用，部分有序初始化规则与翻译单元出现顺序有关，仍不适合复杂依赖图。函数局部 static 的 construct-on-first-use 更容易建立调用顺序，但也可能引入首次调用延迟/重入。

初始化函数抛异常会按非局部静态初始化规则处理，通常导致启动失败/终止边界，不应把可恢复配置加载放进全局 inline 初始化器。

### TLS inline 变量

`inline thread_local` 表示每个线程一个实例，同时允许头文件跨翻译单元定义同一线程局部实体。它既不是全进程单例，也不是每翻译单元副本。

每线程动态初始化和析构成本依旧存在，线程池状态残留问题也不因 inline 改变。取地址在同一线程/实体条件下稳定，不同线程地址通常不同。

## 类静态成员与完整类型

`inline static` 数据成员可在类定义内带初始化器，省掉类外定义。成员仍属于类而非每对象，访问控制、模板特化和初始化顺序照常。

类模板的 inline static 成员每个类特化拥有独立实体。大量 T 会产生大量状态，适合每类型元数据但不适合无意的全局缓存膨胀。

从旧代码迁移时删除传统类外定义；保留无初始化的重复定义在 C++17 对 constexpr 成员可能有兼容/弃用细节，但新代码不要维护两份来源。

## 定义与实体速查

| 场景 | 关键规则 |
| --- | --- |
| 头文件 namespace 变量 | 加 inline 后可在多个翻译单元定义同一实体 |
| 定义 token | 各定义需满足 ODR 的相同 token 等要求 |
| 地址 | 合规程序中各翻译单元观察同一实体地址 |
| 类内 `inline static` | 可在类定义中同时声明和定义 |
| `inline constexpr static` | 同时具常量与内联实体语义 |
| 变量模板 | 可用 inline 管理跨翻译单元特化实体 |
| thread_local inline | 每线程一个实体，各翻译单元定义合并 |
| 动态初始化 | inline 不保证跨不同实体的简单全局次序 |
| 显式特化 | inline 属性需按特化声明自身规则处理 |
| ABI | 仍受类型、布局、可见性和共享库规则约束 |

## 内联变量专项审查问题

- 每个翻译单元看到的定义 token 和名称查找是否一致？
- 初始化式是否受宏影响而违反 ODR？
- inline 是否被误解为保证常量初始化或线程安全？
- 多个 inline 动态初始化实体之间是否存在顺序依赖？
- 类内 static 成员是否真的需要独立可变全局状态？
- 模板特化是否继承/重新声明了正确 inline 属性？
- thread_local inline 的每线程身份是否符合设计？
- 共享库可见性与 ABI 是否另行配置？
- 变量地址是否被用作稳定跨进程/跨版本标识？
- 测试是否包含多个翻译单元以验证唯一实体？

## 权威资料

- [P0386R2：内联变量](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0386r2.pdf)
- [工作草案：inline specifier](https://eel.is/c++draft/dcl.inline)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
