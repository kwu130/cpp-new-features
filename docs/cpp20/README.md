# C++20：约束、组合、异步与构建边界

C++20 是现代 C++ 的又一次大型升级。Concepts 与 Ranges 重塑泛型接口，Coroutines 把可挂起函数纳入语言，Modules 改变声明传播与构建图；三路比较、编译期增强、非拥有视图、格式化、日历和新并发原语则直接改善日常工程代码。

本专题面向掌握基本 C++ 语法的读者。需要的前置知识在各篇开头给出链接，先完成入门示例，再按需阅读深入规则。

## 如何使用本专题

所有标记为 `cpp` 的示例均由验证器以 `-std=c++20 -Wall -Wextra -pedantic` 提取、编译和运行。普通示例面向 GCC 与 Clang；Modules 使用多文件示例，由现有 Ubuntu CI 的 GCC 矩阵分支按工具链实际构建 BMI、对象文件和最终程序。

C++20 的几个大特性不能只靠语法记忆：Concepts 仍有语义要求，View 常不拥有源，协程返回类型决定帧生命周期，Modules 需要构建系统先理解依赖。建议先完成前两阶段，再学习架构级专题。

## 推荐学习路线

### 第一阶段：局部语言与视图

1. [指定初始化](designated-initialization.md)
2. [三路比较运算符](spaceship.md)
3. [consteval、constinit 与扩展 constexpr](compile-time.md)
4. [span](span.md)

先理解字段名、比较、编译期要求和非拥有连续内存窗口，无需先学习约束偏序。

### 第二阶段：日常标准库

5. [字符串和容器常用增强](library-conveniences.md)
6. [format](format.md)
7. [source_location](source-location.md)
8. [位运算工具与数学常量](bit-and-numbers.md)
9. [日历、时区与 chrono](chrono.md)

按实际用途学习，确认当前标准库是否实现所需接口，时区数据库是否可用。

### 第三阶段：现代泛型编程

10. [Concepts：先约束普通模板](concepts.md#先约束一个函数模板)
11. [Lambda 与模板增强](lambdas-and-templates.md)
12. [Ranges 与 Views](ranges.md)

Concepts 先学“哪些类型能调用”，再学 requires-expression 和偏序；Ranges 先比较普通循环与管道，再进入迭代器、哨兵和 borrowed_range。

### 第四阶段：并发与高级控制流

13. [jthread 与协作取消](jthread.md)
14. [latch、barrier 与 semaphore](synchronization.md)
15. [原子等待与 atomic_ref](atomic.md)
16. [Coroutines：先手动暂停与恢复](coroutines.md#先看暂停与恢复)
17. [Modules](modules.md)

协程语言机制不自动创建线程；异步调度是建立在生命周期与同步之上的库协议。Modules 需要独立理解依赖扫描、模块产物和链接流程。

## 验证本版本示例

从仓库根目录运行：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp20
python3 tools/verify_examples.py --compiler g++ --path docs/cpp20
```

普通示例要求 GCC 与 Clang；请用 `--version` 确认编译器身份。GCC 专用示例在 Clang 下跳过，属于未验证项。

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

[继续阅读 C++23](../cpp23/README.md) · [返回仓库总览](../../README.md)
