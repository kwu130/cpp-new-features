# C++20：约束、组合与异步抽象

C++20 是一次大型升级，引入 Concepts、Ranges、Coroutines、Modules，并显著扩充编译期与并发能力。

## 推荐学习顺序

1. 高频语言能力：三路比较、指定初始化、编译期增强、Lambda 模板。
2. 泛型编程：Concepts、Ranges 与 `span`。
3. 标准库：`format`、位工具、日期和常用容器/字符串增强。
4. 并发：`jthread`、停止令牌、同步原语和原子等待。
5. 架构级特性：Coroutines 与 Modules。

Coroutines 和 Modules 不是孤立语法；分别依赖异步生命周期设计和构建系统支持，建议最后学习并结合实际工程验证。

- [Concepts 与约束](concepts.md)
- [Ranges 与 Views](ranges.md)
- [Coroutines](coroutines.md)
- [Modules](modules.md)
- [三路比较运算符](spaceship.md)
- [指定初始化](designated-initialization.md)
- [`consteval`、`constinit` 与扩展 `constexpr`](compile-time.md)
- [Lambda 与模板增强](lambdas-and-templates.md)
- [`span`](span.md)
- [`format`](format.md)
- [`jthread`、停止令牌与协作取消](jthread.md)
- [`latch`、`barrier` 与 `semaphore`](synchronization.md)
- [原子等待与 `atomic_ref`](atomic.md)
- [`source_location`](source-location.md)
- [日历、时区与 `chrono` 增强](chrono.md)
- [位运算工具与数学常量](bit-and-numbers.md)
- [字符串和容器常用增强](library-conveniences.md)

[返回总览](../../README.md)
