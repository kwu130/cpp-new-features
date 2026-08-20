# C++20：约束、组合、异步与构建边界

C++20 是现代 C++ 的又一次大型升级。Concepts 与 Ranges 重塑泛型接口，Coroutines 把可挂起函数纳入语言，Modules 改变声明传播与构建图；三路比较、编译期增强、非拥有视图、格式化、日历和新并发原语则直接改善日常工程代码。

本专题假设读者已掌握 C++11–17 的模板、值类别、Lambda、智能指针、标准容器、线程与内存模型。文章继续采用“旧版本问题 → 最小语法 → 完整示例 → 输出解释 → 底层模型 → 工程边界”的渐进结构。

## 如何使用本专题

所有标记为 `cpp` 的示例均由验证器以 `-std=c++20 -Wall -Wextra -pedantic` 提取、编译和运行。普通示例面向 GCC 与 Clang；Modules 使用多文件示例，并由专门的 GCC CI 任务按工具链实际构建 BMI、对象文件和最终程序。

C++20 的几个大特性不能只靠语法记忆：Concepts 仍有语义要求，View 常不拥有源，协程返回类型决定帧生命周期，Modules 需要构建系统先理解依赖。建议先完成前两阶段，再学习架构级专题。

## 推荐学习路线

### 第一阶段：日常语言能力

1. [三路比较运算符](spaceship.md)
2. [指定初始化](designated-initialization.md)
3. [`consteval`、`constinit` 与扩展 `constexpr`](compile-time.md)
4. [Lambda 与模板增强](lambdas-and-templates.md)

这一阶段重点区分：比较类别不只是三态整数，指定初始化仍受聚合与声明顺序约束，三个常量相关关键字职责不同，显式模板 Lambda 仍会生成闭包成员函数模板。

### 第二阶段：受约束泛型与非拥有抽象

5. [Concepts 与约束](concepts.md)
6. [Ranges 与 Views](ranges.md)
7. [`span`](span.md)

先用 Concepts 理解能力声明，再学习 Ranges 的迭代器/哨兵和惰性 View，最后把同样的非拥有生命周期思维应用到连续内存 span。

### 第三阶段：实用标准库

8. [`format`](format.md)
9. [`source_location`](source-location.md)
10. [日历、时区与 `chrono` 增强](chrono.md)
11. [位运算工具与数学常量](bit-and-numbers.md)
12. [字符串和容器常用增强](library-conveniences.md)

这组能力大多可局部采用，但仍需关注标准库实现完整度、格式字符串来源、日志路径隐私、时区数据部署、位操作溢出和容器查找复杂度。

### 第四阶段：并发与协作取消

13. [`jthread`、停止令牌与协作取消](jthread.md)
14. [`latch`、`barrier` 与 `semaphore`](synchronization.md)
15. [原子等待与 `atomic_ref`](atomic.md)

学习顺序从线程所有权开始，再进入高层同步状态机，最后回到原子内存序和对象表示。新接口可以减少条件变量样板，但不会自动保证公平、取消及时或数据竞争自由。

### 第五阶段：架构级特性

16. [Coroutines](coroutines.md)
17. [Modules](modules.md)

Coroutines 和 Modules 分别要求异步生命周期设计与构建系统支持。建议结合实际任务/生成器库和真实 CI 工具链验证，不把教学协议类型或某个编译器命令直接视为稳定跨平台方案。

## 特性覆盖矩阵

| 领域 | C++20 主要能力 | 对应专题 |
| --- | --- | --- |
| 比较 | `<=>`、比较类别、默认成员比较 | [三路比较](spaceship.md) |
| 聚合初始化 | 成员指示符、默认成员与顺序约束 | [指定初始化](designated-initialization.md) |
| 常量求值 | `consteval`、`constinit`、扩展 `constexpr` | [编译期增强](compile-time.md) |
| Lambda | 显式模板参数、约束、包捕获展开 | [Lambda 增强](lambdas-and-templates.md) |
| 模板约束 | Concept、requires-expression、约束偏序 | [Concepts](concepts.md) |
| 范围 | Range Concepts、Views、投影与管道 | [Ranges](ranges.md) |
| 连续内存 | 动态/静态长度非拥有视图 | [`span`](span.md) |
| 格式化 | 类型安全格式字符串、自定义 formatter | [`format`](format.md) |
| 诊断 | 调用点文件、函数、行与列 | [`source_location`](source-location.md) |
| 时间 | 公历类型、连续日、时区与当地时间 | [Chrono](chrono.md) |
| 位与数值 | 位计数、旋转、`bit_cast`、数学常量 | [位工具](bit-and-numbers.md) |
| 常用接口 | 前后缀、`contains`、`erase_if` 等 | [库便利增强](library-conveniences.md) |
| 线程生命周期 | 自动连接、停止源/令牌/回调 | [`jthread`](jthread.md) |
| 同步 | 一次汇合、阶段屏障、许可计数 | [同步原语](synchronization.md) |
| 原子 | 等待/通知、现有对象的原子视图 | [原子增强](atomic.md) |
| 可挂起函数 | Promise、awaiter、句柄与协程帧 | [Coroutines](coroutines.md) |
| 构建模型 | 模块单元、分区、BMI 与导入图 | [Modules](modules.md) |

## 容易混淆的版本边界

- `if constexpr` 属于 C++17，Concepts 和 requires-expression 属于 C++20；
- Ranges 基础设施与 Views 属于 C++20，`ranges::to` 要到 C++23；
- `span` 属于 C++20且不拥有内存，`mdspan` 不属于 C++20；
- C++20 协程提供语言协议，但标准库没有 C++20 通用 `generator` 或 `task`；
- Modules 属于 C++20，但 BMI/CMI 文件格式与构建命令不具备跨编译器稳定性；
- `consteval`、`constinit` 属于 C++20，`if consteval` 要到 C++23；
- `std::format` 属于 C++20，但早期标准库版本可能未完整实现；
- `starts_with`、`ends_with` 与关联容器 `contains` 属于 C++20；
- `jthread` 和停止令牌属于 C++20，停止是协作式而非抢占式；
- `latch`、`barrier`、`semaphore` 与原子等待属于 C++20；
- C++20 标准化日历与时区接口，但目标标准库是否提供完整时区数据库仍需部署验证；
- `std::expected`、`std::print`、`std::stacktrace` 不属于 C++20。

## 学习完成标准

完成本专题后，应能在 C++17 项目中有边界地引入 C++20：说明特性影响的是声明、对象、运行期状态还是构建图；指出谁拥有资源、何时可能挂起或阻塞；并为工具链支持、异常、取消、生命周期和跨线程可见性建立验证方案。

[返回仓库总览](../../README.md)
