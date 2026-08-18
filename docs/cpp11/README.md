# C++11：现代 C++ 的起点

C++11 是从传统 C++ 走向现代 C++ 的关键版本。它没有抛弃静态类型、确定性析构和零开销抽象，而是让类型推导、资源所有权、局部函数对象、泛型编程和并发模型拥有更直接的语言表达。

本专题面向已经掌握 C++98/03 基础的读者。文章不要求一次记住所有标准规则，而是按照“旧代码的问题 → 新语法 → 可运行示例 → 底层模型 → 工程边界”的顺序逐层展开。

## 如何阅读

每篇文章分成两个层次：

1. **入门层**：学习目标、C++03 痛点、最小语法、完整示例和输出解释；
2. **进阶层**：精确语义、对象模型、生命周期、性能、版本边界和审查清单。

第一次阅读先完成入门层并亲自运行主示例。第二次阅读再关注值类别、所有权、异常保证、迭代器失效和 happens-before 等底层概念。

所有标记为 `cpp` 的代码块都由仓库验证器提取，并以 `-std=c++11 -Wall -Wextra -pedantic` 编译运行。错误写法使用行内代码或 `text` 围栏，避免把反例伪装成可运行程序。

## 推荐学习路线

### 第一阶段：先写出更清楚的局部代码

1. [类型推导：`auto` 与 `decltype`](type-deduction.md)
2. [统一初始化、初始化列表与 `nullptr`](initialization.md)
3. [范围 `for`](range-for.md)
4. [移动语义与完美转发](move-semantics.md)
5. [Lambda 表达式](lambdas.md)

这一阶段重点回答：变量的真实类型是什么、对象是否被复制、引用是否有效、资源能否安全转移，以及回调捕获了什么。

### 第二阶段：理解类型系统和类设计

6. [可变参数模板与类型别名](templates.md)
7. [`constexpr` 与 `static_assert`](compile-time.md)
8. [类定义能力增强](class-improvements.md)
9. [`noexcept`、字面量、线程局部存储、对齐与属性](core-utilities.md)

这一阶段重点回答：哪些工作发生在编译期、编译器会生成哪些特殊成员、接口怎样表达不可复制和不抛异常，以及后续标准放宽了哪些限制。

### 第三阶段：使用新的标准库设施

10. [智能指针](smart-pointers.md)
11. [容器增强](containers.md)
12. [`tuple`、类型萃取与可调用对象](functional-tools.md)
13. [`chrono`、随机数与正则表达式](utility-libraries.md)
14. [并发编程](concurrency.md)

这一阶段重点回答：谁拥有资源、容器的布局和失效规则是什么、何时需要类型擦除，以及线程之间如何建立可证明的同步关系。

## 特性覆盖矩阵

| 领域 | 主要特性 | 对应专题 |
| --- | --- | --- |
| 类型推导 | `auto`、`decltype`、尾置返回类型、cv/ref | [类型推导](type-deduction.md) |
| 初始化 | 列表初始化、窄化、`initializer_list`、`nullptr` | [统一初始化](initialization.md) |
| 循环 | 范围 `for`、`begin`/`end` 查找、循环变量引用 | [范围 for](range-for.md) |
| 对象转移 | 右值引用、移动构造、`move`、`forward` | [移动语义](move-semantics.md) |
| 局部调用对象 | Lambda、捕获、闭包、函数指针转换 | [Lambda](lambdas.md) |
| 泛型 | 参数包、递归展开、别名模板 | [模板](templates.md) |
| 编译期 | `constexpr`、字面类型、`static_assert` | [编译期](compile-time.md) |
| 类设计 | `default/delete`、`override/final`、委托/继承构造、`enum class` | [类改进](class-improvements.md) |
| 核心设施 | `noexcept`、用户字面量、`thread_local`、`alignas`、C++11 属性 | [核心工具](core-utilities.md) |
| 所有权 | `unique_ptr`、`shared_ptr`、`weak_ptr`、控制块 | [智能指针](smart-pointers.md) |
| 容器 | `array`、`forward_list`、无序容器、`emplace` | [容器增强](containers.md) |
| 调用与类型工具 | `tuple`、type traits、`function`、`bind` | [函数工具](functional-tools.md) |
| 通用库 | `chrono`、随机引擎与分布、正则 | [实用库](utility-libraries.md) |
| 并发 | 线程、互斥量、条件变量、Future/Promise、`async`、原子 | [并发](concurrency.md) |

## C++11 弃用与迁移索引

“不推荐”不等于“标准正式弃用”。本专题依据 C++11 的版本事实区分两者：

| C++11 正式弃用项 | 迁移方向 | 详见 |
| --- | --- | --- |
| `std::auto_ptr` | 根据语义迁移到 `unique_ptr`、`shared_ptr` 或非拥有引用 | [智能指针](smart-pointers.md) |
| `register` | 删除提示，让编译器负责寄存器分配 | [核心工具](core-utilities.md) |
| 动态异常说明 `throw(T...)` | 使用普通异常文档和准确的 `noexcept` 契约 | [核心工具](core-utilities.md) |
| `bind1st`、`bind2nd`、`ptr_fun`、`mem_fun` 等旧适配器 | 优先使用 Lambda，必要时使用 `bind`/`function` | [函数工具](functional-tools.md) |
| 部分隐式复制生成行为 | 明确采用零法则或五法则 | [类改进](class-improvements.md) |

以下项目常被误写成“C++11 已弃用”，实际并非如此：

- `random_shuffle` 到 C++14 才弃用，C++17 移除；
- `[=]` 对 `this` 的隐式捕获到 C++20 才弃用；
- 函数 try block 和 C 风格转换可因可读性不推荐，但不是 C++11 正式弃用项；
- `[[nodiscard]]` 是 C++17 属性，不能作为 C++11 属性示例；
- `make_unique` 是 C++14 库设施，C++11 示例不能使用。

## 参考与事实核对

文章借鉴 [GeeksforGeeks C++11 Standard](https://www.geeksforgeeks.org/cpp/cpp-11-standard/) 及其子文章的入门组织方式，并使用原创中文讲解。具体版本归属和规范性行为以 C++11 工作草案、标准条文及后续缺陷修正为准；当教学页面与标准事实冲突时，正文会明确指出版本边界。

[返回仓库总览](../../README.md)
