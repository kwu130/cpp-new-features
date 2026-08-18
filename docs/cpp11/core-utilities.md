# `noexcept`、字面量、线程局部存储与对齐

## 学习目标与阅读方式

本篇汇总四组彼此独立但常用于系统接口的能力：异常契约、领域字面量、线程局部状态和内存对齐。读完后，你应该能够解释 `noexcept` 失败时为何终止程序、定义安全的字面量后缀、判断 `thread_local` 的实例数量，并用 `alignas`/`alignof` 表达布局要求。

建议按需阅读各节；它们不要求彼此作为前置知识。

## C++03 中的问题

- 动态异常说明难以维护，不能清晰表达现代“不抛出”契约；
- 单位常写成无类型数字或宏，容易混淆字节、时间和角度；
- 线程局部存储依赖平台扩展；
- 对齐要求依赖编译器关键字，难以写成可移植声明。

C++11 分别提供 `noexcept`、用户定义字面量、`thread_local`、`alignas` 和 `alignof`。它还标准化属性语法，允许实现和工具读取附加语义。

## 第一个完整示例

下面把 2 KiB 转换为字节、维护每线程独立计数，并在编译期检查函数异常契约和结构体对齐。

```cpp example id="cpp11-core-utilities" std="c++11" file="main.cpp" kind="single" compilers="all" output="2048 bytes, calls=2"
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

程序输出 `2048 bytes, calls=2`。`2_KiB` 在编译期调用字面量运算符；主线程拥有自己的 `calls` 实例；两个断言分别验证异常说明和 16 字节对齐。不要把可能抛出的函数错误标为 `noexcept`，否则异常逃出时程序会终止。

## `noexcept`：接口契约与优化条件

`noexcept` 是函数声明上的异常规格，表示异常不得逃出函数。若违反，运行时调用 `std::terminate`，不会让外层 `catch` 正常恢复。在 C++11 中异常规格尚不是函数类型的一部分；这一点到 C++17 才发生重要变化。条件形式 `noexcept(condition)` 适合让模板函数的异常保证跟随成员操作。

`noexcept(expression)` 运算符不会执行表达式，而是在编译期查询它是否被声明为不抛异常。标准容器在搬迁元素时会参考移动构造是否 `noexcept`，从而决定移动能否保持强异常保证。因此准确标注会影响算法路径，错误标注则可能把可恢复异常变成终止。

C++11 仍支持旧动态异常说明但已不推荐，`noexcept(false)` 表示允许异常逃出，等价于没有不抛承诺的常见语义。空 `noexcept` 等于 `noexcept(true)`。

析构函数通常隐式获得由成员/基类析构合成的不抛说明；析构抛出尤其危险，若栈展开中再抛会终止。资源释放 API 应吸收/记录无法恢复错误或提供显式 close，而非依赖析构异常。

函数指针类型与 noexcept 的关系在 C++17 有重要演进，C++11 不应把后续“异常说明是函数类型一部分”的所有规则倒推回来。重载也不能仅以异常说明区别两个函数。

### 强、基本与不抛保证

noexcept 只声明异常是否逃出，不等于某操作提供强异常保证。强保证允许失败时状态不变，基本保证保持不变量但状态可能改变，不抛保证才是不传播异常。一个非 noexcept 函数也可在特定失败上强回滚。

容器选择 move/copy 时利用 noexcept 是为了组合强保证。自定义类型应从成员真实操作推导，不为性能虚假标注；终止并不是“更快异常处理”的可接受替代。

## 用户定义字面量

字面量运算符把源代码中的数值、字符或字符串字面量转换成领域类型。编译器先按规定参数形式解析字面量，再调用对应运算符；它不是任意文本宏，不能改变语言词法规则。

示例使用整数形式接收 `unsigned long long` 并在编译期换算 KiB。实际单位库应返回强类型而非裸 `size_t`，从类型系统层面防止字节、时间和距离混用。自定义后缀必须以下划线开头，非下划线名称保留给标准库。

整数 cooked 形式接收 unsigned long long，浮点 cooked 形式接收 long double，字符/字符串形式按对应字符类型与长度签名。raw 数值形式或字面量运算符模板可以观察源 token 字符，适合编译期解析，但实现复杂且错误诊断要设计。

字符串字面量运算符接收指针和长度，长度不含结尾零但内容可含嵌入零。函数必须在调用期间复制需要拥有的数据，不能把编译器字面量地址的使用方式泛化到运行时字符串。

用户字面量只对源代码 token 生效，不能对运行期变量写 `value_suffix`。运行期单位转换仍需要普通函数/强类型构造。

后缀位于命名空间作用域定义，使用时受字面量运算符查找规则影响。库通常放专门 literals 命名空间，由调用方选择 using，避免全局后缀碰撞。

### 溢出和单位类型

示例 value*1024 可能超过 `size_t`；constexpr 不自动防溢出，无符号回绕会产生错误容量。强单位库应先检查 ULL 范围、选择足够表示并在非法常量上给出诊断。

返回裸整数仍可与其他整数混用。返回 `Bytes` 值对象并只提供有意义运算，才能阻止把毫秒当字节。字面量是入口语法，类型才承载领域安全。

## `thread_local` 的存储模型

每个线程拥有变量的独立实例，变量在线程首次使用前完成初始化，在线程结束时销毁。实现通常通过线程本地存储段和运行时线程控制块定位对象，而不是为每次访问加锁。

线程局部状态减少共享竞争，但也会放大内存占用，并让测试、任务在线程池间迁移和析构顺序更复杂。它适合缓存或线程上下文，不应替代清晰的参数传递。

`thread_local` 可用于命名空间变量、类静态数据成员和块作用域静态变量；它与 static/extern 的允许组合控制链接和声明。每线程实例有线程存储期，不是每次函数调用新建。

非平凡初始化可能在每线程首次 odr-use 前执行，实现常用守卫检查；热路径访问并不一定只是一个普通全局加载。TLS 模型和动态库边界会影响成本，应在目标平台测量。

每线程析构发生在线程退出，进程终止、线程被平台强制结束或库卸载时的边界复杂。析构访问其他 TLS/全局对象可能遇到次序问题，缓存对象应尽量平凡或独立。

线程池任务迁移让“线程上下文”不等于“请求上下文”。安全身份、locale、allocator 等状态若放 TLS，进入/离开任务必须显式安装和恢复，最好用作用域守卫。

## 对齐控制

`alignas(N)` 指定对象至少满足 N 字节对齐，`alignof(T)` 查询类型对齐要求。编译器会在对象布局和数组步长中插入必要填充；更高对齐可能增加结构体大小。动态分配过度对齐类型在不同标准版本的支持不同，不能只看到类型声明通过就假设任意分配器都满足要求。

alignas 参数可以是常量对齐值或类型。多个 alignas 组合取最严格有效要求，不能用更弱对齐降低类型自然对齐；非法非二次幂/实现不支持值会被诊断。

`std::alignment_of<T>` 提供萃取形式，`std::aligned_storage`/`aligned_union` 在 C++11 用于取得未初始化对齐存储。它们只提供字节存储，调用者仍要 placement new、显式析构并遵守对象生命周期/别名规则。

### 分配器边界

C++11 普通 `operator new` 只承诺满足基本最大对齐范围，过度对齐类型的通用 new 支持到 C++17 才完善。平台可扩展支持，但可移植 C++11 要使用匹配的对齐分配 API和自定义删除器。

对齐地址同时不保证缓存行隔离。两个 alignas(64) 成员/对象是否真正不共享缓存行还受对象布局、数组步长和硬件干扰大小影响，C++17 才提供 interference size 常量。

协议布局不能只靠 alignas；填充、字节序、字段偏移和 ABI 都需验证。网络/磁盘数据应逐字段编码，不把结构体对象表示直接发送。

## 工程检查清单

异常保证必须与实现一致；单位字面量优先返回强类型；线程局部对象保持轻量且避免复杂析构依赖；布局相关代码同时验证 `sizeof`、`alignof` 和目标 ABI，而不是假设跨平台一致。

## 条件 `noexcept` 与泛型包装器

模板包装器的异常保证通常取决于被包装操作。条件 `noexcept(noexcept(expression))` 先在内层查询表达式，再把结果用于外层函数规格。这样类型系统可以准确区分不抛与可能抛出的实例。

```cpp example id="cpp11-conditional-noexcept" std="c++11" file="main.cpp" kind="single" compilers="all" output="safe=true, risky=false"
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

