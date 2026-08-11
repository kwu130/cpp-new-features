# C++11：现代 C++ 的起点

C++11 将资源管理、泛型编程、函数对象和并发能力系统化，是后续标准的共同基础。

## 推荐学习顺序

1. 基础语法：类型推导、初始化、范围 `for`、Lambda。
2. 对象模型：移动语义、类定义增强、`constexpr`。
3. 泛型与资源：可变参数模板、智能指针、容器与函数工具。
4. 系统能力：时间、随机数、正则和并发内存模型。

第一次阅读先运行每篇主示例；第二次阅读重点理解生命周期、值类别、所有权和 happens-before。

## 语言特性

- [类型推导：`auto` 与 `decltype`](type-deduction.md)
- [统一初始化、初始化列表与 `nullptr`](initialization.md)
- [范围 `for`](range-for.md)
- [移动语义与完美转发](move-semantics.md)
- [Lambda 表达式](lambdas.md)
- [可变参数模板与类型别名](templates.md)
- [`constexpr` 与 `static_assert`](compile-time.md)
- [类定义能力增强](class-improvements.md)
- [`noexcept`、字面量、线程局部存储与对齐](core-utilities.md)

## 标准库

- [智能指针](smart-pointers.md)
- [容器增强](containers.md)
- [`tuple`、类型萃取与可调用对象](functional-tools.md)
- [`chrono`、随机数与正则表达式](utility-libraries.md)
- [并发编程](concurrency.md)

[返回总览](../../README.md)