```cpp example id="cpp11-thread-local-isolation" std="c++11" file="main.cpp" kind="single" compilers="all" output="workers=2,2 main=0"
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

在线程池中，任务会复用工作线程，因此 `thread_local` 状态可能跨请求残留。请求上下文若需要严格清理，应使用作用域对象或显式重置，而不能假设每个任务获得新线程。

## C++11 属性：标准语法与版本边界

C++11 标准化了 `[[attribute]]` 语法。属性为编译器和分析工具提供附加信息，但不能随意改变程序的核心语义。C++11 标准属性主要包括 `[[noreturn]]` 和与并发依赖链相关的 `[[carries_dependency]]`。

`[[noreturn]]` 用于声明函数不会正常返回，例如最终总是抛出异常或终止进程的错误处理函数。若函数实际正常返回，程序行为不再可靠，因此它和 `noexcept` 一样必须反映真实实现。

常见的 `[[deprecated]]` 是 C++14 引入，`[[fallthrough]]`、`[[nodiscard]]` 和 `[[maybe_unused]]` 是 C++17 引入。指定参考页面使用 `[[nodiscard]]` 作为 C++11 示例并不准确，本仓库不会把它放入 C++11 可编译示例。

## C++11 正式弃用的核心写法

- `register` 存储类说明符在 C++11 被弃用；现代优化器自行决定寄存器分配，代码不应依赖这一提示。
- 动态异常说明 `throw(Type1, Type2)` 在 C++11 被弃用，应迁移到普通异常文档与 `noexcept` 契约。`throw()` 与 `noexcept` 的历史兼容规则需要按目标标准核对。
- C 风格转换和函数 try block 可以因可读性而不推荐，但它们并不是 C++11 正式弃用项，不能与 Annex D 的弃用设施混为一谈。

## 核心设施速查

| 设施 | 关键语义 |
| --- | --- |
| `noexcept` 说明 | 进入函数类型/契约体系，违约异常导致 terminate |
| `noexcept(expr)` | 未求值查询表达式是否声明为不抛 |
| 条件 noexcept | 可随成员/模板操作的异常性质变化 |
| `operator"" _x` | 用户定义字面量后缀应使用保留规则允许的名称 |
| cooked 字面量 | 接收已转换数值/字符值 |
| raw 字面量 | 接收源码字符序列，适合编译期解析 |
| `thread_local` | 每线程独立对象，初始化/析构发生在线程生命周期 |
| `alignas` | 提高实体对齐，不能请求无效/削弱自然对齐 |
| `alignof(T)` | 返回类型所需对齐，单位为字节 |
| `aligned_storage` | C++11 低层存储工具，仍需 placement 构造和显式析构 |
| `[[noreturn]]` | 声明函数不会正常返回，错误标注会破坏程序语义 |

## 核心工具专项审查

- noexcept 声明是否与实际所有调用路径一致？
- 条件 noexcept 是否包含成员交换/移动的真实表达式？
- noexcept 函数内异常是否会意外 terminate？
- 用户字面量后缀是否遵守保留命名规则？
- raw/cooked 重载是否会产生歧义或错误解析？
- `thread_local` 对象析构是否访问已销毁全局状态？
- 动态加载库卸载与 TLS 析构顺序是否评估？
- alignas 是否满足硬件/API 对齐而非只看 sizeof？
- 手工对齐存储是否正确构造、launder 边界和析构？
- 过度对齐对象的分配器是否实际支持所需对齐？

## 权威资料

- [异常规格](https://eel.is/c++draft/except.spec)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
